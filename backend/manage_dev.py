#!/usr/bin/env python3
"""
Development ortamı için Django yönetim script'i
Otomatik olarak doğru Python ve sanal ortamı tespit eder
"""

import sys
import os
from pathlib import Path

# Proje ana dizinini ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Environment utilities
from utils.environment import detect_environment, get_python_executable

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'help'

    print("OSYM AI Development Manager")
    print(f"Working Directory: {project_root}")
    print(f"Python: {get_python_executable()}")
    print(f"Environment: {detect_environment()}")
    print("-" * 40)

    if command == 'run':
        # Development server'ı başlat
        os.system(f"{get_python_executable()} manage.py runserver 8000")

    elif command == 'migrate':
        # Migration'ları yap
        os.system(f"{get_python_executable()} manage.py makemigrations")
        os.system(f"{get_python_executable()} manage.py migrate")

    elif command == 'reset':
        # Migration'ları reset'le
        os.system(f"{get_python_executable()} manage.py migrate quiz zero")
        os.system(f"{get_python_executable()} manage.py makemigrations quiz")
        os.system(f"{get_python_executable()} manage.py migrate")

    elif command == 'shell':
        # Django shell
        os.system(f"{get_python_executable()} manage.py shell")

    elif command == 'superuser':
        # Superuser oluştur
        os.system(f"{get_python_executable()} manage.py createsuperuser")

    elif command == 'env':
        # Environment bilgisi göster
        print(f"Environment: {detect_environment()}")
        print(f"Python: {get_python_executable()}")
        print(f"Django Settings: osym_ai.settings")

    else:
        print("Usage:")
        print("  python manage_dev.py run      - Start development server")
        print("  python manage_dev.py migrate  - Run migrations")
        print("  python manage_dev.py reset    - Reset migrations")
        print("  python manage_dev.py shell    - Django shell")
        print("  python manage_dev.py superuser - Create superuser")
        print("  python manage_dev.py env      - Show environment info")

if __name__ == '__main__':
    main()