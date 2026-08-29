from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def env_value(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


DEBUG = env_bool("DEBUG", True)
SECRET_KEY = env_value("DJANGO_SECRET_KEY") or env_value("SECRET_KEY") or "dev-only-secret-key-change-me"

if not DEBUG and not env_value("DJANGO_SECRET_KEY") and not env_value("SECRET_KEY"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production mode.")

ADMIN_BOT_TOKEN = env_value("ADMIN_BOT_TOKEN")
ADMIN_BOT_WEBHOOK_SECRET = env_value("ADMIN_BOT_WEBHOOK_SECRET")
PUBLIC_BASE_URL = env_value("PUBLIC_BASE_URL")
SITE_DOMAIN = env_value("SITE_DOMAIN")
SITE_URL = env_value("SITE_URL", PUBLIC_BASE_URL or SITE_DOMAIN or ("http://localhost:8000" if DEBUG else "https://tinchlik24.uz"))

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver,tinchlik24.uz,www.tinchlik24.uz,.vercel.app",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "https://tinchlik24.uz,https://www.tinchlik24.uz",
)

SITE_NAME = env_value("SITE_NAME", "TINCHLIK")
DEFAULT_FROM_EMAIL = env_value("DEFAULT_FROM_EMAIL", "noreply@tinchlik24.uz")
EMAIL_BACKEND = env_value("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env_value("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = env_value("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env_value("EMAIL_HOST_PASSWORD")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMIN_PHONE_NUMBER = env_value("ADMIN_PHONE_NUMBER", "+998991649848")

DEFAULT_ADMIN_TELEGRAM_IDS = [8461653028]
ADMIN_TELEGRAM_IDS = [
    int(x.strip())
    for x in (env_value("ADMIN_TELEGRAM_IDS") or "").split(",")
    if x.strip()
]
if not ADMIN_TELEGRAM_IDS:
    ADMIN_TELEGRAM_IDS = DEFAULT_ADMIN_TELEGRAM_IDS
else:
    ADMIN_TELEGRAM_IDS = list(dict.fromkeys(DEFAULT_ADMIN_TELEGRAM_IDS + ADMIN_TELEGRAM_IDS))

MAIN_ADMIN_USERNAME = env_value("MAIN_ADMIN_USERNAME", "admin")
MAIN_ADMIN_PASSWORD = env_value("MAIN_ADMIN_PASSWORD")
BOT_LOGIN_MAX_ATTEMPTS = int(os.getenv("BOT_LOGIN_MAX_ATTEMPTS", "5"))
BOT_LOGIN_BLOCK_MINUTES = int(os.getenv("BOT_LOGIN_BLOCK_MINUTES", "15"))

TELEGRAM_GATEWAY_TOKEN = env_value("TELEGRAM_GATEWAY_TOKEN")
TELEGRAM_GATEWAY_RESEND_COOLDOWN_SECONDS = int(os.getenv("TELEGRAM_GATEWAY_RESEND_COOLDOWN_SECONDS", "60"))
TELEGRAM_GATEWAY_CODE_TTL_SECONDS = int(os.getenv("TELEGRAM_GATEWAY_CODE_TTL_SECONDS", "300"))
PENDING_REGISTRATION_EXPIRE_MINUTES = int(os.getenv("PENDING_REGISTRATION_EXPIRE_MINUTES", "30"))
VALIDATION_LINK_TTL_MINUTES = int(os.getenv("VALIDATION_LINK_TTL_MINUTES", "10"))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'core',
    'accounts',
    'chat',
    'market.apps.MarketConfig',
    'adminpanel',
]

try:
    import channels  # noqa: F401
except Exception:
    pass
else:
    INSTALLED_APPS.insert(0, 'channels')

try:
    import daphne  # noqa: F401
except Exception:
    pass
else:
    INSTALLED_APPS.insert(0, 'daphne')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.LastSeenMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=DATABASE_URL.startswith('postgres'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/profile/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REDIRECT_EXEMPT = [r'^/health/$']  # optional; harmless if route exists
    USE_X_FORWARDED_HOST = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ONLINE_THRESHOLD_MINUTES = 5
VERIFICATION_CODE_TTL_MINUTES = 5
