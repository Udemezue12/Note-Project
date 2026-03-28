import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv
from notes.env import (
    ALLOW_DEBUG,
    ALLOWED_ORIGINS,
    CORS_ALLOWED_HOSTS,
    CSRF_TRUSTED_HOSTS,
    JWT_SECRET_KEY,
    REDIS_URL,
    ENV,
    CLOUDINARY_API_KEY, CLOUDINARY_CLOUD_NAME, CLOUDINARY_SECRET_KEY
)
import cloudinary
import cloudinary.uploader
import cloudinary.api


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

SECRET_KEY = JWT_SECRET_KEY


DEBUG = True

ALLOWED_HOSTS = ALLOWED_ORIGINS


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    'cloudinary_storage',
    'cloudinary',
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular_sidecar",
    "django_prometheus",
    "rest_framework",
    "django_extensions",
    "notes",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "notes.middleware.exception_middleware.GlobalExceptionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "notes.middleware.ensure_response_middleware.EnsureRenderedMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
ROOT_URLCONF = "note_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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


cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_SECRET_KEY
)


WSGI_APPLICATION = "note_app.wsgi.application"
ASGI_APPLICATION = "note_app.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 7},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "notes.password_validator.StrongPasswordValidator",
    },
]


PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 10,
            },
        },
    }
}


STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
AUTH_USER_MODEL = "notes.CustomUser"

CELERY_BROKER_URL = REDIS_URL


CELERY_RESULT_BACKEND = REDIS_URL

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_USE_SSL = None
CELERY_REDIS_BACKEND_USE_SSL = None

CELERY_BROKER_POOL_LIMIT = 5
CELERY_REDIS_MAX_CONNECTIONS = 10
CELERY_WORKER_CONCURRENCY = 1

APPEND_SLASH = False
CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_HOSTS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = CORS_ALLOWED_HOSTS

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"


SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "security_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "logs/security.log"),
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "security": {
            "handlers": ["security_file", "console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

if ENV == "production":
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    DATABASES = {
        "default": dj_database_url.parse(
            os.getenv("DATABASE_URL", ""),
            conn_max_age=600,
            ssl_require=True,
        )
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }

    PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]
    THROTTLE_RATES = {
        "anon": "10/minute",
        "user": "60/minute",
        "burst": "5/second",
        "sustained": "500/day",
        "auth": "5/minute",
    }
    RENDERERS = [
        "rest_framework.renderers.JSONRenderer",
    ]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    THROTTLE_RATES = {
        "anon": "1000/minute",
        "user": "1000/minute",
        "burst": "100/second",
        "sustained": "10000/day",
        "auth": "100/minute",
    }

    RENDERERS = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
    PERMISSION_CLASSES = ["rest_framework.permissions.AllowAny"]

    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": RENDERERS,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "notes.middleware.custom_jwt_middleware.CustomJWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": THROTTLE_RATES,
    "DEFAULT_PERMISSION_CLASSES": PERMISSION_CLASSES,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "My Awesome API",
    "DESCRIPTION": "API with all the features",
    "VERSION": "2.0.0",
    # ... other settings
}
