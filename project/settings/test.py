import environ

env = environ.Env(
    DEBUG=(bool, True),
)

DEBUG = env("DEBUG")

if DEBUG:
    from .dev import *  # noqa
else:
    from .production import *  # noqa

# Во время сборки тестов происходит ошибка связанная с использованием django-constance и глобальным импортом через *
# pytest не может получить доступ к бд и запуск тестов падает. Поэтому внутри тест кейсов мы изменяем backend для
# django-constance c бд на in memory (https://django-constance.readthedocs.io/en/latest/testing.html#memory-backend)
CONSTANCE_BACKEND = "constance.backends.memory.MemoryBackend"

# Отправка писем в тестах — без задержки.
MAILING_SEND_DELAY_SECONDS = 0


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "tracker_db",
        "USER": "tracker_user",
        "HOST": "db",
        "PASSWORD": "pass",
        "PORT": 5432,
    }
}

