# Development Setup Guide

## Otomatik Ortam Tespiti

Bu proje otomatik olarak development ve production ortamlarını tespit eder:

### Environment Değişkenleri
```bash
# .env dosyası
ENVIRONMENT=development          # veya production
DEBUG=1                         # development'de 1, production'da 0
```

### Development Mode'da Çalıştırma

#### Method 1: Otomatik Script (Tavsiye Edilen)
```bash
# Development server'ı başlat
python manage_dev.py run

# Migration'ları yap
python manage_dev.py migrate

# Environment kontrolü yap
python manage_dev.py env
```

#### Method 2: Manuel (Linux/Mac)
```bash
# Sanal ortamı aktifleştir
source ../env/bin/activate

# Migration'ları yap
python manage.py makemigrations
python manage.py migrate

# Server'ı başlat
python manage.py runserver
```

#### Method 3: Manuel (Windows)
```bash
# Virtual environment'de Python'ı doğrudan kullan
../env/Scripts/python.exe manage.py makemigrations
../env/Scripts/python.exe manage.py migrate
../env/Scripts/python.exe manage.py runserver
```

## Ortam Tespiti Mantığı

1. **Önce `.env` dosyasını kontrol eder**
2. **`ENVIRONMENT` variable'ını okur**
3. **Sanal ortamı tespit eder**
4. **Doğru Python executable'ı seçer**

## Database Konfigürasyonu

### Development (Default)
- SQLite kullanılır (`db.sqlite3`)
- Migration'lar otomatik oluşturulur

### Production
- PostgreSQL kullanılır
- `.env` dosyasında PostgreSQL config gereklir

```bash
# Production için .env
ENVIRONMENT=production
POSTGRES_DB=osym
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=db
DATABASE_URL=postgres://postgres:password@db:5432/osym
```

## Common Commands

```bash
# Yeni model ekledikten sonra
python manage_dev.py migrate

# Superuser oluştur
python manage_dev.py superuser

# Django shell
python manage_dev.py shell

# Migration'ları reset'le
python manage_dev.py reset
```

## Troubleshooting

### "No module named" Hatası
```bash
# .env dosyasını kontrol et
cat .env

# Environment'ı kontrol et
python manage_dev.py env
```

### Sanal Ortam Bulunamadı
```bash
# Sanal ortam yolu kontrol et
find ../ -name "python.exe" 2>/dev/null  # Windows
find ../ -name "python" 2>/dev/null      # Linux/Mac
```