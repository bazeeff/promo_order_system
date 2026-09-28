import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from uuid import UUID

from apps.helpers.services import AbstractService
from apps.mailing.models import Mailing
from apps.user.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from django.db import transaction
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("external_id", "user_id", "email", "subject", "message")
DEFAULT_BATCH_SIZE = 500

SUBJECT_MAX_LENGTH = 255


class MissingColumnsError(ValueError):
    """В файле нет одной или нескольких обязательных колонок."""


@dataclass
class ImportStats:
    """Сводка результата импорта."""

    processed: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list = field(default_factory=list)  # noqa: WPS110

    def register_error(self, row_number: int, reason: str) -> None:
        self.failed += 1
        self.errors.append((row_number, reason))


class MailingsImportService(AbstractService):
    """Импорт писем рассылки из XLSX и постановка их в отправку.

    Файл читается потоково (``read_only``) и записывается в БД батчами,
    поэтому размер файла не ограничен памятью. Повторная обработка той
    же записи предотвращается уникальностью ``external_id``: такие
    строки пропускаются и попадают в ``skipped``.
    """

    def process(
        self,
        *,
        path: Path,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
        dispatch: Callable[[Mailing], None] | None = None,
    ) -> ImportStats:
        """Импортировать письма из файла.

        Args:
            path: путь к XLSX-файлу, первая строка — заголовки колонок.
            batch_size: сколько строк записывать в БД за один батч.
            dry_run: только проверить файл, ничего не создавать.
            dispatch: колбэк постановки письма в отправку; по умолчанию —
                Celery-задача ``send_mailing``.

        Returns:
            Сводка ImportStats: обработано/создано/пропущено/ошибки.

        Raises:
            MissingColumnsError: если нет обязательных колонок.

        """
        dispatch = dispatch or self._default_dispatch
        stats = ImportStats()
        seen_external_ids: set[str] = set()

        workbook = load_workbook(
            filename=path, read_only=True, data_only=True
        )
        try:
            worksheet = workbook.active
            rows = worksheet.iter_rows(values_only=True)
            columns = self._column_indices(next(rows))

            batch: list[dict] = []
            for row_number, row in enumerate(rows, start=2):
                values = self._row_values(columns, row)
                if values is None:  # полностью пустая строка
                    continue

                stats.processed += 1
                parsed = self._parse_row(row_number, values, stats)
                if parsed is not None:
                    batch.append(parsed)

                if len(batch) >= batch_size:
                    self._flush_batch(
                        batch=batch,
                        stats=stats,
                        seen_external_ids=seen_external_ids,
                        dry_run=dry_run,
                        dispatch=dispatch,
                    )
                    batch = []

            self._flush_batch(
                batch=batch,
                stats=stats,
                seen_external_ids=seen_external_ids,
                dry_run=dry_run,
                dispatch=dispatch,
            )
        finally:
            workbook.close()

        logger.info(
            "Mailings import finished: processed=%s created=%s skipped=%s failed=%s",
            stats.processed,
            stats.created,
            stats.skipped,
            stats.failed,
        )
        return stats

    @staticmethod
    def _column_indices(header_row: tuple) -> dict[str, int]:
        """Сопоставить имена обязательных колонок с их индексами."""
        normalized = {
            str(cell).strip().lower(): index
            for index, cell in enumerate(header_row)
        }
        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in normalized
        ]
        if missing:
            raise MissingColumnsError(
                "В файле отсутствуют колонки: " + ", ".join(missing)
            )
        return {
            column: normalized[column] for column in REQUIRED_COLUMNS
        }

    @staticmethod
    def _row_values(columns: dict[str, int], row: tuple) -> dict | None:
        """Достать значения обязательных колонок строки.

        ``None`` возвращается для полностью пустых строк — они не
        считаются ни обработанными, ни ошибочными.
        """
        values = {
            column: row[index] if index < len(row) else None
            for column, index in columns.items()
        }
        if all(value is None or not str(value).strip() for value in values.values()):
            return None
        return values

    @staticmethod
    def _clean(value) -> str:
        """Привести значение ячейки к строке без лишних пробелов."""
        if value is None:
            return ""
        return str(value).strip()

    def _parse_row(
        self, row_number: int, values: dict, stats: ImportStats
    ) -> dict | None:
        """Провалидировать строку и собрать данные для Mailing.

        Возвращает ``None`` для ошибочных строк; причина ошибки
        регистрируется в статистике.
        """
        external_id = self._clean(values.get("external_id"))
        user_id = self._clean(values.get("user_id"))
        email = self._clean(values.get("email"))
        subject = self._clean(values.get("subject"))
        message = self._clean(values.get("message"))

        if not external_id:
            self._fail(stats, row_number, "external_id пуст")
            return None
        if not user_id:
            self._fail(stats, row_number, "user_id пуст")
            return None
        try:
            user_pk = UUID(user_id)
        except (TypeError, ValueError):
            self._fail(stats, row_number, f"user_id не является UUID: {user_id!r}")
            return None
        if not email:
            self._fail(stats, row_number, "email пуст")
            return None
        try:
            EmailValidator()(email)
        except DjangoValidationError:
            self._fail(stats, row_number, f"некорректный email: {email!r}")
            return None
        if not subject:
            self._fail(stats, row_number, "subject пуст")
            return None
        if len(subject) > SUBJECT_MAX_LENGTH:
            self._fail(
                stats,
                row_number,
                f"subject длиннее {SUBJECT_MAX_LENGTH} символов",
            )
            return None
        if not message:
            self._fail(stats, row_number, "message пуст")
            return None

        return {
            "row_number": row_number,
            "external_id": external_id,
            "user_pk": user_pk,
            "email": email,
            "subject": subject,
            "message": message,
        }

    def _flush_batch(
        self,
        *,
        batch: list[dict],
        stats: ImportStats,
        seen_external_ids: set,
        dry_run: bool,
        dispatch: Callable[[Mailing], None],
    ) -> None:
        """Записать батч строк в БД и поставить письма в отправку."""
        if not batch:
            return

        external_ids = [row["external_id"] for row in batch]
        existing_ids = set(
            Mailing.objects.filter(external_id__in=external_ids)
            .values_list("external_id", flat=True)
        )
        user_pks = {row["user_pk"] for row in batch}
        known_user_pks = set(
            User.objects.filter(pk__in=user_pks).values_list("pk", flat=True)
        )

        mailings = []
        for row in batch:
            row_number = row["row_number"]
            external_id = row["external_id"]
            if external_id in seen_external_ids or external_id in existing_ids:
                stats.skipped += 1
                continue
            if row["user_pk"] not in known_user_pks:
                self._fail(
                    stats,
                    row_number,
                    f"пользователь не найден: {row['user_pk']}",
                )
                continue

            seen_external_ids.add(external_id)
            mailings.append(
                Mailing(
                    external_id=external_id,
                    user_id=row["user_pk"],
                    email=row["email"],
                    subject=row["subject"],
                    message=row["message"],
                )
            )

        if dry_run:
            stats.created += len(mailings)
            return

        with transaction.atomic():
            created = Mailing.objects.bulk_create(mailings)
        stats.created += len(created)
        for mailing in created:
            dispatch(mailing)

    @staticmethod
    def _default_dispatch(mailing: Mailing) -> None:
        """Поставить письмо в отправку Celery-воркером.

        Недоступный брокер не должен валить импорт: запись уже
        сохранена и будет отправлена при повторной обработке.
        """
        from apps.mailing.tasks import send_mailing

        try:
            send_mailing.apply_async(args=[str(mailing.pk)])
        except Exception:  # noqa: WPS329
            logger.exception(
                "Не удалось поставить письмо %s в отправку",
                mailing.external_id,
            )

    @staticmethod
    def _fail(stats: ImportStats, row_number: int, reason: str) -> None:
        logger.warning("Строка %s ошибочна: %s", row_number, reason)
        stats.register_error(row_number, reason)
