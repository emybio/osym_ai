from pathlib import Path


# SQLite optimization settings for osym_ai project
# Add these to your settings.py DATABASES configuration
BASE_DIR = Path(__file__).resolve().parent

SQLITE_OPTIMIZATION = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db.sqlite3',
    'OPTIONS': {
        'timeout': 20,  # 20 seconds timeout
        'check_same_thread': False,  # Allow multi-threading
        'isolation_level': None,  # Autocommit mode
    },
    'CONN_MAX_AGE': 60,  # Connection pooling
}

# Also add to settings.py:
# DATABASES = {'default': SQLITE_OPTIMIZATION}