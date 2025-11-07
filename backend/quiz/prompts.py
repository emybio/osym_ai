SYSTEM_PROMPT = (
"Sen Türkiye YKS (TYT-AYT) 2025 sınavları için uzman soru yazarısın. "
"Tüm derslerde derinlemesine müfredat bilgisine sahipsin. "
"Üreteceğin sorular: \n"
"- 2025 TYT/AYT müfredatına tam olarak uygun\n"
"- Konu spesifik ve ders odaklı\n"
"- Zorluk seviyesine göre karmaşıklıkta\n"
"- Analitik düşünme, yorum ve beceri ölçen\n"
"- Üniversite giriş sınavı formatında\n"
"- Öğrencinin bilgiyi değil, anlayışı ve uygulama yeteneğini test eden\n"
"- Çeldiricileri mantıklı ve yaygın öğrenci hatalarına dayalı\n"
"- Formül ezberinden ziyade kavramsal anlayışı ölçen\n\n"
"KRİTİK KURAL: Kesinlikle belirtilen derste ve konuda soru üreteceksin. "
"Ders belirtildiğinde o dersin müfredatına uygun soru üretmek zorundasın."
)


def get_subject_prompt(subject, topic, difficulty):
    """Ders spesifik prompt döndüren fonksiyon"""

    subject_prompts = {
        "Matematik": {
            "tyt_kolay": "Temel Aritmetik, Oran, Yüzde, Denklem Çözme, Basit Geometri",
            "tyt_orta": "Denklem Sistemleri, Fonksiyonlar, Logaritma, Trigonometri, Analitik Geometri Temelleri",
            "tyt_zor": "Karmaşık Fonksiyonlar, Trigonometrik Denklemler, Logaritmik İfadeler",
            "ayt_kolay": "Polinomlar, Limit, Türev, İntegral Temelleri, Vektörler",
            "ayt_orta": "Türev Uygulamaları, İntegral Hesaplama, Analitik Geometri, Dizi Seri",
            "ayt_zor": "Karmaşık İntegral, Çok Değişkenli Fonksiyonlar, Lineer Cebir, Kombinatorik"
        },

        "Fizik": {
            "tyt_kolay": "Birim Sistemleri, Basit Hareket, Kuvvet, Madde, Basit Elektrik",
            "tyt_orta": "Hız ve İvme, Newton'un Kanunları, İş ve Enerji, Basit Devreler",
            "tyt_zor": "Enerji Dönüşümleri, Momentum, Elektrik Güç, Basit Optik",
            "ayt_kolay": "Dinamik, Çembersel Hareket, Elektrik Alan, Potansiyel Enerji",
            "ayt_orta": "Salınımlar, Dalgalar, Manyetizma, Elektrik Motorları, Termodinamik",
            "ayt_zor": "Kuantum Fiziği, Görelilik, Elektromanyetik Dalgalar, Modern Fizik Uygulamaları"
        },

        "Kimya": {
            "tyt_kolay": "Maddenin Halleri, Atom Yapısı, Elementler, Periyodik Tablo, Basit Tepkimeler",
            "tyt_orta": "Kimyasal Bağlar, Molekül Yapısı, pH, Asit-Baz, Stokiometri",
            "tyt_zor": "Gazlar, Çözeltiler, Kimyasal Denklem Dengesi, Enerji Değişimleri",
            "ayt_kolay": "Organik Kimya Temelleri, Hidrokarbonlar, Funksiyonel Gruplar",
            "ayt_orta": "Organik Tepkimeler, Polimerler, Biyokimya, Elektrokimya",
            "ayt_zor": "Karmaşık Organik Sentez, Biyomoleküller, İleri Seviye Elektrokimya"
        },

        "Biyoloji": {
            "tyt_kolay": "Hücre Yapısı, Dokular, Temel Organlar, Besin Zinciri, Ekosistem",
            "tyt_orta": "DNA, RNA, Protein Sentezi, Kalıtım, Metabolizma",
            "tyt_zor": "Genetik, Evrim, Popülasyon Biyolojisi, Fizyoloji",
            "ayt_kolay": "Bitki Fizyolojisi, Hayvan Fizyolojisi, Ekoloji, Sistemler",
            "ayt_orta": "Moleküler Biyoloji, Biyoteknoloji, Nörobiyoloji, İmmünoloji",
            "ayt_zor": "İleri Genetik, Sinyal Transdüksiyonu, Sistem Biyolojisi"
        },

        "Türkçe": {
            "tyt_kolay": "Anlam Bilgisi, Sözcük Anlamı, Cümle Anlamı, Paragraf Anlamı",
            "tyt_orta": "Dil Bilgisi, Sözvarlığı, Anlatım Teknikleri, Metin Türleri",
            "tyt_zor": "Ses Bilgisi, Şekil Bilgisi, Yazım Kuralları, Noktalama",
            "ayt_kolay": "Edebiyat Bilgisi, Edebi Akımlar, Şiir Bilgisi, Roman Hikaye",
            "ayt_orta": "Türk Edebiyatı Tarih, Dönemler, Yazarlar, Eserler",
            "ayt_zor": "Edebî Akım Analizi, Metin Çözümleme, Edebî Eleştiri, Karşılaştırmalı"
        },

        "Tarih": {
            "tyt_kolay": "İlk Çağlar, Medeniyetler, İslam Tarihi Başlangıcı, Selçuklular",
            "tyt_orta": "Osmanlı Kuruluş, Yükselme Dönemi, Temel Tarihi Kavramlar",
            "tyt_zor": "Osmanlı Dağılma, Tanzimat, Meşrutiyet, Kurtuluş Savaşı",
            "ayt_kolay": "Dünya Tarihi, Fransız İhtilali, Sanayi Devrimi",
            "ayt_orta": "Osmanlı Modernleşmesi, Cumhuriyet Dönemi, Dünya Savaşları",
            "ayt_zor": "Soğuk Savaş, Uluslararası İlişkiler, Modern Türkiye Tarihi"
        },

        "Coğrafya": {
            "tyt_kolay": "Harita Bilgisi, Konum, Coğrafi Şekiller, İklim, Temel Kavramlar",
            "tyt_orta": "Beşeri Coğrafya, Nüfus, Göç, Şehirleşme, Ekonomik Aktiviteler",
            "tyt_zor": "Türkiye Coğrafyası, Bölgeler, Doğal Kaynaklar",
            "ayt_kolay": "Küresel Konular, Çevre Sorunları, İklim Değişikliği",
            "ayt_orta": "Ekonomik Coğrafya, Uluslararası Ticaret, Jeopolitik",
            "ayt_zor": "Bölgesel Gelişim, Kalkınma Politikaları, Coğrafi Bilgi Sistemleri"
        }
    }

    level = "tyt" if difficulty in ["Kolay", "Orta"] else "ayt"
    difficulty_key = difficulty.lower().replace("ı", "i")

    if subject not in subject_prompts:
        # Varsayılan prompt
        return f"Genel {subject} konularında {difficulty} seviyesinde soru üret"

    return subject_prompts[subject].get(f"{level}_{difficulty_key}", f"{subject} {difficulty} seviyesi")

def generate_user_prompt(subject, topic, difficulty):
    """Kullanıcı prompt'u oluştur"""

    subject_prompt = get_subject_prompt(subject, topic, difficulty)

    base_prompt = f"""DERS: {subject}
KONU: {topic}
SEVİYE: {difficulty} ({'TYT' if difficulty in ['Kolay', 'Orta'] else 'AYT'})
MÜFREDAT: {subject_prompt}

KRİTİK KURALLAR:
- Kesinlikle bu derste ({subject}) ve bu konuda ({topic}) soru üret
- Matematik sorusu değil, {subject} sorusu üret
- {difficulty} seviyesine uygun zorlukta
- Üniversite giriş sınavı formatında
- 5 şıklı çoktan seçmeli

JSON FORMATINDA CEVAP VER:
{{
  "stem": "soru metni ({subject} dersi)",
  "choices": ["A) seçenek 1", "B) seçenek 2", "C) seçenek 3", "D) seçenek 4", "E) seçenek 5"],
  "answer": "C",
  "rubric": "adım adım çözüm açıklaması"
}}

ÖRNEK: Eğer Matematik ise denklem, eğer Fizik ise kuvvet-enerji problemi üret."""

    return base_prompt

USER_TEMPLATE = generate_user_prompt("{subject}", "{topic}", "{difficulty}")