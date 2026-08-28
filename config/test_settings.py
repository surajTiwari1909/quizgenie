import os
from pathlib import Path
from tempfile import gettempdir

import environ

from .settings import *  # noqa: F403

APP_ENV = "test"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
if test_database_url := os.environ.get("TEST_DATABASE_URL"):
    DATABASES = {"default": environ.Env.db_url_config(test_database_url)}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CLAMAV_ENABLED = False
TEST_STORAGE_ROOT = Path(gettempdir()) / f"quizgenie-tests-{os.getpid()}"
MEDIA_ROOT = TEST_STORAGE_ROOT / "media"
DOCUMENT_ROOT = TEST_STORAGE_ROOT / "private_documents"
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {"document_upload": "10000/hour"},
}
