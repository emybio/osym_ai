#!/usr/bin/env python
"""
Bulk Question Fixer
JSON dosyasındaki sorunlu soruları toplu halde düzeltir
"""

import json
import random
import re

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

# ÖSYM formatında soru bankaları
TURKCE_SORULARI = [
    "Paragrafta aşağıdaki kelime veya kavramlardan hangisi geçmemektedir?",
    "Verilen cümlede noktalama hatası bulunmaktadır. Hangi seçenekte düzeltilmiş hali verilmiştir?",
    "'Anlam' bakımından aşağıdaki cümlelerin hangisinde sorun vardır?",
    "Aşağıdaki deyimlerden hangisi yanlış kullanılmıştır?",
    "Verilen şiir dizesindeki anlam katmanıyla ilgili olarak aşağıdakilerden hangisi söylenebilir?",
    "'Boşluk doldurma' türündeki soruda aşağıdakilerden hangisi anlama en uygun şekilde tamamlar?",
    "Aşağıdaki sözcüklerden hangisi diğerlerinden farklı bir anlam köküne sahiptir?",
    "Paragraftaki ana düşünceyi en iyi şekilde ifade eden seçenek aşağıdakilerden hangisidir?",
    "Verilen metinde yazarın amacı aşağıdakilerden hangisidir?",
    "'Aşağıdakilerden hangisi...' ile başlayan soruda doğru cevap hangisidir?"
]

MATEMATIK_SORULARI = [
    "x² + 5x + 6 = 0 denkleminin çözüm kümesi aşağıdakilerden hangisidir?",
    "Fonksiyonu tanımlı olmak için x'in alamayacağı değer aşağıdakilerden hangisidir?",
    "Bir üçgende açı ölçüleri veriliyor. Kalan açının ölçüsü kaç derecedir?",
    "Verilen dizideki 10. terim kaçtır?",
    "Dikdörtgenler prizmasının hacmi x birim küptür. Genişliği y birim ise yüksekliği kaç birimdir?",
    "Logaritma denklemi log₂(8) = x için x değeri kaçtır?",
    "Türev Alma kuralına göre f(x) = 3x² + 2x fonksiyonunun türevi nedir?",
    "Verilen setin eleman sayısı ve alt setler sayısı aşağıdakilerden hangisidir?",
    "Olasılık sorusunda 6 yüzlü zarla ilgili beklenen değer kaçtır?",
    "İki boyutlu vektörlerin dot product sonucu kaçtır?"
]

FIZIK_SORULARI = [
    "Bir cism 10 N'luk kuvvetle 5 metre sürüklenirse yapılan iş kaç joule olur?",
    "Hızı 90 km/saat olan araba 2 saniyede ne kadar yol alır?",
    "Sesin havadaki yayılma hızı yaklaşık kaç m/s'dir?",
    "Işık kırılma indisi 1.5 olan ortama girdiğinde hızı ne kadar değişir?",
    "Potansiyel farkı 12V olan batarya 2A akım verirse güç kaç watttır?",
    "Yerçekimi ivmesi 9.8 m/s² olan yerde 10 kg'lık cismin ağırlığı kaç newtondur?",
    "Elastik çarpışmada momentum korunumu kuralına göre son hızlar nasıl hesaplanır?",
    "Basit harmonik hareket yapan bir sistemin periyodu nasıl bulunur?",
    "Isıl kapasitesi 500 J/K olan metal 100 K ısıtılırsa ne kadar enerji gerekir?",
    "Manyetik alan içinde hareketli iletkendeki indüklenen EMK nasıl hesaplanır?"
]

KIMYA_SORULARI = [
    "H₂O maddesi aşağıdakilerden hangisinin kimyasal formülüdür?",
    "Asit ortamında pH değeri 4 olan çözelti nötr ortama göre kaç kez daha asidiktir?",
    "Periyodik tabloda 17. grupta yer alan element aşağıdakilerden hangisidir?",
    "NaCl sulu çözeltisine AgNO₃ eklendiğinde oluşan çökeltilerin rengi nedir?",
    "C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O reaksiyonunda aşağıdakilerden hangisi doğrudur?",
    "Standart şartlar altında 1 mol gazın hacmi kaç litredir?",
    "Güçlü asit ve güçlü bazın tepkimesinde oluşan tuz pH değeri kaçtır?",
    "Redoks reaksiyonunda elektron transfer sayısı 2 ise oksidasyon sayısı değişimi nedir?",
    "Organik bileşikte fonksiyonel grup olarak -COOH bulunduğunda bu aşağıdakilerden hangisidir?",
    "Kromatografide ayırma prensibi aşağıdakilerden hangisidir?"
]

BIYOLOJI_SORULARI = [
    "Fotosentez hangi organelde gerçekleşir?",
    "İnsan vücudundaki en büyük kas aşağıdakilerden hangisidir?",
    "DNA'nın çift sarmal yapısını keşfeden bilim insanları kimlerdir?",
    "Hücre bölünmesinde mitoz ve meioz arasındaki temel fark aşağıdakilerden hangisidir?",
    "Enzim aktivitesini etkileyen faktörlerden hangisi doğrudur?",
    "Sinir hücresi (neuron) yapısıyla ilgili olarak aşağıdakilerden hangisi doğrudur?",
    "Kalp-damar sisteminde oksijenli kan taşınan damar aşağıdakilerden hangisidir?",
    "Ekosistemde üretici rolünü oynayan organizmalar aşağıdakilerden hangisidir?",
    "Protein sentezi sırasında RNA'ların rolü aşağıdakilerden hangisidir?",
    "Bağışıklık sisteminde antikor üreten hücre tipi aşağıdakilerden hangisidir?"
]

TARIH_SORULARI = [
    "Türk tarihinin en önemli dönüm noktalarından hangisi Malazgirt Zaferi'dir?",
    "Osmanlı Devleti'nin kurucusu olan kişinin adı aşağıdakilerden hangisidir?",
    "Cumhuriyetin ilanı hangi tarihte ve kimin tarafından yapılmıştır?",
    "Lozan Barış Antlaşması'nda aşağıdaki konulardan hangisi gündeme gelmiştir?",
    "Tanzimat Fermanı'nın ilan tarihi ve anlamı aşağıdakilerden hangisidir?",
    "Kurtuluş Savaşı'nın en önemli cephelerinden Sakarya Meydan Muharebesi hangi yılda gerçekleşmiştir?",
    "Türkiye Cumhuriyeti'nde çok partili hayata geçiş hangi yıllarda başlamıştır?",
    "İstiklal Marşı'mızın şairi ve bestecisi kimlerdir?",
    "Balkan Savaşları'nda Osmanlı Devleti'nin kaybettiği topraklar aşağıdakilerden hangisidir?",
    "Atatürk'ün inkılaplarından hangisi eğitim alanıyla ilgilidir?"
]

COGRAFYA_SORULARI = [
    "Türkiye'nin en yüksek dağı aşağıdakilerden hangisidir?",
    "Afrika kıtasının en uzun nehri aşağıdakilerden hangisidir?",
    "Kıtaların kayma teorisini ilk kez ortaya atan bilim insanı kimdir?",
    "İklim tiplerinden hangisi yağış ormanlarında görülür?",
    "Nüfus yoğunluğu en yüksek olan kıta aşağıdakilerden hangisidir?",
    "Dünya'da en fazla petrol rezervine sahip ülke hangisidir?",
    "Ekvatoral iklimin özellikleri aşağıdakilerden hangisidir?",
    "Türkiye'de Karadeniz Bölgesi'ne özgü ekonomik aktivite aşağıdakilerden hangisidir?",
    "Volkanik originli toprak türü aşağıdakilerden hangisidir?",
    "İstanbul Boğazı'nın stratejik önemi aşağıdakilerden hangisidir?"
]

FILOZOFE_SORULARI = [
    "Sokrates'in 'Sorgulama yöntemi' aşağıdakilerden hangisiyle bilinir?",
    "Platon'un 'İdealar dünyası' felsefesi aşağıdakilerden hangisini savunur?",
    "Aristo'ya göre mutlak bilgiye ulaşmanın yolu aşağıdakilerden hangisidir?",
    "Descartes'ın 'Düşünüyorum, öyleyse varım' sözü felsefenin hangi alanıyla ilgilidir?",
    "Kant'ın 'Kategori'leri bilgisine göre bilgi nasıl elde edilir?",
    "Etik felsefesi olarak utilitaryanizm aşağıdakilerden hangisini savunur?",
    "Varoluşçuluk akımına göre özgürlük ve sorumluluk ilişkisi nasıl yorumlanır?",
    "Epistemoloji bilimi aşağıdaki sorulardan hangisini inceler?",
    "Metafizik felsefesi aşağıdaki konulardan hangisini araştırır?",
    "Mantıksal çıkarımlarda doğru önermeden yanlış sonuç çıkarma olasılığı var mıdır?"
]

DIN_KULTURU_SORULARI = [
    "İslam dininde beş vakit namaz hangileridir?",
    "Hac ibadeti İslam'ın şartlarından kaçıncısıdır?",
    "Kuran-ı Kerim'in ilk vahyedildiği sura aşağıdakilerden hangisidir?",
    "Peygamber Efendimiz'in doğum yeri ve yılı aşağıdakilerden hangisidir?",
    "Müslüman aile hayatında miras paylaşımı nasıl yapılır?",
    "Regaib Kandili'nin anlamı ve önemi nedir?",
    "Cuma namazının kılınış şekli vakit namazlarından nasıl farklıdır?",
    "Oruç tutmanın sağlık açısından faydaları aşağıdakilerden hangisidir?",
    "Zekat verilecek kişiler Kuran'da hangi ayette belirtilmiştir?",
    "Hz. Muhammed'in hayatından öğrenilebilecek en önemli ahlaki değerler nelerdir?"
]

def generate_grammar_question():
    """Türkçe gramer sorusu oluştur"""
    patterns = [
        "Aşağıdaki cümlelerin hangisinde yazım yanlışı bulunmamaktadır?",
        "Paragrafta noktalama işaretleriyle ilgili olarak aşağıdakilerden hangisi söylenemez?",
        "'Boşluk bırakarak' sorusu: Türk dil kurumuna göre doğru kullanım hangisidir?",
        "Anlamca en yakın cümle aşağıdakilerden hangisidir?",
        "Sözcük türü itibariyle farklı olan kelime hangisidir?"
    ]
    return random.choice(patterns)

def generate_math_question():
    """Matematik sorusu oluştur"""
    patterns = [
        f"Verilen denklem {random.randint(1,20)}x + {random.randint(1,20)} = {random.randint(20,100)} için x değeri kaçtır?",
        f"Ardisik sayılar dizisinde {random.randint(1,10)} ve {random.randint(11,30)} arasındaki asal sayılar kaç tanedir?",
        f"Kenarları {random.randint(3,10)} cm ve {random.randint(3,10)} cm olan dikdörtgenin alanı kaç cm²'dir?",
        f"Logaritma denkleminde log_{random.randint(2,10)}({random.randint(100,1000)}) = x için x kaçtır?",
        f"Vektör toplamı işleminde sonuç kaçtır?"
    ]
    return random.choice(patterns)

def generate_physics_question():
    """Fizik sorusu oluştur"""
    patterns = [
        f"{random.randint(5,50)} N'luk kuvvet {random.randint(2,10)} kg'lık cismi ne kadar ivmelendirir?",
        f"Hızı {random.randint(60,120)} km/saat olan araç {random.randint(2,6)} saatte kaç km yol alır?",
        f"Voltajı {random.randint(10,220)}V olan devreden akan akım {random.randint(1,20)}A ise güç kaç watttır?",
        f"Yerçekimi ivmesi altında {random.randint(100,1000)} gram'lık cismin ağırlığı kaç newtondur?",
        f"Isıl iletkenliği {random.randint(100,500)} W/(m·K) olan malzemenin ısı transfer oranı nedir?"
    ]
    return random.choice(patterns)

def generate_chemistry_question():
    """Kimya sorusu oluştur"""
    patterns = [
        f"pH'ı {random.randint(2,6)} olan çözelti ne tür bir çözeltidir?",
        f"Periyodik tabloda atom numarası {random.randint(1,118)} olan elementin grubu kaçtır?",
        f"Kimyasal formülü C{random.randint(1,20)}H{random.randint(1,40)}O{random.randint(1,10)} olan bileşik kaç atom içerir?",
        f"Stoikiyometrik hesaplamada {random.randint(1,5)} mol reaktan kullanılıyor ise ürün kaç mol olur?",
        f"Kimyasal dengede denge sabiti K={random.uniform(0.1,10)} için reaksiyon yönünü belirleyiniz."
    ]
    return random.choice(patterns)

def generate_biology_question():
    """Biyoloji sorusu oluştur"""
    patterns = [
        f"ATP sentezi hücrenin hangi organelinde gerçekleşir?",
        f"DNA replikasyonunda {random.randint(1,20)} baz çifti kopyalandığında kaç yeni DNA molekülü oluşur?",
        f"Enzim optimum sıcaklığı {random.randint(20,50)}°C ise en yüksek aktivite ne zaman görülür?",
        f"Fotosentezde {random.randint(1,10)} mol CO₂ kullanıldığında kaç mol O₂ üretilir?",
        f"Nöron ileti hızının {random.randint(10,200)} m/s olduğu sinirde sinyal {random.randint(1,10)} cm'yi kaç saniyede alır?"
    ]
    return random.choice(patterns)

def generate_choices_for_subject(subject_name, question_text):
    """Dersine uygun şıklar oluştur"""
    subject_choices = {
        "Türkçe": [
            ["Anlamca doğru", "Yazım hatası var", "Noktalama hatası", "Sözcük hatası"],
            ["Soyut", "Somut", "Gösterge", "İaret"],
            ["Cümle tam", "Yanlış yapı", "Anlam bozuk", "Üslup hatalı"],
            ["Doğru", "Yanlış", "Eksik", "Fazla"]
        ],
        "Matematik": [
            ["12", "15", "18", "21"],
            ["x = 3", "x = 4", "x = 5", "x = 6"],
            ["x² + 2x + 1", "x² - 2x + 1", "2x² + x", "x² + 3x"],
            ["4", "5", "6", "7"],
            ["100", "150", "200", "250"]
        ],
        "Fizik": [
            ["50 J", "75 J", "100 J", "125 J"],
            ["5 m/s²", "7.5 m/s²", "10 m/s²", "12.5 m/s²"],
            ["10 kg·m/s", "20 kg·m/s", "30 kg·m/s", "40 kg·m/s"],
            ["120 W", "240 W", "360 W", "480 W"],
            ["98 N", "196 N", "294 N", "392 N"]
        ],
        "Kimya": [
            ["Asidik", "Bazik", "Nötr", "Amfoter"],
            ["Halojen", "Alkali", "Noble gas", "Transition metal"],
            ["Na", "K", "Ca", "Mg"],
            ["pH 3", "pH 7", "pH 10", "pH 14"],
            ["1", "2", "3", "4"]
        ],
        "Biyoloji": [
            ["Mitokondri", "Kloroplast", "Ribozom", "Lizozom"],
            ["Mitoz", "Meioz", "Amitoz", "Bölünme yok"],
            ["DNA", "RNA", "Protein", "Lipid"],
            ["0.00025", "0.0005", "0.001", "0.002"],
            ["4", "8", "16", "32"]
        ],
        "Tarih": [
            ["1071", "1099", "1105", "1110"],
            ["Fatih Sultan Mehmet", "Yavuz Sultan Selim", "Kanuni Sultan Süleyman", "II. Abdülhamid"],
            ["1920", "1922", "1923", "1924"],
            ["Malazgirt", "Kosova", "Mohaç", "Varna"]
        ],
        "Coğrafya": [
            ["Ağrı Dağı", "Erciyes Dağı", "Uludağ", "Kaçkar Dağları"],
            ["Nijer Nehri", "Nil Nehri", "Kongo Nehri", "Zambezi Nehri"],
            ["Wegener", "Darwin", "Newton", "Einstein"],
            ["Asya", "Afrika", "Avrupa", "Güney Amerika"]
        ],
        "Felsefe": [
            ["Mayetik", "Diyalektik", "Sofistik", "Retorik"],
            ["Gerçeklik", "Görünüş", "Rüya", "Hayal"],
            ["A priori", "A posteriori", "Indüksiyon", "Dedüksiyon"],
            ["Doğalcılık", "İdealcilik", "Pragmatizm", "Varoluşçuluk"]
        ],
        "Din Kültürü": [
            ["Sabah", "Öğle", "İkindi", "Yatsı"],
            ["1", "2", "3", "4"],
            ["Alak", "Fatiha", "İhlas", "Fil"],
            ["Mekke", "Medine", "Kudüs", "İstanbul"]
        ]
    }

    choices_list = subject_choices.get(subject_name, ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"])
    choices = random.choice(choices_list)

    # Şık formatı
    choice_dict = {}
    labels = ['A', 'B', 'C', 'D', 'E']

    for i, choice in enumerate(choices):
        if i < len(labels):
            choice_dict[labels[i]] = str(choice)

    return choice_dict, random.choice(labels)

def fix_question(question):
    """Tek bir soruyu düzelt"""
    fields = question.get('fields', {})
    subject_id = fields.get('subject', 0)
    subject_name = get_subject_name(subject_id)

    # Soru üret
    question_generators = {
        "Türkçe": lambda: random.choice(TURKCE_SORULARI + [generate_grammar_question()]),
        "Matematik": generate_math_question,
        "Fizik": generate_physics_question,
        "Kimya": generate_chemistry_question,
        "Biyoloji": generate_biology_question,
        "Tarih": lambda: random.choice(TARIH_SORULARI),
        "Coğrafya": lambda: random.choice(COGRAFYA_SORULARI),
        "Felsefe": lambda: random.choice(FILOZOFE_SORULARI),
        "Din Kültürü": lambda: random.choice(DIN_KULTURU_SORULARI)
    }

    generator = question_generators.get(subject_name)
    if generator:
        new_question_text = generator()
        new_choices, correct_answer = generate_choices_for_subject(subject_name, new_question_text)

        # Soruyu güncelle
        fields['question_text'] = new_question_text
        fields['explanation'] = f"ÖSYM standardı {subject_name} sorusu"

        # Not: Choices'ı burada update etmiyoruz, sadece Question model'ini
        # Question ve Choice ayrı modeller olduğu için

        return question, new_choices, correct_answer

    return question, None, None

def fix_all_questions(input_file, output_file):
    """Tüm sorunlu soruları düzelt"""
    print("Sorular düzeltiliyor...\n")

    questions = load_questions(input_file)
    fixed_questions = []
    new_choices_dict = {}  # Yeni choices'ları sakla

    fixed_count = 0

    for question in questions:
        fields = question.get('fields', {})
        question_text = fields.get('question_text', '')

        # Sorunlu soruları tespit et
        issues = []

        # Generic content kontrolü
        generic_patterns = [
            r'temel soru',
            r'örnek soru',
            r'.*dersi.*\d+\. soru',
            r'hangi.*doğrudur',
            r'hangi.*yanlıştır'
        ]

        for pattern in generic_patterns:
            if re.search(pattern, question_text, re.IGNORECASE):
                issues.append("generic")
                break

        # Subject relevance kontrolü
        subject_id = fields.get('subject', 0)
        subject_content = {
            2: ["Matematik", "denklem", "fonksiyon", "türev", "integral"],
            3: ["Fizik", "kuvvet", "enerji", "hız"],
            4: ["Kimya", "atom", "molekül", "reaksiyon"],
            5: ["Biyoloji", "hücre", "fotosentez", "DNA"]
        }

        if subject_id in subject_content:
            keywords = subject_content[subject_id]
            subject_name = keywords[0]
            has_relevant = any(keyword.lower() in question_text.lower() for keyword in keywords[1:])
            if not has_relevant:
                issues.append("no_subject_content")

        # Sorun varsa düzelt
        if issues:
            fixed_question, new_choices, correct_answer = fix_question(question)
            fixed_questions.append(fixed_question)

            if new_choices:
                new_choices_dict[question.get('pk')] = {
                    'choices': new_choices,
                    'correct_answer': correct_answer
                }

            fixed_count += 1
            if fixed_count % 50 == 0:
                print(f"{fixed_count} soru düzeltildi...")
        else:
            # Sorunsuz soruları aynen ekle
            fixed_questions.append(question)

    # Düzelttiğimiz soruları dosyaya yaz
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fixed_questions, f, ensure_ascii=False, indent=2)

    print(f"\nToplam {fixed_count} soru düzeltildi")
    print(f"Düzeltilmiş sorular {output_file} dosyasına kaydedildi")

    # Yeni choices'ları ayrı dosyaya yaz
    with open('new_choices.json', 'w', encoding='utf-8') as f:
        json.dump(new_choices_dict, f, ensure_ascii=False, indent=2)

    print(f"Yeni şıklar 'new_choices.json' dosyasına kaydedildi")

    return fixed_count

if __name__ == "__main__":
    fixed_count = fix_all_questions('questions_original.json', 'questions_fixed.json')
    print(f"\nİşlem tamamlandı: {fixed_count} soru düzeltildi")