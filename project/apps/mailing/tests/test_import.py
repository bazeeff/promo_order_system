import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import TestCase

import pytest
from apps.mailing.models import Mailing
from apps.mailing.services import (
    MailingsImportService,
    MissingColumnsError,
)
from apps.user.models.user import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from openpyxl import Workbook

HEADERS = ("external_id", "user_id", "email", "subject", "message")


def make_xlsx(path: Path, rows, headers=HEADERS):
    """Создать XLSX-файл с заголовком и строками данных."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    workbook.save(path)
    return path


def make_user(email="customer@example.com"):
    return User.objects.create_user(
        email=email,
        password="test-password-123",
        first_name="Customer",
    )


class DispatchRecorder:
    """Собирает письма, поставленные в отправку, вместо Celery."""

    def __init__(self):
        self.dispatched = []

    def __call__(self, mailing):
        self.dispatched.append(mailing)


class TempDirTestCase(TestCase):
    """Базовый класс с временной директорией для файлов импорта."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


@pytest.mark.django_db
class MailingsImportServiceTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.recorder = DispatchRecorder()
        self.service = MailingsImportService()

    def import_rows(self, rows, headers=HEADERS, **options):
        path = make_xlsx(self.tmp / "mailings.xlsx", rows, headers)
        return self.service.process(
            path=path, dispatch=self.recorder, **options
        )

    def test_creates_mailings_and_dispatches(self):
        stats = self.import_rows(
            [
                ("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст"),
                (
                    "ext-2",
                    str(self.user.pk),
                    "b@example.com",
                    "Тема 2",
                    "Текст 2",
                ),
            ],
        )

        assert stats.processed == 2
        assert stats.created == 2
        assert stats.skipped == 0
        assert stats.failed == 0
        assert Mailing.objects.count() == 2
        assert len(self.recorder.dispatched) == 2
        [first] = Mailing.objects.filter(external_id="ext-1")
        assert first.user == self.user
        assert first.status == Mailing.Status.PENDING

    def test_reimport_skips_existing_external_ids(self):
        rows = [("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст")]
        first = self.import_rows(rows)
        assert first.created == 1

        second = self.import_rows(rows)

        assert second.processed == 1
        assert second.created == 0
        assert second.skipped == 1
        assert second.failed == 0
        assert Mailing.objects.count() == 1

    def test_intra_file_duplicate_is_skipped(self):
        row = ("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст")

        stats = self.import_rows([row, row])

        assert stats.created == 1
        assert stats.skipped == 1

    def test_invalid_rows_are_counted_as_failed(self):
        unknown_user_uuid = "f" * 32

        stats = self.import_rows(
            [
                ("", str(self.user.pk), "a@example.com", "Тема", "Текст"),
                ("ext-2", "not-an-uuid", "a@example.com", "Тема", "Текст"),
                ("ext-3", str(self.user.pk), "not-email", "Тема", "Текст"),
                ("ext-4", str(self.user.pk), "a@example.com", "", "Текст"),
                ("ext-5", str(self.user.pk), "a@example.com", "Тема", ""),
                ("ext-6", unknown_user_uuid, "a@example.com", "Тема", "Текст"),
            ],
        )

        assert stats.processed == 6
        assert stats.created == 0
        assert stats.failed == 6
        assert len(stats.errors) == 6
        reasons = " ".join(reason for _, reason in stats.errors)
        assert "external_id пуст" in reasons
        assert "UUID" in reasons
        assert "email" in reasons
        assert "subject пуст" in reasons
        assert "message пуст" in reasons
        assert "пользователь не найден" in reasons

    def test_missing_column_raises(self):
        path = make_xlsx(
            self.tmp / "mailings.xlsx",
            [("ext-1", str(self.user.pk), "a@example.com", "Тема")],
            headers=("external_id", "user_id", "email", "subject"),
        )

        with pytest.raises(MissingColumnsError):
            self.service.process(path=path, dispatch=self.recorder)

    def test_column_order_does_not_matter(self):
        path = make_xlsx(
            self.tmp / "mailings.xlsx",
            [("Тема", "ext-1", "a@example.com", "Текст", str(self.user.pk))],
            headers=("subject", "external_id", "email", "message", "user_id"),
        )

        stats = self.service.process(path=path, dispatch=self.recorder)

        assert stats.created == 1
        [mailing] = Mailing.objects.all()
        assert mailing.external_id == "ext-1"
        assert mailing.subject == "Тема"
        assert mailing.message == "Текст"

    def test_blank_rows_are_ignored(self):
        stats = self.import_rows(
            [
                ("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст"),
                (None, None, None, None, None),
                ("   ", "", "", "", ""),
            ],
        )

        assert stats.processed == 1
        assert stats.created == 1
        assert stats.failed == 0

    def test_dry_run_creates_nothing(self):
        stats = self.import_rows(
            [("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст")],
            dry_run=True,
        )

        assert stats.created == 1
        assert Mailing.objects.count() == 0
        assert self.recorder.dispatched == []

    def test_rows_are_processed_in_batches(self):
        rows = [
            (
                f"ext-{index}",
                str(self.user.pk),
                "a@example.com",
                "Тема",
                "Текст",
            )
            for index in range(5)
        ]

        stats = self.import_rows(rows, batch_size=2)

        assert stats.processed == 5
        assert stats.created == 5
        assert stats.failed == 0
        assert Mailing.objects.count() == 5
        assert len(self.recorder.dispatched) == 5


@pytest.mark.django_db
class SendMailingTaskTestCase(TestCase):
    def setUp(self):
        from apps.mailing.tasks import send_mailing

        self.task = send_mailing
        self.user = make_user()

    def make_mailing(self, **overrides):
        defaults = {
            "external_id": "ext-1",
            "user": self.user,
            "email": "customer@example.com",
            "subject": "Тема",
            "message": "Текст письма",
        }
        defaults.update(overrides)
        return Mailing.objects.create(**defaults)

    def test_task_marks_mailing_sent_and_logs_message(self):
        mailing = self.make_mailing()

        with self.assertLogs("apps.mailing.tasks", level="INFO") as logs:
            self.task(str(mailing.pk))

        mailing.refresh_from_db()
        assert mailing.status == Mailing.Status.SENT
        assert mailing.sent_at is not None
        assert "Текст письма" in logs.output[0]
        assert "customer@example.com" in logs.output[0]

    def test_task_is_idempotent_for_sent_mailing(self):
        mailing = self.make_mailing(
            status=Mailing.Status.SENT,
            sent_at=timezone.now() - timedelta(days=1),
        )
        sent_at = mailing.sent_at

        self.task(str(mailing.pk))

        mailing.refresh_from_db()
        assert mailing.sent_at == sent_at

    def test_task_tolerates_missing_mailing(self):
        self.task("00000000-0000-0000-0000-000000000000")  # не должно падать


@pytest.mark.django_db
class ImportMailingsCommandTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()

    def test_command_imports_file_and_prints_summary(self):
        path = make_xlsx(
            self.tmp / "mailings.xlsx",
            [
                ("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст"),
                ("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст"),
                ("ext-2", "", "a@example.com", "Тема", "Текст"),
            ],
        )

        stdout = StringIO()
        call_command("import_mailings", str(path), stdout=stdout)

        output = stdout.getvalue()
        assert "обработано строк 3" in output
        assert "создано записей 1" in output
        assert "пропущено записей 1" in output
        assert "ошибочных строк 1" in output
        assert "Строка 4 ошибочна" in output
        assert Mailing.objects.count() == 1

    def test_command_dry_run_creates_nothing(self):
        path = make_xlsx(
            self.tmp / "mailings.xlsx",
            [("ext-1", str(self.user.pk), "a@example.com", "Тема", "Текст")],
        )

        stdout = StringIO()
        call_command("import_mailings", str(path), dry_run=True, stdout=stdout)

        assert "создано записей 1" in stdout.getvalue()
        assert Mailing.objects.count() == 0

    def test_command_fails_on_missing_file(self):
        with pytest.raises(CommandError):
            call_command("import_mailings", "/nonexistent/file.xlsx")
