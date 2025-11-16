from quiz.models import Subject, Topic, Subskill

SEED = {
    "Türkçe": {
        "code": "TR",
        "topics": {
            "Noktalama İşaretleri": {
                "phase": "TYT",
                "subskills": [
                    "Nokta",
                    "Virgül",
                    "Soru işareti",
                    "Ünlem",
                    "Tırnak işareti",
                    "Konuşma çizgisi",
                ],
            },
            "Sözcükte Anlam": {
                "phase": "TYT",
                "subskills": [
                    "Eş anlam",
                    "Zıt anlam",
                    "Gerçek anlam",
                    "Mecaz anlam",
                ],
            },
            "Cümle Bilgisi": {
                "phase": "TYT",
                "subskills": [
                    "Cümle elemanları",
                    "Cümle türleri",
                    "Cümlede anlam",
                ],
            },
            "Ses Bilgisi": {
                "phase": "TYT",
                "subskills": [
                    "Ses olayları",
                    "Ses bilgisinin uygulandığı alanlar",
                ],
            },
            "Yazım Kuralları": {
                "phase": "TYT",
                "subskills": [
                    "Büyük harfler",
                    "Birleşik kelimeler",
                    "Yabancı kelimeler",
                    "Kısaltmalar",
                ],
            },
            "Paragraf": {
                "phase": "TYT",
                "subskills": [
                    "Paragrafta ana fikir",
                    "Paragrafta yardımcı fikir",
                    "Paragraf tamamlama",
                    "Anlam bütünlüğü",
                ],
            },
        },
    },
    "Matematik": {
        "code": "MAT",
        "topics": {
            "Temel Kavramlar": {
                "phase": "TYT",
                "subskills": [
                    "Doğal sayılar",
                    "Tam sayılar",
                    "Rasyonel sayılar",
                    "Mutlak değer",
                ],
            },
            "Problemler": {
                "phase": "TYT",
                "subskills": [
                    "Yaş problemleri",
                    "Hız-Zaman-Yol",
                    "Kar-Zarar",
                ],
            },
            "Oran ve Orantı": {
                "phase": "TYT",
                "subskills": [
                    "Oran",
                    "Orantı",
                    "Bileşik orantı",
                ],
            },
            "Üslü Sayılar": {
                "phase": "TYT",
                "subskills": [
                    "Üslü ifadeler",
                    "Köklü ifadeler",
                    "Üslü denklemler",
                ],
            },
            "Denklemler": {
                "phase": "TYT",
                "subskills": [
                    "Birinci dereceden denklemler",
                    "İkinci dereceden denklemler",
                    "Denklem sistemleri",
                ],
            },
            "Fonksiyonlar": {
                "phase": "AYT",
                "subskills": [
                    "Fonksiyon kavramı",
                    "Birebir ve örten fonksiyonlar",
                    "Dört işlem ve bileşke fonksiyon",
                    "Polinomlar",
                ],
            },
        },
    },
    "Fizik": {
        "code": "FIZ",
        "topics": {
            "Kuvvet ve Hareket": {
                "phase": "AYT",
                "subskills": [
                    "Newton yasaları",
                    "Denge",
                    "İvme-hız ilişkisi",
                ],
            },
            "Elektrik Devreleri": {
                "phase": "AYT",
                "subskills": [
                    "Seri bağlantı",
                    "Paralel bağlantı",
                    "Ohm yasası",
                    "Güç ve enerji",
                ],
            },
        },
    },
    "Kimya": {
        "code": "KIM",
        "topics": {
            "Gazlar": {
                "phase": "AYT",
                "subskills": [
                    "Basınç-hacim ilişkisi",
                    "Boyle kanunu",
                    "Charles kanunu",
                ],
            },
            "Elektrokimya": {
                "phase": "AYT",
                "subskills": [
                    "Anot-katot",
                    "Elektroliz",
                    "Hücre potansiyeli",
                ],
            },
        },
    },
    "Biyoloji": {
        "code": "BIO",
        "topics": {
            "Hücre Solunumu": {
                "phase": "AYT",
                "subskills": [
                    "Glikoliz",
                    "Krebs döngüsü",
                    "ETS",
                ],
            },
            "Kalıtım": {
                "phase": "AYT",
                "subskills": [
                    "Gen-alel kavramı",
                    "Genotip-fenotip",
                    "Monohibrit çaprazlama",
                ],
            },
        },
    },
    "Geometri": {
        "code": "GEO",
        "topics": {
            "Üçgenler": {
                "phase": "BOTH",
                "subskills": [
                    "Açıortay",
                    "Kenarortay",
                    "Benzerlik",
                ],
            },
            "Dörtgenler": {
                "phase": "BOTH",
                "subskills": [
                    "Paralelkenar",
                    "Eşkenar dörtgen",
                    "Yamuk",
                ],
            },
        },
    },
}


def run():
    for subject_name, sdata in SEED.items():
        subject, _ = Subject.objects.get_or_create(
            code=sdata["code"],
            defaults={"name": subject_name},
        )
        for topic_name, tdata in sdata["topics"].items():
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=topic_name,
                defaults={"phase": tdata["phase"]},
            )
            for sub in tdata["subskills"]:
                Subskill.objects.get_or_create(topic=topic, name=sub)
    print("Seed işlemi tamamlandı.")