# backend/Dockerfile
FROM python:3.11-slim

# Sistemde temel bağımlılıklar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir  --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Geliştirme sırasında host kodunu mount edeceğiz (COPY yok)
# Böylece her kod değişikliği container içinde anında görünür

# Django settings
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=osym_ai.settings

# Production için varsayılan komut (development'da docker-compose override eder)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "osym_ai.wsgi:application"]
RUN apt update && apt install -y postgresql-client