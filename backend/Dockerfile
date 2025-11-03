# backend/Dockerfile
FROM python:3.11-slim

# Sistemde temel bağımlılıklar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Geliştirme sırasında host kodunu mount edeceğiz (COPY yok)
# Böylece her kod değişikliği container içinde anında görünür

# Django otomatik reload
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=osym_ai.settings
ENV DEBUG=1

# Başlatma komutu
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
RUN apt update && apt install -y postgresql-client