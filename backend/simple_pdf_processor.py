#!/usr/bin/env python
"""
Simple PDF processor for development - no Redis/Celery needed
"""
import os
import sys
import django

# Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
sys.path.append('/mnt/c/Users/kur06/Downloads/osym_ai/backend')
django.setup()

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from quiz.models import PDFDocument, Question, Subject, Topic, Choice, Measure, Misconception, Subskill

def process_pdf_simpler(pdf_id):
    """
    Basit PDF işleme - Redis/Celery olmadan
    """
    try:
        pdf_doc = PDFDocument.objects.get(id=pdf_id)
        print(f"PDF isleniyor: {pdf_doc.title}")

        # PDF'i yükle
        file_path = pdf_doc.file.path
        print(f"Dosya yolu: {file_path}")

        # PDF metnini çıkar
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        print(f"PDF sayfa sayisi: {len(documents)}")

        # Metin örneği
        full_text = ""
        for i, doc in enumerate(documents):
            page_text = doc.page_content
            if page_text.strip():
                full_text += page_text + "\n"
                if i < 3:  # İlk 3 sayfanın özetini göster
                    print(f"Sayfa {i+1} ({len(page_text)} karakter): {page_text[:100]}...")

        # Embedding oluştur ( ChromaDB için)
        print("Embedding'ler olusturuluyor...")
        embeddings = OpenAIEmbeddings()

        # ChromaDB persist directory kontrolü
        persist_dir = "chroma_yks_pdf_dev"
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
            print(f"Klasor olusturuldu: {persist_dir}")

        # ChromaDB'ye yükle
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir
        )

        print("PDF basariyla islendi!")
        print(f"Toplam metin uzunlugu: {len(full_text)} karakter")

        return True

    except Exception as e:
        print(f"PDF isleme hatasi: {e}")
        return False

def generate_question_from_pdf_content(pdf_id, question_count=5):
    """
    PDF içeriğinden soru üret
    """
    try:
        pdf_doc = PDFDocument.objects.get(id=pdf_id)
        print(f"{pdf_doc.title} PDF'inden {question_count} soru uretiliyor...")

        # PDF'i yükle
        loader = PyPDFLoader(pdf_doc.file.path)
        documents = loader.load()

        # Örnek sorular oluştur (ilk 5 sayfadan)
        sample_texts = []
        for doc in documents[:5]:
            if doc.page_content.strip() and len(doc.page_content) > 100:
                sample_texts.append(doc.page_content[:500])

        print(f"{len(sample_texts)} adet ornek metin bulundu")

        # Basit örnek sorular üret
        questions_created = 0
        subject_map = {
            "MAT": "Matematik",
            "TR": "Türkçe",
            "FIZ": "Fizik",
            "KIM": "Kimya",
            "BIO": "Biyoloji"
        }

        for i, text in enumerate(sample_texts[:question_count]):
            try:
                # Basit soru şablonu
                question_text = f"Bu metne dayalı olarak {i+1}. soru:\n\n{text[:200]}...\n\nBu metinde ana fikir nedir?"

                # Konu tahmin et (PDF adına göre)
                subject_code = "TR"  # Varsayılan
                if "mat" in pdf_doc.title.lower():
                    subject_code = "MAT"
                elif "fiz" in pdf_doc.title.lower():
                    subject_code = "FIZ"
                elif "kim" in pdf_doc.title.lower():
                    subject_code = "KIM"
                elif "biy" in pdf_doc.title.lower():
                    subject_code = "BIO"

                # Subject ve Topic oluştur
                subject, _ = Subject.objects.get_or_create(
                    code=subject_code,
                    defaults={"name": subject_map.get(subject_code, "Genel")}
                )

                topic, _ = Topic.objects.get_or_create(
                    subject=subject,
                    name="PDF'den Türetilen Konu",
                    defaults={"phase": "TYT"}
                )

                # Question oluştur
                question_id = f"PDF-{pdf_id}-{i+1:04d}"
                question = Question.objects.create(
                    id=question_id,
                    subject=subject,
                    topic=topic,
                    question_text=question_text,
                    difficulty=3,
                    cognitive="Kavrama",
                    correct_answer="A",
                    explanation=f"Bu soru {pdf_doc.title} PDF'inin {i+1}. sayfasından türetilmiştir."
                )

                # Choice'lar oluştur
                choices_data = {
                    "A": "Metnin ana fikri doğru bir şekilde kavranmıştır",
                    "B": "Metnin ana fikri tamamen yanlış yorumlanmıştır",
                    "C": "Metinde ana fikir bulunmamaktadır",
                    "D": "Metin sadece detaylardan ibarettir",
                    "E": "Metin anlamsız ifadeler içermektedir"
                }

                for label, text in choices_data.items():
                    Choice.objects.create(
                        question=question,
                        label=label,
                        text=text,
                        is_correct=(label == "A")
                    )

                questions_created += 1
                print(f"OK Soru {questions_created} olusturuldu: {question_id}")

            except Exception as e:
                print(f"HATA Soru {i+1} olusturulamadi: {e}")
                continue

        print(f"BASARILI Toplam {questions_created} soru basariyla olusturuldu!")
        return questions_created

    except Exception as e:
        print(f"Soru uretme hatasi: {e}")
        return 0

if __name__ == "__main__":
    print("Basit PDF Isleyici Baslatildi")
    print("="*50)

    # Mevcut PDF'leri listele
    pdfs = PDFDocument.objects.all()
    print(f"Bulunan PDF sayisi: {pdfs.count()}")

    for pdf in pdfs:
        print(f"\nPDF: {pdf.title}")
        print(f"   ID: {pdf.id}")
        print(f"   Tur: {pdf.document_type}")
        print(f"   Boyut: {pdf.file.size} bytes")

    print("\n" + "="*50)

    # İşlem için PDF seç
    if pdfs.exists():
        first_pdf = pdfs.first()
        print(f"Islenecek PDF: {first_pdf.title} (ID: {first_pdf.id})")

        # PDF işle
        if process_pdf_simpler(first_pdf.id):
            # Sorular üret
            generate_question_from_pdf_content(first_pdf.id, question_count=3)
        else:
            print("PDF isleme basarisiz!")
    else:
        print("Islenecek PDF bulunamadi!")