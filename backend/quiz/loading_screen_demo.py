# EĞLENCELİ BEKLEME EKRANI DEMO
# Ana yapıya dokunmadan, sadece frontend'e gönderilecek JSON verisi

import time
import random

def generate_loading_screen_data(total_time_seconds=25):
    """
    25 saniyelik eğlenceli bekleme verisi üretir
    Frontend'e gönderilecek JSON formatı
    """

    phases = [
        {
            "id": "preparation",
            "title": "🧠 Beyn Geliştirme Başlatılıyor",
            "description": "Zeka sistemleri uyanıyor...",
            "duration": 8,
            "icon": "🧠"
        },
        {
            "id": "question_selection",
            "title": "📚 Milyonlarca Soru Aranıyor",
            "description": "En uygun sorular seçiliyor...",
            "duration": 12,
            "icon": "🔍"
        },
        {
            "id": "optimization",
            "title": "⚡ Kişiselleştirme Yapılıyor",
            "description": "Sınavınız özel olarak tasarlanıyor...",
            "duration": 5,
            "icon": "✨"
        }
    ]

    # Progress stages (her bir phase'de)
    progress_stages = {
        "preparation": [
            "🧠 Yapay zeka devreye alınıyor...",
            "🔍 Soru veritabanı taranıyor...",
            "📈 Kişiselleştirme profili yükleniyor...",
            "⚡ Hız optimizasyonu yapılıyor..."
        ],
        "question_selection": [
            "📚 Matematik soruları seçiliyor...",
            "🔍 Fizik denklemleri taranıyor...",
            "⚛️ Kimya formülleri hazırlanıyor...",
            "🧬 Biyoloji deneyleri analiz ediliyor...",
            "📖 Türkçe metinleri inceleniyor..."
        ],
        "optimization": [
            "✨ Zorluk seviyesi ayarlanıyor...",
            "🎯 Hedef skor belirleniyor...",
            "📊 İstatistikler güncelleniyor..."
        ]
    }

    # Fun facts (rastgele gösterilecek)
    fun_facts = [
        "💡 Biliyor muydun? Beynim her saniyede 4 milyar işlem yapabilir!",
        "🧠 En zeki bilgisayarlar bile TYT'ı 25 saniyede hazırlıyor!",
        "📊 Sınavda başarılış oranı %85'i aşıyor! Sen de aralarında olabilirsin!",
        "⏰ Hazırladığın bu sınavla ~500 soru analiz edildi!",
        "🎯 En çok hata yapılan konu: Türev ve Limit. Sen dikkatli ol!"
    ]

    # Interactive tips (rastgele gösterilecek)
    tips = [
        "💡 İpucu: Zor soruları en sona bırak",
        "📝 Not alırken anahtar kelimelere odaklan",
        "⏰ Zamanı iyi yönet, takıldığında geç",
        "🎯 Emin olduğun soruları önce çöz",
        "📊 Şıklarını kontrol et, zamanı iyi kullan"
    ]

    # Ana loading verisi
    loading_data = {
        "status": "loading",
        "total_duration": total_time_seconds,
        "current_phase": 0,
        "progress": 0,
        "phases": phases,
        "fun_fact": random.choice(fun_facts),
        "tip": random.choice(tips),
        "loading_animation": {
            "type": "progressive",
            "elements": ["🧠", "📚", "🔍", "⚡", "✨", "🎯", "📊"]
        },
        "estimated_completion": None
    }

    return loading_data

def get_realistic_progress(current_time_elapsed, total_duration):
    """
    Gerçekçi ilerleme hesapla (non-linear)
    """
    # İlk 10 saniye çok hızlı, sonra yavaşla
    if current_time_elapsed < 10:
        progress = (current_time_elapsed / 10) * 40  # İlk 10 saniyede %40
    elif current_time_elapsed < 20:
        # 10-20 saniye arası yavaş ilerleme
        additional_time = current_time_elapsed - 10
        progress = 40 + (additional_time / 10) * 50  # Sonraki 10 saniyede %50
    else:
        # Son 5 saniye çok yavaş
        additional_time = current_time_elapsed - 20
        progress = 90 + (additional_time / 5) * 10  # Son 5 saniyede %10

    return min(99, progress)  # %99'a kadar, tamamlanma %100'de anında

def generate_loading_step_data(current_phase, progress_percent, total_duration, current_time_elapsed):
    """
    Anlık loading adımı verisi üret
    """
    current_time = time.time()

    # Phase-specific messages
    phase_messages = {
        "preparation": [
            "🧠 Yapay zeka modüllerini aktifleştiriyorum...",
            "🔍 Soru veritabanını tarıyorum...",
            "📈 Öğrenme profiliniz yükleniyor..."
        ],
        "question_selection": [
            f"📚 {random.choice(['Matematik', 'Fizik', 'Kimya', 'Biyoloji', 'Türkçe'])} soruları seçiyorum...",
            "🎯 Kişiselleştirme algoritması çalışıyor...",
            "⚡ En zorluğu belirliyorum..."
        ],
        "optimization": [
            "✨ Sınavı size özel olarak tasarlıyorum...",
            "📊 Başarı oranını tahmin ediyorum...",
            "🎯 Optimal strateji oluşturuyorum..."
        ]
    }

    return {
        "status": "loading",
        "current_phase": current_phase,
        "progress": progress_percent,
        "message": random.choice(phase_messages.get(current_phase, ["Sistem çalışıyor..."])),
        "timestamp": current_time,
        "estimated_remaining": max(1, total_duration - current_time_elapsed)
    }

# DEMO KULLANIMI
if __name__ == "__main__":
    print("=== EĞLENCELİ BEKLEME EKRANI DEMO ===")

    # Ana loading data
    loading = generate_loading_screen_data()

    print("Frontend'e gönderilecek veri:")
    print("=" * 50)
    print(f"Status: {loading['status']}")
    print(f"Toplam Süre: {loading['total_duration']}s")
    print(f"Fun Fact: {loading['fun_fact']}")
    print(f"Tip: {loading['tip']}")
    print(f"Phases: {len(loading['phases'])} adım")

    print("\nPhases:")
    for i, phase in enumerate(loading['phases']):
        print(f"  {i+1}. {phase['icon']} {phase['title']} ({phase['duration']}s)")

    print("\nAnimasyon Elements:")
    print(f"  {', '.join(loading['loading_animation']['elements'])}")

    print("\n" + "="*50)
    print("Frontend'de bu veriyi şu şekilde kullanabilir:")
    print("const response = await fetch('/api/v1/quicktest/init/', ...)")
    print("const loadingData = response;")
    print("startLoadingAnimation(loadingData)")

    print(f"\n🎯 BEKLENEN HIZLANMA: 25s → Eğlenceli 25s!")