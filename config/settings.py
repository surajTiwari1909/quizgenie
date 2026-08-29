from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    APP_NAME=(str, "AI Quiz Game API"),
    APP_ENV=(str, "development"),
    APP_LOG_LEVEL=(str, "INFO"),
    DJANGO_DEBUG=(bool, True),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(BASE_DIR / ".env")

APP_NAME = env("APP_NAME")
APP_ENV = env("APP_ENV")
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

if APP_ENV == "production":
    if SECRET_KEY == "unsafe-development-key-change-me":
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")
    if DEBUG:
        raise ImproperlyConfigured("DJANGO_DEBUG must be false in production")
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "core",
    "documents",
    "games",
    "profiles",
    "quizzes",
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://quiz_user:quiz_password@localhost:5434/quiz_game",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DOCUMENT_ROOT = BASE_DIR / "private_documents"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {"document_upload": "10/hour"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_TRACK_STARTED = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://localhost:6379/1"),
    }
}

DOCUMENT_MAX_COUNT_PER_USER = env.int("DOCUMENT_MAX_COUNT_PER_USER", default=20)
DOCUMENT_MAX_FILE_SIZE = env.int("DOCUMENT_MAX_FILE_SIZE", default=10 * 1024 * 1024)
DOCUMENT_MAX_PAGE_COUNT = env.int("DOCUMENT_MAX_PAGE_COUNT", default=250)
DOCUMENT_MAX_EXTRACTED_CHARACTERS = env.int(
    "DOCUMENT_MAX_EXTRACTED_CHARACTERS",
    default=1_000_000,
)
DOCUMENT_MAX_TOTAL_BYTES_PER_USER = env.int(
    "DOCUMENT_MAX_TOTAL_BYTES_PER_USER",
    default=100 * 1024 * 1024,
)
DOCUMENT_RETENTION_DAYS = env.int("DOCUMENT_RETENTION_DAYS", default=30)
DOCUMENT_PROCESSING_SOFT_TIME_LIMIT = env.int(
    "DOCUMENT_PROCESSING_SOFT_TIME_LIMIT",
    default=60,
)
DOCUMENT_PROCESSING_TIME_LIMIT = env.int("DOCUMENT_PROCESSING_TIME_LIMIT", default=75)
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_QUIZ_MODEL = env("GROQ_QUIZ_MODEL", default="openai/gpt-oss-120b")
QUIZ_GENERATOR_CLASS = env(
    "QUIZ_GENERATOR_CLASS",
    default="quizzes.providers.GroqQuestionGenerator",
)
QUIZ_MAX_REGENERATION_ATTEMPTS = env.int(
    "QUIZ_MAX_REGENERATION_ATTEMPTS",
    default=2,
)
QUIZ_GENERATION_REQUEST_TIMEOUT = env.float(
    "QUIZ_GENERATION_REQUEST_TIMEOUT",
    default=60.0,
)
QUIZ_GENERATION_SOFT_TIME_LIMIT = env.int(
    "QUIZ_GENERATION_SOFT_TIME_LIMIT",
    default=150,
)
QUIZ_GENERATION_TIME_LIMIT = env.int("QUIZ_GENERATION_TIME_LIMIT", default=180)
CLAMAV_ENABLED = env.bool("CLAMAV_ENABLED", default=True)
CLAMAV_HOST = env("CLAMAV_HOST", default="localhost")
CLAMAV_PORT = env.int("CLAMAV_PORT", default=3310)
CLAMAV_TIMEOUT = env.float("CLAMAV_TIMEOUT", default=15.0)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("APP_LOG_LEVEL")},
}
