from pathlib import Path

from apps.mailing.services import (
    MailingsImportService,
    MissingColumnsError,
)
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Импорт писем рассылки из XLSX-файла с постановкой в отправку. "
        "Первая строка файла — заголовки колонок: "
        "external_id, user_id, email, subject, message."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=Path,
            help="Путь к XLSX-файлу рассылки.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Сколько строк записывать в БД за один батч (по умолчанию 500).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только проверить файл, ничего не создавать и не отправлять.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        if not path.is_file():
            raise CommandError(f"Файл не найден: {path}")

        try:
            stats = MailingsImportService().process(
                path=path,
                batch_size=options["batch_size"],
                dry_run=options["dry_run"],
            )
        except MissingColumnsError as exc:
            raise CommandError(exc) from exc

        for row_number, reason in stats.errors:
            self.stdout.write(
                self.style.WARNING(f"Строка {row_number} ошибочна: {reason}")
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершён: обработано строк {stats.processed}, "
                f"создано записей {stats.created}, "
                f"пропущено записей {stats.skipped}, "
                f"ошибочных строк {stats.failed}."
            )
        )
