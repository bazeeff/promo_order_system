# flake8: noqa
import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env(
    DEBUG=(bool, True),
)

DEBUG = env("DEBUG")

if DEBUG:
    from .dev import *  # noqa
else:
    from .production import *  # noqa

if not environ.Env(SENTRY_DSN=(bool, False)):
    raise ImproperlyConfigured("Установите переменную SENTRY_DSN")
