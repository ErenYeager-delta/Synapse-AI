"""
Django settings for Synapse AI.
FIX: Replaced djongo ENGINE with SQLite. MongoDB accessed via PyMongo directly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path as _Path

# FIX: Explicitly load .env from project root (same folder as manage.py)
_env_path = _Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=_env_path, override=True)

import sys as _sys
_key = os.getenv('GEMINI_API_KEY', '')
print(f"[Synapse] .env loaded from: {_env_path}")
print(f"[Synapse] .env file exists: {_env_path.exists()}")
print(f"[Synapse] GEMINI_API_KEY loaded: {'YES (' + _key[:8] + '...)' if _key else 'NO - .env not found!'}")

# Environment loaded securely.

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://127.0.0.1:8000',
]
# FIX: Handle Railway HTTPS Proxy & Security
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Production Security
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000 # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_COOKIE_HTTPONLY = False # Must be False for JS to read it
else:
    CSRF_COOKIE_HTTPONLY = False

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
ASGI_APPLICATION  = 'synapse_project.asgi.application'

# ── FIX 1: SQLite replaces djongo ────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DJANGO_ALLOW_ASYNC_UNSAFE = True

# MongoDB URI used directly via PyMongo (mongo_store.py)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/synapse_mongo')

# Redis / fallback to LocMem
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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N = True
USE_TZ   = True

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'

_primary_key = os.getenv('GEMINI_API_KEY', '').strip()
_pool_keys = os.getenv('GEMINI_API_KEYS', '').split(',')
# Combine and deduplicate
_all_keys = ([_primary_key] if _primary_key else []) + [k.strip() for k in _pool_keys if k.strip()]
GEMINI_API_KEYS = list(dict.fromkeys(_all_keys))
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ''

MAX_USERS = 10

EMAILJS_SERVICE_ID  = os.getenv('EMAILJS_SERVICE_ID')
EMAILJS_TEMPLATE_ID = os.getenv('EMAILJS_TEMPLATE_ID')
EMAILJS_PUBLIC_KEY  = os.getenv('EMAILJS_PUBLIC_KEY')

AUTHENTICATION_BACKENDS = [
    'chat.mongo_auth.MongoAuthBackend',
    'django.contrib.auth.backends.ModelBackend', # Keep as fallback
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
