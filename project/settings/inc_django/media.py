import os

from ..common import BASE_DIR, env

if env("USING_S3_STORAGE"):
    DEFAULT_FILE_STORAGE = "apps.helpers.storages.MediaStorage"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"
