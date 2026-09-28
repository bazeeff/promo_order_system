from django.conf import settings
from django.db import models

from ...helpers.models import UUIDModel, CreatedModel


class Mailing(UUIDModel, CreatedModel):
    """Письмо рассылки, импортированное из внешней системы.

    ``external_id`` — идентификатор записи во внешней системе: уникален,
    поэтому повторный импорт того же файла не создаёт дубликаты.
    ``status``/``sent_at`` заполняет Celery-задача отправки.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает отправки"
        SENT = "sent", "Отправлено"

    external_id = models.CharField(
        "ID во внешней системе",
        max_length=255,
        unique=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mailings",
        verbose_name="Пользователь",
    )
    email = models.EmailField(
        "Email получателя",
    )
    subject = models.CharField(
        "Тема письма",
        max_length=255,
    )
    message = models.TextField(
        "Текст письма",
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    sent_at = models.DateTimeField(
        "Отправлено",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Письмо рассылки"
        verbose_name_plural = "Письма рассылки"

    def __str__(self) -> str:
        return f"{self.external_id}: {self.subject}"
