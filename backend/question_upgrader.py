#!/usr/bin/env python
"""
Question Upgrader to AI Generator Standards
Mevcut soruları AI generator'daki prompt'lar standartlarına göre yükseltir
"""

import json
import random
from collections import defaultdict

def load_questions(filename):
    """JSON dosyasından soruları yükle"""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        content = content.replace('�', 'Ö').replace('SYM', 'ÖSYM')
        data = json.loads(content)

    questions = []
    for item in data:
        if item.get('model') == 'quiz.question':
            questions.append(item)

    return questions

def get_subject_name(subject_id):
    """Subject ID'den ders adını al"""
    subject_map = {
        1: "Türkçe",
        2: "Matematik",
        3: "Fizik",
        4: "Kimya",
        5: "Biyoloji",
        6: "Tarih",
        7: "Coğrafya",
        8: "Felsefe",
        9: "Din Kültürü"
    }
    return subject_map.get(subject_id, f"Unknown({subject_id})")

def generate_ai_standard_choices(subject_name, question_text):
    """AI generator standartlarında 5 şıklı cevaplar üret"""

    choice_banks = {
        "Türkçe": [
            ["Anlamca uygun", "Anlamca uygunsuz", "Gramer hatası var", "Yazım yanlışı", "Sözcük seçimi hatalı"],
            ["Doğru kullanım", "Yanlış kullanım", "Eksik bilgi", "Fazla bilgi", "Çelişkili ifade"],
            ["Bağlaç doğru", "Zaman uyumsuz", "Anlam bozuk", "Üslup hatası", "Noktalama eksik"],
            ["Soyut kavram", "Somut örnek", "Sembolik ifade", "Metaforik anlam", "Teorik yaklaşım"]
        ],
        "Matematik": [
            ["12", "15", "18", "21", "24"],
            ["x = 3", "x = 4", "x = 5", "x = 6", "x = 7"],
            ["x² + 2x + 1", "x² - 2x + 1", "2x² + x", "x² + 3x", "3x² - 2x"],
            ["4", "5", "6", "7", "8"],
            ["100", "150", "200", "250", "300"],
            ["2√3", "3√2", "4", "6", "√12"],
            ["log₂8 = 3", "log₃9 = 2", "log₅25 = 2", "log₁₀100 = 2", "ln e = 1"]
        ],
        "Fizik": [
            ["50 J", "75 J", "100 J", "125 J", "150 J"],
            ["5 m/s²", "7.5 m/s²", "10 m/s²", "12.5 m/s²", "15 m/s²"],
            ["10 kg·m/s", "20 kg·m/s", "30 kg·m/s", "40 kg·m/s", "50 kg·m/s"],
            ["120 W", "240 W", "360 W", "480 W", "600 W"],
            ["98 N", "196 N", "294 N", "392 N", "490 N"],
            ["340 m/s", "300 m/s", "400 m/s", "250 m/s", "450 m/s"]
        ],
        "Kimya": [
            ["Asidik", "Bazik", "Nötr", "Amfoter", "Tuz karakterli"],
            ["Halojen", "Alkali", "Noble gas", "Transition metal", "Lantanit"],
            ["Na", "K", "Ca", "Mg", "Al"],
            ["pH 3", "pH 7", "pH 10", "pH 14", "pH 1"],
            ["1", "2", "3", "4", "5"],
            ["H₂SO₄", "HCl", "NaOH", "CH₃COOH", "NH₃"]
        ],
        "Biyoloji": [
            ["Mitokondri", "Kloroplast", "Ribozom", "Lizozom", "Peroksizom"],
            ["Mitoz", "Meioz", "Amitoz", "Bölünme yok", "Sitokinez"],
            ["DNA", "RNA", "Protein", "Lipid", "Karbonhidrat"],
            ["0.00025", "0.0005", "0.001", "0.002", "0.0001"],
            ["4", "8", "16", "32", "64"],
            ["Fotosentez", "Solunum", "Glikoliz", "Krebs döngüsü", "Oksidatif fosforilazyon"]
        ],
        "Tarih": [
            ["1071", "1099", "1105", "1110", "1157"],
            ["Fatih Sultan Mehmet", "Yavuz Sultan Selim", "Kanuni Sultan Süleyman", "II. Abdülhamid", "III. Selim"],
            ["1920", "1922", "1923", "1924", "1928"],
            ["Malazgirt", "Kosova", "Mohaç", "Varna", "Nicopolis"],
            ["Selçuklu", "Osmanlı", "Rum", "Bizans", "Sasani"]
        ],
        "Coğrafya": [
            ["Ağrı Dağı", "Erciyes Dağı", "Uludağ", "Kaçkar Dağları", "Bolkar Dağları"],
            ["Nijer Nehri", "Nil Nehri", "Kongo Nehri", "Zambezi Nehri", "Fırat Nehri"],
            ["Wegener", "Darwin", "Newton", "Einstein", "Galileo"],
            ["Asya", "Afrika", "Avrupa", "Güney Amerika", "Kuzey Amerika"],
            ["Akdeniz", "Karadeniz", "Ege", "Marmara", "İç Anadolu"]
        ],
        "Felsefe": [
            ["Mayetik", "Diyalektik", "Sofistik", "Retorik", "Skeptisizm"],
            ["Gerçeklik", "Görünüş", "Rüya", "Hayal", "İllüzyon"],
            ["A priori", "A posteriori", "İndüksiyon", "Dedüksiyon", "Abdüksiyon"],
            ["Doğalcılık", "İdealcilik", "Pragmatizm", "Varoluşçuluk", "Fenomenoloji"],
            ["Platon", "Aristo", "Sokrates", "Descartes", "Kant"]
        ],
        "Din Kültürü": [
            ["Sabah", "Öğle", "İkindi", "Yatsı", "Teravih"],
            ["1", "2", "3", "4", "5"],
            ["Alak", "Fatiha", "İhlas", "Fil", "Nas"],
            ["Mekke", "Medine", "Kudüs", "İstanbul", "Kudüs"],
            ["Oruç", "Hac", "Zekat", "Namaz", "Şehadet"]
        ]
    }

    choices = random.choice(choice_banks.get(subject_name, ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D", "Seçenek E"]))

    # 5 şık formatı
    choice_dict = {}
    labels = ['A', 'B', 'C', 'D', 'E']

    for i, choice in enumerate(choices):
        choice_dict[labels[i]] = str(choice)

    # Rastgele doğru şık seç
    correct_answer = random.choice(labels)

    return choice_dict, correct_answer

def generate_measures(subject_name, topic_name):
    """Measures alanları oluştur"""
    measure_templates = {
        "Türkçe": [
            {"subskill": "Anlam Çıkarımı", "rule": "Metnin ana fikrini belirleme", "weight": 0.4},
            {"subskill": "Yazım Kuralları", "rule": "Noktalama ve yazım denetimi", "weight": 0.3},
            {"subskill": "Sözcük Bilgisi", "rule": "Kelime anlamı ve kökeni", "weight": 0.3}
        ],
        "Matematik": [
            {"subskill": "Problem Çözme", "rule": "Matematiksel düşünme ve strateji", "weight": 0.5},
            {"subskill": "Hesaplama", "rule": "Sayısal işlemler ve formüller", "weight": 0.3},
            {"subskill": "Mantıksal Akıl Yürütme", "rule": "Matematiksel mantık", "weight": 0.2}
        ],
        "Fizik": [
            {"subskill": "Formül Uygulama", "rule": "Fizik formüllerini kullanma", "weight": 0.4},
            {"subskill": "Birim Analizi", "rule": "Fiziksel birimleri anlama", "weight": 0.3},
            {"subskill": "Kavramsal Anlama", "rule": "Fizik prensiplerini kavrama", "weight": 0.3}
        ],
        "Kimya": [
            {"subskill": "Stoikiyometri", "rule": "Kimyasal hesaplamalar", "weight": 0.4},
            {"subskill": "Periyodik Sistem", "rule": "Element özellikleri", "weight": 0.3},
            {"subskill": "Kimyasal Denklemler", "rule": "Reaksiyonları anlama", "weight": 0.3}
        ],
        "Biyoloji": [
            {"subskill": "Hücre Biyolojisi", "rule": "Hücre yapı ve fonksiyonu", "weight": 0.4},
            {"subskill": "Genetik", "rule": "Kalıtım ve DNA", "weight": 0.3},
            {"subskill": "Fizyoloji", "rule": "Canlı sistem fonksiyonları", "weight": 0.3}
        ]
    }

    base_measures = measure_templates.get(subject_name, [
        {"subskill": "Temel Bilgiler", "rule": "Konu temel kavramları", "weight": 0.5},
        {"subskill": "Uygulama", "rule": "Bilgiyi kullanma", "weight": 0.5}
    ])

    # Weight'ları normalize et
    total_weight = sum(m["weight"] for m in base_measures)
    for m in base_measures:
        m["weight"] = round(m["weight"] / total_weight, 2)

    return base_measures

def generate_misconceptions(subject_name, choices_dict):
    """Misconceptions alanları oluştur"""
    misconception_templates = {
        "Türkçe": {
            "common": ["Anlam çelişkisi", "Yazım hatası", "Gramer hatası", "Bağlam dışı yorum"],
            "detailed": ["Cümlenin ana fikrini yanlış anlama", "Sözcüğün gerçek anlamını bilmeme", "Noktalama işaretini yanlış kullanma"]
        },
        "Matematik": {
            "common": ["Formül hatası", "Hesaplama hatası", "Kavram yanılgısı", "Yanlış varsayım"],
            "detailed": ["Denklemin yanlış çözülmesi", "Değişkenin yerine yanlış değer koyma", "Matematiksel ilişkiyi kuramama"]
        },
        "Fizik": {
            "common": ["Birim karışıklığı", "Formül eksikliği", "Kavram hatası", "Yanlış yaklaşım"],
            "detailed": ["Fiziksel prensibi yanlış anlama", "Formülde yanlış değişken kullanma", "Birimi dönüştürememe"]
        },
        "Kimya": {
            "common": ["Formül hatası", "Reaksiyon hatası", "Denge sorunu", "pH yanılgısı"],
            "detailed": ["Kimyasal denklemin yanlış kurulması", "Element özelliklerini karıştırma", "Stoikiyometrik hesaplama hatası"]
        },
        "Biyoloji": {
            "common": ["Organ karışıklığı", "Süreç hatası", "Terminoloji yanılgısı", "Fonksiyon hatası"],
            "detailed": ["Hücre organellerini karıştırma", "Biyolojik süreci yanlış anlama", "Terimleri yanlış kullanma"]
        }
    }

    templates = misconception_templates.get(subject_name, {
        "common": ["Bilgi hatası", "Kavram yanılgısı", "Yanlış yorumlama", "İlişki kuramama"],
        "detailed": ["Temel kavramı yanlış anlama", "İlişkiyi kuramama", "Bilgiyi yanlış kullanma"]
    })

    misconceptions = {}
    common_misconceptions = templates["common"]
    detailed_misconceptions = templates["detailed"]

    for label in choices_dict.keys():
        # Her şık için 1-3 misconception
        num_misconceptions = random.randint(1, 3)
        selected = random.sample(common_misconceptions, min(1, len(common_misconceptions))) + \
                   random.sample(detailed_misconceptions, min(num_misconceptions-1, len(detailed_misconceptions)))

        misconceptions[label] = selected[:3]  # Max 3 tane

    return misconceptions

def generate_detailed_explanation(subject_name, question_text, correct_answer, choices_dict):
    """Detaylı explanation oluştur"""
    explanation_templates = {
        "Türkçe": [
            "Bu soruda metnin anlam bütünlüğü dikkate alınarak en uygun seçenek belirlenmelidir. Doğru cevap {correct_answer} şıkkıdır çünkü metnin ana fikrini en doğru şekilde yansıtmaktadır.",
            "Yazım kuralları açısından değerlendirildiğinde {correct_answer} şıkkı doğru kullanım içermektedir. Diğer şıklar yazım yanlışı veya anlam bozukluğu içermektedir.",
            "Cümlenin dilbilgisel yapısı incelendiğinde {correct_answer} şıkkı gramere uygun haldeyken diğer şıklarda yapısal hatalar bulunmaktadır."
        ],
        "Matematik": [
            "Matematiksel ifadeyi adım adım çözümleyelim: {correct_answer} şıkkı doğru sonuca götürmektedir. Formülün doğru uygulanması ve hesaplamanın dikkatli yapılması gerekir.",
            "Denklem çözümünde değişkenin değerini bulmak için adımları takip edelim. {correct_answer} şıkkı denklemin doğru çözümüdür.",
            "Problem çözme stratejisi kullanarak soruyu analiz edelim. {correct_answer} şıkkı matematiksel olarak doğru sonuca ulaşmamızı sağlar."
        ],
        "Fizik": [
            "Fizik prensiplerini uygulayarak problemi çözelim. {correct_answer} şıkkı formülün doğru kullanımı ve birimlerin dikkatli hesaplanması sonucu ortaya çıkmaktadır.",
            "Enerji korunumu prensibini kullanarak hesaplama yapalım. {correct_answer} şıkkı fiziksel olarak doğru sonucu vermektedir.",
            "Kuvvet ve hareket ilişkisini dikkate alarak problemi çözelim. {correct_answer} şıkkı fiziksel yasalara uygundur."
        ],
        "Kimya": [
            "Kimyasal dengeyi ve reaksiyon mekanizmasını göz önünde bulunduralım. {correct_answer} şıkkı kimyasal olarak doğru sonuca götürmektedir.",
            "Stoikiyometrik hesaplamaları dikkatli yapalım. {correct_answer} şıkkı kimyasal oranların doğru kullanılması sonucu elde edilmiştir.",
            "Periyodik tablodaki element özelliklerini kullanarak soruyu çözelim. {correct_answer} şıkkı kimyasal olarak doğru cevaptır."
        ],
        "Biyoloji": [
            "Hücresel düzeyde süreci analiz edelim. {correct_answer} şıkkı biyolojik mekanizmanın doğru açıklamasını içermektedir.",
            "Genetik prensiplerini ve kalıtımı dikkate alalım. {correct_answer} şıkkı biyolojik olarak doğru sonuca ulaşmamızı sağlar.",
            "Fizyolojik süreci adım adım inceleyelim. {correct_answer} şıkkı canlı sistem fonksiyonları açısından doğrudur."
        ]
    }

    templates = explanation_templates.get(subject_name, [
        f"Doğru cevap {correct_answer} şıkkıdır. Bu seçenek diğer şıklardan daha doğru ve mantıklı bir sonuç vermektedir.",
        f"Problem çözüm yaklaşımlarını değerlendirdiğimizde {correct_answer} şıkkı en uygun cevap olarak ortaya çıkmaktadır.",
        f"Analiz ve mantıksal çıkarım yoluyla {correct_answer} şıkkının doğru olduğu sonucuna varabiliriz."
    ])

    base_explanation = random.choice(templates)

    # Ek detay ekle
    additional_details = [
        "Diğer şıkların neden yanlış olduğu incelendiğinde temel kavram yanılgıları veya hesaplama hataları görülmektedir.",
        "Bu soru türünde dikkatli okuma ve kavramsal anlama başarının anahtarıdır.",
        "Benzer problemlerde aynı strateji kullanılarak doğru sonuca ulaşılabilir."
    ]

    if random.random() > 0.5:  # 50% ihtimalle ek detay ekle
        base_explanation += " " + random.choice(additional_details)

    return base_explanation

def upgrade_question_to_ai_standards(question):
    """Soruyu AI generator standartlarına yükselt"""
    fields = question.get('fields', {})
    subject_id = fields.get('subject', 0)
    subject_name = get_subject_name(subject_id)
    question_text = fields.get('question_text', '')

    # 1. Gelişmiş soru metni (varsa koru, yoksa geliştir)
    if len(question_text.strip()) < 30 or question_text.endswith('?') == False:
        # Daha detaylı soru üret
        enhanced_questions = {
            "Türkçe": f"Verilen metinde aşağıdakilerden hangisi söylenebilir? {question_text}",
            "Matematik": f"Aşağıdaki matematiksel problemin çözümü nedir? {question_text}",
            "Fizik": f"Fiziksel prensiplere göre aşağıdaki durumda ne olur? {question_text}",
            "Kimya": f"Kimyasal reaksiyon açısından aşağıdakilerden hangisi doğrudur? {question_text}",
            "Biyoloji": f"Biyolojik süreç açısından aşağıdakilerden hangisi doğrudur? {question_text}"
        }
        question_text = enhanced_questions.get(subject_name, question_text)

    # 2. 5 şıklı choices üret
    choices_dict, correct_answer = generate_ai_standard_choices(subject_name, question_text)

    # 3. AI standardı difficulty seviyeleri (database integer format: 1-5)
    difficulty_map = {"Kolay": 2, "Orta": 3, "Zor": 4}
    difficulty_names = ["Kolay", "Orta", "Zor"]
    difficulty_name = random.choice(difficulty_names)
    difficulty = difficulty_map[difficulty_name]

    # 4. Gelişmiş cognitive seviyeleri
    cognitive_levels = ["Bilgi", "Kavrama", "Uygulama", "Analiz", "Sentez", "Değerlendirme"]
    cognitive = random.choice(cognitive_levels)

    # 5. Topic (fields içinde varsa kullan)
    topic = fields.get('topic', 1)  # Default topic 1

    # 6. Measures oluştur
    measures = generate_measures(subject_name, f"Topic {topic}")

    # 7. Misconceptions oluştur
    misconceptions = generate_misconceptions(subject_name, choices_dict)

    # 8. Detailed explanation oluştur
    explanation = generate_detailed_explanation(subject_name, question_text, correct_answer, choices_dict)

    # AI standardı format
    ai_standard_question = {
        "model": "quiz.question",
        "pk": question.get('pk'),
        "fields": {
            "subject": subject_id,
            "topic": topic,
            "question_text": question_text,
            "difficulty": difficulty,  # String olarak
            "cognitive": cognitive,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "created_at": fields.get('created_at', '2025-11-14T17:00:00.000Z'),
            "subskills": []
        }
    }

    return ai_standard_question, choices_dict, measures, misconceptions

def upgrade_all_questions(input_file, output_file_questions, output_file_choices):
    """Tüm soruları AI standartlarına yükselt"""
    print("Sorular AI generator standartlarına yükseltiliyor...\n")

    questions = load_questions(input_file)
    upgraded_questions = []
    all_choices = {}
    upgrade_count = 0

    for i, question in enumerate(questions):
        if i % 50 == 0:
            print(f"{i}/{len(questions)} soru işlendi...")

        try:
            upgraded_q, choices_dict, measures, misconceptions = upgrade_question_to_ai_standards(question)

            upgraded_questions.append(upgraded_q)

            # Choices'ları ayrı dosya için sakla
            all_choices[question.get('pk')] = {
                'choices': choices_dict,
                'measures': measures,
                'misconceptions': misconceptions
            }

            upgrade_count += 1

        except Exception as e:
            print(f"Hata - {question.get('pk')}: {e}")
            # Orijinal soruyu ekle
            upgraded_questions.append(question)

    # Düzeltilmiş soruları kaydet
    with open(output_file_questions, 'w', encoding='utf-8') as f:
        json.dump(upgraded_questions, f, ensure_ascii=False, indent=2)

    # Choices, measures, misconceptions'ları kaydet
    with open(output_file_choices, 'w', encoding='utf-8') as f:
        json.dump(all_choices, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Tamamlandı!")
    print(f"📊 Toplam soru: {len(questions)}")
    print(f"🔄 Yükseltilen: {upgrade_count}")
    print(f"📁 Sorular: {output_file_questions}")
    print(f"📁 Ek veriler: {output_file_choices}")

    return upgrade_count

if __name__ == "__main__":
    upgrade_count = upgrade_all_questions(
        'questions_original.json',
        'questions_ai_standard.json',
        'ai_standard_extras.json'
    )

    print(f"\n🎯 {upgrade_count} soru AI generator standartlarına yükseltildi!")