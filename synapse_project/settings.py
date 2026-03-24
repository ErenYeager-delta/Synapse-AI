"""
Django settings for Synapse AI.
FIX: Replaced djongo ENGINE with SQLite. MongoDB accessed via PyMongo directly.
"""
import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from django.core.management.utils import get_random_secret_key

logger = logging.getLogger(__name__)

# ── Load .env from project root (same folder as manage.py) ───
_env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=_env_path, override=True)

_key = os.getenv('GEMINI_API_KEY', '')
logger.info("[Synapse] .env loaded from: %s", _env_path)
logger.info("[Synapse] .env file exists: %s", _env_path.exists())
logger.info("[Synapse] GEMINI_API_KEY loaded: %s", 'YES' if _key else 'NO')

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core settings ────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY', '') or get_random_secret_key()
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://127.0.0.1:8000',
]

# ── Security headers ─────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ── Upload limits ────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB

# ── Applications ─────────────────────────────────────────────
INSTALLED_APPS = [
    'daphne',  # Must be first for ASGI
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'chat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'synapse_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'synapse_project.wsgi.application'
ASGI_APPLICATION = 'synapse_project.asgi.application'

# ── Database (SQLite replaces djongo) ────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 600,
    }
}

import dj_database_url
_db_from_env = dj_database_url.config(conn_max_age=600)
if _db_from_env:
    DATABASES['default'].update(_db_from_env)

if DEBUG:
    DJANGO_ALLOW_ASYNC_UNSAFE = True

# ── MongoDB (accessed directly via PyMongo in mongo_store.py) ─
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/synapse_mongo')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'synapse_mongo')

# ── Redis / fallback to LocMem ───────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')

try:
    import redis as _redis
    _r = _redis.from_url(REDIS_URL, socket_connect_timeout=1)
    _r.ping()
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
            'TIMEOUT': 3600,
        }
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        },
    }
except Exception:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 3600,
        }
    }
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
    }

# ── Session engine (use cache backend for performance) ───────
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# ── Auth password validators ─────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ─────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N = True
USE_TZ   = True

# ── Static files ─────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Auth redirects ───────────────────────────────────────────
LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ── Gemini API keys ──────────────────────────────────────────
GEMINI_API_KEY  = os.getenv('GEMINI_API_KEY', '')
GEMINI_API_KEYS = os.getenv('GEMINI_API_KEYS', GEMINI_API_KEY).split(',')
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS if k.strip()]

if not GEMINI_API_KEYS:
    logger.warning(
        "[Synapse] No GEMINI_API_KEYS configured. "
        "AI features will be unavailable until keys are set in .env"
    )

MAX_USERS = 10

# ── EmailJS configuration ────────────────────────────────────
EMAILJS_SERVICE_ID  = os.getenv('EMAILJS_SERVICE_ID')
EMAILJS_TEMPLATE_ID = os.getenv('EMAILJS_TEMPLATE_ID')
EMAILJS_PUBLIC_KEY  = os.getenv('EMAILJS_PUBLIC_KEY')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Logging configuration ────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'synapse_project': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}