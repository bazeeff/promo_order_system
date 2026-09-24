import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("SQL_DATABASE", "postgres"),
        "USER": os.environ.get("SQL_USER", "postgres"),
        "HOST": os.environ.get("SQL_HOST", "db"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "postgres"),
        "PORT": 5432,
    },
}
