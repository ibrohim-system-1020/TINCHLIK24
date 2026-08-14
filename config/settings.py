from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "True") == "True"

USER_BOT_TOKEN = os.getenv("USER_BOT_TOKEN", "")
USER_BOT_USERNAME = os.getenv("USER_BOT_USERNAME", "")
USER_BOT_WEBHOOK_SECRET = os.getenv("USER_BOT_WEBHOOK_SECRET", "")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")
ADMIN_BOT_WEBHOOK_SECRET = os.getenv("ADMIN_BOT_WEBHOOK_SECRET", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "")
DEFAULT_ADMIN_TELEGRAM_IDS = [8461653028]
ADMIN_TELEGRAM_IDS = [
    int(x)
    for x in (os.getenv("ADMIN_TELEGRAM_IDS", "") or "").split(",")
    if x.strip().isdigit()
]
if not ADMIN_TELEGRAM_IDS:
    ADMIN_TELEGRAM_IDS = DEFAULT_ADMIN_TELEGRAM_IDS
else:
    ADMIN_TELEGRAM_IDS = list(dict.fromkeys(DEFAULT_ADMIN_TELEGRAM_IDS + ADMIN_TELEGRAM_IDS))
MAIN_ADMIN_USERNAME = os.getenv("MAIN_ADMIN_USERNAME", "admin")
MAIN_ADMIN_PASSWORD = os.getenv("MAIN_ADMIN_PASSWORD", "")
BOT_LOGIN_MAX_ATTEMPTS = int(os.getenv("BOT_LOGIN_MAX_ATTEMPTS", "5"))
BOT_LOGIN_BLOCK_MINUTES = int(os.getenv("BOT_LOGIN_BLOCK_MINUTES", "15"))

TELEGRAM_GATEWAY_TOKEN = os.getenv("TELEGRAM_GATEWAY_TOKEN", "")
TELEGRAM_GATEWAY_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("TELEGRAM_GATEWAY_RESEND_COOLDOWN_SECONDS", "60")
)
TELEGRAM_GATEWAY_CODE_TTL_SECONDS = int(
    os.getenv("TELEGRAM_GATEWAY_CODE_TTL_SECONDS", "300")
)
PENDING_REGISTRATION_EXPIRE_MINUTES = int(
    os.getenv("PENDING_REGISTRATION_EXPIRE_MINUTES", "30")
)


SECRET_KEY = 'django-insecure-z8hw^g@7+sy3f-$+ysr@7aj_4olls3!7eorkc8zhd(-l38#gmx'

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".vercel.app",
    "tinchlik.online",
    "www.tinchlik.online",
]



INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "core",
    "accounts",
    "chat",

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "accounts.middleware.LastSeenMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        "DIRS": [BASE_DIR / "templates"],
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
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/profile/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'uz'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ONLINE_THRESHOLD_MINUTES = 5
VERIFICATION_CODE_TTL_MINUTES = 5
