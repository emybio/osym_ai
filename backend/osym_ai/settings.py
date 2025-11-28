import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================
# PATH CONFIGURATION
# ============================================================

# settings.py: backend/osym_ai/settings.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent   # D:/Projeler/osym_ai
BACKEND_DIR = Path(__file__).resolve().parent.parent           # D:/Projeler/osym_ai/backend

# Django BASE_DIR olarak proje kökü kullanılacak
BASE_DIR = PROJECT_ROOT

# ============================================================
# DJANGO_ENV OTOMATİK SEÇİM SİSTEMİ
# ============================================================

# Öncelik sırası:
# 1. DJANGO_ENV sistemden gelmişse (Docker override) -> onu kullan
# 2. Aksi halde bilgisayar adına göre otomatik seç

explicit_env = os.getenv("DJANGO_ENV")

if explicit_env:
    DJANGO_ENV = explicit_env
else:
    computer = os.getenv("COMPUTERNAME", "").lower()

    if computer == "s68edenizer":
        DJANGO_ENV = "office_development"
    elif computer == "elifnarin":
        DJANGO_ENV = "home_development"
    else:
        DJANGO_ENV = "home_development"

# ============================================================
# DJANGO_ENV → .env DOSYA HARİTASI
# ============================================================

ENV_FILE_MAP = {
    # Django runserver (development)
    "home_development":   PROJECT_ROOT / ".env.dev",
    "office_development": PROJECT_ROOT / ".env.office.dev",

    # Docker (production ortamları)
    "production":         PROJECT_ROOT / ".env.prod",

    # Ofis docker özel senaryosu
    "office_docker":      BACKEND_DIR / ".env.office.prod",
}

# Eğer DJANGO_ENV bilinmeyen ise ev dev'e düş
env_file_path = ENV_FILE_MAP.get(DJANGO_ENV, PROJECT_ROOT / ".env.dev")

# ============================================================
# .env DOSYASINI YÜKLE
# ============================================================

print(f"DJANGO_ENV = {DJANGO_ENV}")
print(f"Loading environment from: {env_file_path}")
print(f"File exists: {env_file_path.exists()}")

if env_file_path.exists():
    load_dotenv(env_file_path)
else:
    raise RuntimeError(f".env file not found: {env_file_path}")

# ============================================================
# BASIC SETTINGS
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-key")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT != "production"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    os.getenv("LOCAL_IP", ""),
    os.getenv("SERVER_IP", ""),
]
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]

# ============================================================
# CORS / CSRF
# ============================================================

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "quiz",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "osym_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "osym_ai.wsgi.application"

# ============================================================
# DATABASE CONFIGURATION - ONLY SQLITE FOR DEVELOPMENT
# ============================================================

POSTGRES_ENVS = ["office_docker", "production"]

if DJANGO_ENV in POSTGRES_ENVS:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOST"),
            "PORT": os.getenv("POSTGRES_PORT"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
# ============================================================
# STATIC / MEDIA
# ============================================================

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ============================================================
# REDIS / CELERY
# ============================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "osym_ai",
        "TIMEOUT": 3600,
    }
}

# ============================================================
# AI API KEYS
# ============================================================

ABACUSAI_API_KEY = os.getenv("ABACUSAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAI_API_KEY = os.getenv("ZAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"