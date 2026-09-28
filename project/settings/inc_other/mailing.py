from ..common import env

# Имитация отправки письма: пауза перед записью сообщения в лог
# (см. примечание к задаче импорта рассылок).
MAILING_SEND_DELAY_SECONDS = env("MAILING_SEND_DELAY_SECONDS", int, 5)
