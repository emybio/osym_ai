# =============================================
# BACKEND DOCKERFILE (OFFICE OPTIMIZED)
# =============================================
FROM python:3.11-slim

# Sistemde temel bağımlılıklar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Sertifika güven problemi yaşayan ofisler için
ENV PIP_NO_VERIFY_CERTS=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Çalışma dizini
WORKDIR /app

# Requirements önce kopyalanır (docker cache avantajı)
COPY requirements.txt .

# Ofis ortamındaki SSL hatalarını bypass ederek install
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt

# Django ayarları
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=osym_ai.settings

# PostgreSQL client (pg_dump, psql vs)
RUN apt-get update && apt-get install -y postgresql-client

# Backend kodlarını docker-compose sırasında mount edeceğiz
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "osym_ai.wsgi:application"]
