# API Keys Setup Guide

## 🔑 Gerekli API Key'ler

Hybrid AI Provider System'i kullanmak için aşağıdaki API key'lere ihtiyacınız var:

---

## 1. OpenAI API Key (Zorunlu)

### Nereden Alınır?
https://platform.openai.com/api-keys

### Adımlar:
1. OpenAI hesabınıza giriş yapın
2. API Keys sayfasına gidin
3. "Create new secret key" butonuna tıklayın
4. Key'i kopyalayın (bir daha gösterilmeyecek!)

### Kullanım:
- GPT-4o modeli (karmaşık görsel sorular)
- GPT-4o-mini modeli (metin soruları)

### Maliyet:
- GPT-4o: ~$0.015/soru
- GPT-4o-mini: ~$0.002/soru

### .env Ayarı:
```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
```

---

## 2. AbacusAI API Key (Önerilen)

### Nereden Alınır?
https://abacus.ai

### Adımlar:
1. AbacusAI hesabı oluşturun
2. Dashboard'a gidin
3. API Keys bölümünden yeni key oluşturun
4. Key'i kopyalayın

### Kullanım:
- Claude modelleri (basit görsel sorular)
- DeepSeek modeli (metin soruları)

### Maliyet:
- Claude Sonnet: ~$0.012/soru
- DeepSeek: ~$0.0003/soru

### .env Ayarı:
```bash
ABACUS_API_KEY=...
CLAUDE_MODEL=claude-3-5-sonnet-20241022
DEEPSEEK_MODEL=deepseek-chat
```

### Avantajları:
- Tek key ile hem Claude hem DeepSeek kullanılabilir
- OpenAI'dan daha ucuz
- Yüksek rate limit

---

## 3. Opsiyonel API Key'ler

### ZAI API Key (Geriye dönük uyumluluk)
```bash
ZAI_API_KEY=...
ZAI_MODEL=glm-4-plus
```

### Anthropic API Key (Direkt Claude kullanımı)
```bash
ANTHROPIC_API_KEY=...
```

---

## 📝 .env Dosyası Örneği

```bash
# Security Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
POSTGRES_DB=osym
POSTGRES_USER=postgres
POSTGRES_PASSWORD=osym
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgres://postgres:osym@db:5432/osym

# AI Service API Keys
OPENAI_API_KEY=sk-proj-...
ABACUS_API_KEY=...

# AI Models
OPENAI_MODEL=gpt-4o-mini
CLAUDE_MODEL=claude-3-5-sonnet-20241022
DEEPSEEK_MODEL=deepseek-chat

# Legacy (optional)
ZAI_API_KEY=...
ZAI_MODEL=glm-4-plus
ANTHROPIC_API_KEY=...

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Development/Production Environment
ENVIRONMENT=development

IGNORE_SSL=True
NODE_TLS_REJECT_UNAUTHORIZED=0
```

---

## 🧪 Test Etme

### 1. Backend Test
```bash
cd backend
python test_hybrid_system.py
```

### 2. Frontend Test
1. Uygulamayı başlatın
2. Sol menüden "AI Provider Test" sayfasına gidin
3. "Test All" butonuna tıklayın
4. Provider'ların bağlantı durumunu görün

### 3. API Test
```bash
# Provider test
curl http://localhost:8000/api/quiz/ai/test-providers/

# Soru üretimi
curl -X POST http://localhost:8000/api/quiz/questions/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Matematik",
    "topic": "Parabol",
    "difficulty": "Orta"
  }'

# Maliyet tahmini
curl -X POST http://localhost:8000/api/quiz/ai/cost-estimate/ \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Matematik",
    "num_questions": 1000
  }'

# Metrikler
curl http://localhost:8000/api/quiz/ai/provider-metrics/
```

---

## 💰 Maliyet Karşılaştırması

### 10,000 Soru Üretimi (Matematik)

| Senaryo | Maliyet | Tasarruf |
|---------|---------|----------|
| Sadece GPT-4o | $150 | - |
| Sadece Claude Sonnet | $120 | 20% |
| Sadece DeepSeek | $3 | 98% |
| **Hybrid (Önerimiz)** | **$60** | **60%** |

### Hybrid Dağılım (Matematik)
- 6,000 metin × DeepSeek = $1.80
- 2,500 basit görsel × Claude = $30
- 1,500 karmaşık görsel × GPT-4o = $22.50
- **Toplam: $54.30**

---

## 🔒 Güvenlik

### API Key'leri Koruma
1. ✅ `.env` dosyasını `.gitignore`'a ekleyin
2. ✅ Production'da environment variables kullanın
3. ✅ Key'leri asla kod içine yazmayın
4. ✅ Düzenli olarak key'leri rotate edin

### Rate Limiting
- OpenAI: 10,000 requests/min (Tier 2)
- AbacusAI: 100,000 requests/min
- DeepSeek: 60 requests/min

### Best Practices
```python
# ✅ Doğru
api_key = os.getenv("OPENAI_API_KEY")

# ❌ Yanlış
api_key = "sk-proj-..."
```

---

## 🚨 Sorun Giderme

### "No AI providers initialized" Hatası
**Çözüm:** En az bir API key tanımlı olmalı
```bash
# .env dosyasını kontrol edin
OPENAI_API_KEY=sk-proj-...
# veya
ABACUS_API_KEY=...
```

### "Provider connection failed" Hatası
**Çözüm:** API key'in geçerli olduğundan emin olun
```bash
# Test edin
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Rate limit exceeded" Hatası
**Çözüm:** Daha ucuz provider kullanın veya bekleyin
```python
# DeepSeek kullanın (daha yüksek limit)
force_provider='deepseek'
```

---

## 📞 Destek

### OpenAI
- Dokümantasyon: https://platform.openai.com/docs
- Destek: https://help.openai.com

### AbacusAI
- Dokümantasyon: https://docs.abacus.ai
- Destek: support@abacus.ai

### DeepSeek
- Dokümantasyon: https://platform.deepseek.com/docs
- Destek: support@deepseek.com

---

## 📚 İlgili Dokümantasyon

- [Hybrid AI Provider System](HYBRID_AI_PROVIDER_SYSTEM.md)
- [Question Validation System](QUESTION_VALIDATION_README.md)
- [Setup Report](QUESTION_VALIDATION_SETUP_REPORT.md)

---

**Son Güncelleme:** 2024  
**Durum:** ✅ Production Ready
