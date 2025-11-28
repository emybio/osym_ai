# Soru Doğrulama Sistemi - Akış Şeması ve Dokümantasyon

## Genel Bakış

Bu sistem, AI tarafından oluşturulan soruların matematiksel ve görsel tutarlılığını kontrol eder.

## Doğrulama Akışı

```
┌─────────────────────────────────────────────────────────────┐
│                    SORU OLUŞTURMA BAŞLA                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. AI ile Soru Üret                                         │
│     - Konu ve zorluk seviyesi belirlenir                     │
│     - AI prompt'u hazırlanır                                 │
│     - Soru metni, seçenekler ve görsel oluşturulur          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Temel Yapı Kontrolü                                      │
│     ✓ Zorunlu alanlar var mı?                               │
│     ✓ Soru metni yeterli uzunlukta mı?                      │
│     ✓ 5 seçenek var mı?                                     │
│     ✓ Doğru cevap belirtilmiş mi?                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                    ┌────┴────┐
                    │ Geçti?  │
                    └────┬────┘
                    HAYIR│    │EVET
         ┌───────────────┘    └──────────────┐
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────────────┐
│ Yeniden Üret    │                  │ 3. Soru Tipi Belirleme  │
│ (Attempt +1)    │                  │    - Parabol            │
└─────────────────┘                  │    - Geometri           │
         │                            │    - Fonksiyon Grafiği  │
         │                            │    - Genel              │
         │                            └────────┬────────────────┘
         │                                     │
         │                                     ▼
         │                            ┌─────────────────────────┐
         │                            │ 4. Özel Tip Doğrulama   │
         │                            └────────┬────────────────┘
         │                                     │
         │                    ┌────────────────┼────────────────┐
         │                    ▼                ▼                ▼
         │          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │          │   PARABOL    │  │  GEOMETRİ    │  │  FONKSİYON   │
         │          │  DOĞRULAMA   │  │  DOĞRULAMA   │  │  DOĞRULAMA   │
         │          └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
         │                 └──────────────────┼──────────────────┘
         │                                    │
         │                                    ▼
         │                   ┌─────────────────────────────────┐
         │                   │ 5. SVG İçerik Doğrulama         │
         │                   │    ✓ SVG parse edilebiliyor mu? │
         │                   │    ✓ ViewBox tanımlı mı?        │
         │                   │    ✓ Görsel elementler var mı?  │
         │                   └────────┬────────────────────────┘
         │                            │
         │                            ▼
         │                   ┌─────────────────────────────────┐
         │                   │ 6. Görsel-Metin Uyum Kontrolü   │
         │                   │    ✓ Fonksiyon tanımı uyuyor mu?│
         │                   │    ✓ Noktalar doğru mu?         │
         │                   │    ✓ Açılar doğru mu?           │
         │                   └────────┬────────────────────────┘
         │                            │
         │                            ▼
         │                   ┌─────────────────────────────────┐
         │                   │ 7. Seçenek Tutarlılığı          │
         │                   │    ✓ Boş seçenek var mı?        │
         │                   │    ✓ Doğru cevap seçeneklerde?  │
         │                   │    ✓ Tekrar eden seçenek?       │
         │                   └────────┬────────────────────────┘
         │                            │
         │                            ▼
         │                   ┌─────────────────────────────────┐
         │                   │ 8. Skor Hesaplama               │
         │                   │    Başlangıç: 100 puan          │
         │                   │    Her hata: -20 puan           │
         │                   │    Her uyarı: -5 puan           │
         │                   └────────┬────────────────────────┘
         │                            │
         │                            ▼
         │                       ┌────┴────┐
         │                       │ Skor ≥  │
         │                       │  60?    │
         │                       └────┬────┘
         │                       HAYIR│    │EVET
         │              ┌──────────────┘    └──────────────┐
         │              ▼                                   ▼
         │     ┌─────────────────┐                ┌─────────────────┐
         │     │ Attempt < 3?    │                │  SORU ONAYLANDI │
         │     └────┬────────────┘                │  Veritabanına   │
         │     EVET │    │ HAYIR                  │  Kaydet         │
         └──────────┘    │                        └─────────────────┘
                         ▼
                ┌─────────────────┐
                │  SORU REDDEDİLDİ│
                │  Loglara Kaydet │
                └─────────────────┘
```

## Parabol Sorusu Özel Doğrulama

```
┌─────────────────────────────────────────────────────────────┐
│              PARABOL SORUSU DOĞRULAMA                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Fonksiyon Çıkarma                                        │
│     Soru metninden: f(x) = ax² + bx + c                     │
│     Regex pattern'ler ile tespit                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. SVG'den Nokta Çıkarma                                    │
│     - Path elementlerini parse et                            │
│     - Koordinatları (x, y) çiftleri olarak al               │
│     - SVG koordinatlarını Kartezyen'e dönüştür              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Fonksiyondan Nokta Hesaplama                             │
│     - x değerleri için y = f(x) hesapla                     │
│     - 100 nokta örnekle (-10 ile 10 arası)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Nokta Karşılaştırma                                      │
│     - Her SVG noktası için en yakın hesaplanan noktayı bul  │
│     - Mesafe < tolerans (1.5 birim) ise eşleşme             │
│     - Eşleşme oranı > %70 ise GEÇER                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Tepe Noktası Kontrolü                                    │
│     Hesaplanan: x = -b/(2a), y = f(x)                       │
│     SVG'den: En yüksek/düşük y değerli nokta                │
│     Mesafe kontrolü: < 1.5 birim                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Kök Noktaları Kontrolü (varsa)                           │
│     Hesaplanan: ax² + bx + c = 0 çözümleri                  │
│     SVG'den: y ≈ 0 olan noktalar                            │
│     Karşılaştırma                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                    ┌────┴────┐
                    │ Tüm     │
                    │ kontrol │
                    │ ler OK? │
                    └────┬────┘
                    EVET │    │ HAYIR
         ┌───────────────┘    └──────────────┐
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│  PARABOL GEÇER  │                  │  PARABOL HATA   │
│  Score: +0      │                  │  Score: -20     │
└─────────────────┘                  └─────────────────┘
```

## Geometri Sorusu Özel Doğrulama

```
┌─────────────────────────────────────────────────────────────┐
│              GEOMETRİ SORUSU DOĞRULAMA                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Açı Bilgilerini Metinden Çıkar                           │
│     Pattern'ler:                                             │
│     - ∠ABC = 60°                                            │
│     - açı ABC = 60                                          │
│     - m(ABC) = 60                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. SVG'den Açı İşaretlerini Çıkar                           │
│     - Arc elementlerini bul                                  │
│     - Açı işareti konumlarını tespit et                     │
│     - Açı değerlerini hesapla (vektör analizi)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Açı Eşleştirme                                           │
│     Her metin açısı için:                                    │
│     - Label'a göre SVG'de ara (∠ABC)                        │
│     - Konum kontrolü (doğru köşede mi?)                     │
│     - Değer kontrolü (±5° tolerans)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Kenar Uzunlukları (varsa)                                │
│     - Metinden kenar uzunluklarını çıkar                     │
│     - SVG'den çizgi uzunluklarını hesapla                    │
│     - Ölçek faktörü ile karşılaştır                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Geometrik İlişkiler                                      │
│     - Açılar toplamı kontrolü (üçgen: 180°)                 │
│     - Paralellik kontrolü                                    │
│     - Dik açı kontrolü                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                    ┌────┴────┐
                    │ Tüm     │
                    │ kontrol │
                    │ ler OK? │
                    └────┬────┘
                    EVET │    │ HAYIR
         ┌───────────────┘    └──────────────┐
         ▼                                    ▼
┌─────────────────┐                  ┌─────────────────┐
│ GEOMETRİ GEÇER  │                  │ GEOMETRİ HATA   │
│  Score: +0      │                  │  Score: -20     │
└─────────────────┘                  └─────────────────┘
```

## Kullanım Örneği

```python
from quiz.services.question_validation_system import (
    QuestionValidationSystem,
    generate_validation_report
)

# Doğrulama sistemi oluştur
validator = QuestionValidationSystem()

# Soru verisi
question_data = {
    'question_text': 'f(x) = x² - 4x + 3 parabolü için tepe noktası nedir?',
    'image_svg': '<svg>...</svg>',
    'choices': [
        {'text': '(2, -1)', 'is_correct': True},
        {'text': '(1, 0)', 'is_correct': False},
        {'text': '(3, 0)', 'is_correct': False},
        {'text': '(0, 3)', 'is_correct': False},
        {'text': '(4, 3)', 'is_correct': False},
    ],
    'correct_answer': '(2, -1)'
}

# Doğrulama yap
result = validator.validate_question(question_data, question_type='parabola')

# Rapor oluştur
report = generate_validation_report(result)
print(report)

# Sonuç kontrolü
if result.is_valid():
    # Soruyu veritabanına kaydet
    save_question(question_data)
else:
    # Yeniden üret
    regenerate_question()
```

## Hata Tipleri ve Çözümleri

### 1. PARABOLA_POINT_MISMATCH
**Sorun:** SVG'deki parabol ile fonksiyon tanımı uyuşmuyor

**Çözüm:**
- Fonksiyon tanımını kontrol et
- SVG oluşturma parametrelerini gözden geçir
- Koordinat dönüşümlerini doğrula

### 2. GEOMETRY_ANGLE_MISMATCH
**Sorun:** Açı işaretleri yanlış konumda veya değerler uyuşmuyor

**Çözüm:**
- Açı işareti konumlandırma algoritmasını düzelt
- Açı hesaplama fonksiyonunu kontrol et
- SVG arc parametrelerini ayarla

### 3. MATH_INCONSISTENCY
**Sorun:** Matematiksel tutarsızlık

**Çözüm:**
- Fonksiyon parse işlemini kontrol et
- Hesaplama toleransını ayarla
- Özel durumları (sıfıra bölme, vb.) ele al

### 4. SVG_PARSE_ERROR
**Sorun:** SVG içeriği geçersiz

**Çözüm:**
- SVG oluşturma kodunu kontrol et
- XML syntax hatalarını düzelt
- Namespace tanımlarını ekle

## Performans Metrikleri

- **Doğrulama Süresi:** ~100-200ms per soru
- **Bellek Kullanımı:** ~5-10MB per soru
- **Başarı Oranı:** %85+ (ilk denemede)
- **Yeniden Üretim Oranı:** %10-15

## Gelecek İyileştirmeler

1. **Makine Öğrenmesi Entegrasyonu**
   - Görsel tanıma ile açı ve nokta tespiti
   - Anomali tespiti için ML modeli

2. **Gelişmiş Geometri Kontrolü**
   - Otomatik şekil tanıma
   - Ölçek ve oran kontrolü

3. **Performans Optimizasyonu**
   - Paralel doğrulama
   - Cache mekanizması

4. **Detaylı Raporlama**
   - Görsel diff gösterimi
   - İnteraktif hata gösterimi
