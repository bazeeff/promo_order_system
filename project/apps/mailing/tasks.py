import logging
import time

from apps import app
from apps.mailing.models import Mailing
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_SEND_DELAY_SECONDS = 5


@app.task
def send_mailing(mailing_id: str) -> None:
    """«Отправка» письма: запись сообщения в лог с задержкой.

    По условию задачи вместо реального SMTP письмо пишется в лог после
    паузы ``settings.MAILING_SEND_DELAY_SECONDS`` — имитация доставки,
    выполняемая Celery-воркером. Задача идемпотентна: уже отправленное
    письмо не отправляется повторно.
    """
    try:
        mailing = Mailing.objects.get(pk=mailing_id)
    except Mailing.DoesNotExist:
        logger.warning("Mailing %s not found, skipping", mailing_id)
        return

    if mailing.status == Mailing.Status.SENT:
        logger.info("Mailing %s already sent, skipping", mailing_id)
        return

    delay = getattr(
        settings,
        "MAILING_SEND_DELAY_SECONDS",
        DEFAULT_SEND_DELAY_SECONDS,
    )
    if delay > 0:
        time.sleep(delay)

    logger.info(
        "Письмо отправлено: external_id=%s, user_id=%s, email=%s, "
        "subject=%s, message=%s",
        mailing.external_id,
        mailing.user_id,
        mailing.email,
        mailing.subject,
        mailing.message,
    )
    mailing.status = Mailing.Status.SENT
    mailing.sent_at = timezone.now()
    mailing.save(update_fields=["status", "sent_at"])
