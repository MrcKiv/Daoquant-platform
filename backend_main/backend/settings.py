import os
from pathlib import Path

from .env import env_bool, env_list, get_database_config


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "*")

ENABLE_TRADE_MODULE = env_bool("ENABLE_TRADE_MODULE", True)
ENABLE_WHITENOISE = env_bool("ENABLE_WHITENOISE", False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "api.apps.ApiConfig",
    "corsheaders",
    "user",
    "strategy",
    "stock_analysis",
]

if ENABLE_TRADE_MODULE:
    INSTALLED_APPS.append("ths_trade")

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
]

if ENABLE_WHITENOISE:
    MIDDLEWARE.append("whitenoise.middleware.WhiteNoiseMiddleware")

MIDDLEWARE += [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

default_frontend_origins = ",".join(
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.2.92:5173",
    ]
)

CORS_ALLOWED_ORIGINS = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default_frontend_origins,
)
CORS_ORIGIN_WHITELIST = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = (
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "VIEW",
)
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "Authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "X-CSRFToken",
)

SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", SESSION_COOKIE_SAMESITE)
CSRF_COOKIE_DOMAIN = os.getenv("CSRF_COOKIE_DOMAIN") or None
CSRF_COOKIE_HTTPONLY = env_bool("CSRF_COOKIE_HTTPONLY", False)
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default_frontend_origins,
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {
    "default": get_database_config(),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if ENABLE_WHITENOISE:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", True)

BACKTEST_SCHEDULE_TIME = os.getenv("BACKTEST_SCHEDULE_TIME", "16:58")
