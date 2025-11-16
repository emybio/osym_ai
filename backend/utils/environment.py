import os
import sys
from pathlib import Path

def detect_environment():
    """
    Otomatik olarak development/production ortamını tespit eder
    """

    # .env dosyasından oku
    env_file = Path(__file__).parent.parent / '.env'

    # Environment variable'ları kontrol et
    environment = os.getenv('ENVIRONMENT', '').lower()

    if environment:
        return environment

    # Eğer .env dosyası varsa ve içinde production belirtilmişse
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('ENVIRONMENT=production'):
                    return 'production'

    # Development varsayılan
    return 'development'

def get_python_executable():
    """
    Mevcut ortama göre doğru Python executable'ı döner
    """
    environment = detect_environment()

    if environment == 'development':
        # Sanal ortamı kontrol et
        venv_paths = [
            '../env/Scripts/python.exe',  # Windows
            '../env/bin/python',          # Linux/Mac
            'env/Scripts/python.exe',     # Windows (farklı path)
            'env/bin/python',             # Linux/Mac (farklı path)
        ]

        base_dir = Path(__file__).parent.parent

        for venv_path in venv_paths:
            full_path = base_dir / venv_path
            if full_path.exists():
                return str(full_path)

        # Global Python
        return sys.executable

    # Production için container'daki Python
    return 'python3'

def run_django_command(command):
    """
    Ortama uygun Django komutu çalıştırır
    """
    python_exe = get_python_executable()
    full_command = f"{python_exe} manage.py {command}"

    print(f"🔧 Running: {full_command}")
    print(f"📍 Environment: {detect_environment()}")
    print(f"🐍 Python: {python_exe}")

    return os.system(full_command)

# Kullanım için shortcut fonksiyonlar
def makemigrations(app_name=None):
    app_arg = f" {app_name}" if app_name else ""
    return run_django_command(f"makemigrations{app_arg}")

def migrate():
    return run_django_command("migrate")

def runserver(port='8000'):
    return run_django_command(f"runserver {port}")

def createsuperuser():
    return run_django_command("createsuperuser")

def collectstatic():
    return run_django_command("collectstatic --noinput")