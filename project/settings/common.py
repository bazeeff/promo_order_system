# flake8: noqa
import os

import environ

env = environ.Env(
    ALLOWED_HOSTS=(list, []),
    SECRET_KEY=(str, ""),
    SENTRY_DSN=(str, ""),
    USING_S3_STORAGE=(bool, False),
)

SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")

ROOT_URLCONF = "apps.urls"

# Django settings
from .inc_django.applications import *  # noqa
from .inc_django.auth import *  # noqa
from .inc_django.caches import *  # noqa
from .inc_django.databases import *  # noqa
from .inc_django.languages import *  # noqa
from .inc_django.logging import *  # noqa
from .inc_django.media import *  # noqa
from .inc_django.middleware import *  # noqa
from .inc_django.security import *  # noqa
from .inc_django.static import *  # noqa
from .inc_django.templates import *  # noqa
from .inc_django.tz import *  # noqa

# 3-rd party tools
from .inc_other.celery_config import *  # noqa
from .inc_other.ckeditor import *  # noqa
from .inc_other.constance import *  # noqa
from .inc_other.cors import *  # noqa
from .inc_other.drf import *  # noqa
from .inc_other.fcm_django import *  # noqa
from .inc_other.jwt import *  # noqa
from .inc_other.swagger import *  # noqa
