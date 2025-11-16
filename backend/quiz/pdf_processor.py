import os
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

from django.conf import settings
from django.utils import timezone
from langchain_community.document_loaders import PyPDFLoader
# Claude entegrasyonu - OpenAI olmadan
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma

from .models import PDFDocument, Subject, Topic, PastQuestion


class SimpleTextSplitter:
    """Simple text splitter alternative to langchain's RecursiveCharacterTextSplitter"""

    def __init__(self, chunk_size=1000, chunk_overlap=200, length_function=len):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function

    def split_documents(self, documents):
        """Split documents into chunks"""
        chunks = []
        for doc in documents:
            text = doc.page_content
            chunks.extend(self._split_text(text, doc.metadata))
        return chunks

    def _split_text(self, text, metadata):
        """Split text into chunks"""
        if self.length_function(text) <= self.chunk_size:
            return [type('Document', (), {'page_content': text, 'metadata': metadata})()]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end >= len(text):
                chunks.append(type('Document', (), {'page_content': text[start:], 'metadata': metadata})())
                break

            # Try to find a sentence break near the chunk size
            best_break = end
            for i in range(end, max(start + self.chunk_size // 2, start + 1), -1):
                if text[i] in '.!?\n' and i < len(text) - 1:
                    best_break = i + 1
                    break

            chunk_text = text[start:best_break]
            chunks.append(type('Document', (), {'page_content': chunk_text, 'metadata': metadata})())

            start = best_break - self.chunk_overlap
            if start < 0:
                start = 0

        return chunks


def process_pdf_document(pdf_document: PDFDocument) -> Dict[str, Any]:
    """
    PDF dokümanını işler ve embedding veritabanına ekler.
    """
    try:
        print(f"Processing PDF: {pdf_document.title}")

        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            # PDF dosyasını geçici dosyaya kopyala
            with pdf_document.file.open('rb') as pdf_file:
                tmp_file.write(pdf_file.read())

            temp_path = tmp_file.name

        try:
            # PDF'i yükle ve metinleri çıkar
            loader = PyPDFLoader(temp_path)
            pages = loader.load_and_split()

            if not pages:
                return {
                    'success': False,
                    'message': f"PDF'de metin bulunamadı: {pdf_document.title}",
                    'errors': {'pdf_loading': 'No text content found'}
                }

            # Metinleri parçalara ayır
            text_splitter = SimpleTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )

            chunks = text_splitter.split_documents(pages)

            # Her parçaya metadata ekle
            for chunk in chunks:
                chunk.metadata.update({
                    'pdf_id': pdf_document.id,
                    'pdf_title': pdf_document.title,
                    'document_type': pdf_document.document_type,
                    'subject': pdf_document.subject.code if pdf_document.subject else None,
                    'exam_type': pdf_document.exam_type,
                    'year': pdf_document.year,
                    'processed_at': timezone.now().isoformat()
                })

            # Claude ile entegre analiz - OpenAI embeddings kullanmadan
            if pdf_document.document_type == "PAST_EXAM":
                # Doğrudan soru çıkarımına git
                extract_past_questions(pdf_document, pages)
            else:
                # Müfredat için basit metin analizi
                analyze_curriculum_content(pdf_document, chunks)

            print(f"Successfully processed {len(chunks)} chunks from {pdf_document.title}")

            return {
                'success': True,
                'message': f"PDF başarıyla işlendi. {len(chunks)} parça oluşturuldu.",
                'chunks_count': len(chunks),
                'pages_count': len(pages)
            }

        finally:
            # Geçici dosyayı temizle
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'pdf_title': pdf_document.title
        }

        print(f"Error processing PDF {pdf_document.title}: {str(e)}")

        return {
            'success': False,
            'message': f"PDF işlenirken hata oluştu: {str(e)}",
            'errors': error_details
        }


def extract_past_questions(pdf_document: PDFDocument, pages: List[Any]) -> Dict[str, Any]:
    """
    Geçmiş sınav PDF'lerinden soruları ayrıştırır.
    """
    try:
        if not pdf_document.subject or not pdf_document.year:
            print("Skipping question extraction - missing subject or year")
            return {'success': True, 'extracted_count': 0}

        extracted_count = 0
        exam_type = pdf_document.exam_type or "TYT"

        # Basit bir soru ayrıştırma mantığı (gerçek uygulamada daha gelişmiş olmalı)
        # Burada her sayfayı bir potansiyel soru olarak işliyoruz
        for i, page in enumerate(pages):
            text = page.page_content.strip()

            # Metin içinde potansiyel soru kalıplarını ara
            # Bu kısım gerçek uygulamada AI ile daha gelişmiş olmalı
            if len(text) > 100:  # Minimum karakter kontrolü
                # İlgili konuları bul (basit bir eşleştirme)
                topic = find_relevant_topic(pdf_document.subject, text)

                if topic:
                    # PastQuestion oluştur
                    PastQuestion.objects.get_or_create(
                        year=pdf_document.year,
                        exam=exam_type,
                        subject=pdf_document.subject,
                        topic=topic,
                        question_text=text[:500],  # İlk 500 karakter
                        defaults={
                            'choices': {'A': '...', 'B': '...', 'C': '...', 'D': '...', 'E': '...'},
                            'correct_answer': 'A',
                            'cognitive_level': 'Kavrama',
                            'difficulty': 3
                        }
                    )
                    extracted_count += 1

        print(f"Extracted {extracted_count} potential questions from {pdf_document.title}")

        return {
            'success': True,
            'extracted_count': extracted_count,
            'message': f"{extracted_count} potansiyel soru ayrıştırıldı."
        }

    except Exception as e:
        import traceback
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }

        print(f"Error extracting questions from {pdf_document.title}: {str(e)}")

        return {
            'success': False,
            'message': f"Soru ayrıştırılırken hata oluştu: {str(e)}",
            'errors': error_details,
            'extracted_count': 0
        }


def find_relevant_topic(subject: Subject, text: str) -> Topic:
    """
    Metne göre ilgili konuyu bulur (basit bir eşleştirme).
    """
    try:
        # Konu anahtar kelimeleri (basit bir örnek)
        topic_keywords = {
            'Türkçe': ['paragraf', 'söz', 'anlam', 'cümle', 'edat', 'baglac', 'noktalama'],
            'Matematik': ['denklem', 'fonksiyon', 'türev', 'integral', 'limit', 'logaritma'],
            'Fizik': ['kuvvet', 'hız', 'ivme', 'enerji', 'madde', 'elektrik', 'manyetizma'],
            'Kimya': ['atom', 'molekül', 'reaksiyon', 'asit', 'baz', 'tuz', 'organik'],
            'Biyoloji': ['hücre', 'DNA', 'protein', 'fotosentez', 'solunum', 'boşaltım'],
        }

        subject_name = subject.name.lower()
        keywords = topic_keywords.get(subject_name, [])

        if not keywords:
            # İlk konuyu varsayılan olarak döndür
            return Topic.objects.filter(subject=subject).first()

        # Metinde anahtar kelimeleri ara
        text_lower = text.lower()
        best_topic = None
        best_score = 0

        for topic in Topic.objects.filter(subject=subject):
            score = 0
            topic_name_lower = topic.name.lower()

            # Konu adı metinde geçiyorsa puan ver
            if topic_name_lower in text_lower:
                score += 5

            # Anahtar kelimeler için puan ver
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_topic = topic

        return best_topic or Topic.objects.filter(subject=subject).first()

    except Exception as e:
        print(f"Error finding relevant topic: {str(e)}")
        return None


def bulk_upload_pdfs(pdf_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Çoklu PDF yükleme işlemi.

    Args:
        pdf_files: [{
            'title': str,
            'description': str,
            'file': File,
            'document_type': str,
            'subject_code': str,
            'exam_type': str,
            'year': int
        }]
    """
    results = {
        'success_count': 0,
        'error_count': 0,
        'errors': [],
        'uploaded_files': []
    }

    for pdf_data in pdf_files:
        try:
            # Subject'i bul
            subject = None
            if pdf_data.get('subject_code'):
                subject = Subject.objects.get(code=pdf_data['subject_code'])

            # PDFDocument oluştur
            pdf_doc = PDFDocument.objects.create(
                title=pdf_data['title'],
                description=pdf_data.get('description', ''),
                document_type=pdf_data['document_type'],
                subject=subject,
                exam_type=pdf_data.get('exam_type', ''),
                year=pdf_data.get('year'),
                file=pdf_data['file']
            )

            results['uploaded_files'].append(pdf_doc.title)
            results['success_count'] += 1

        except Exception as e:
            error_msg = f"{pdf_data.get('title', 'Unknown file')}: {str(e)}"
            results['errors'].append(error_msg)
            results['error_count'] += 1

    return results


def get_embedding_stats() -> Dict[str, Any]:
    """
    Embedding veritabanı istatistiklerini döner.
    """
    stats = {}

    try:
        embeddings = OpenAIEmbeddings()

        # YKS müfredat veritabanı
        try:
            yks_db = Chroma(persist_directory="chroma_yks_pdf", embedding_function=embeddings)
            stats['curriculum'] = {
                'exists': True,
                'collection_count': yks_db._collection.count()
            }
        except Exception:
            stats['curriculum'] = {'exists': False}

        # Geçmiş sorular veritabanı
        try:
            past_db = Chroma(persist_directory="chroma_past", embedding_function=embeddings)
            stats['past_exams'] = {
                'exists': True,
                'collection_count': past_db._collection.count()
            }
        except Exception:
            stats['past_exams'] = {'exists': False}

        # PDF dokümanları
        stats['pdf_documents'] = {
            'total': PDFDocument.objects.count(),
            'processed': PDFDocument.objects.filter(is_processed=True).count(),
            'pending': PDFDocument.objects.filter(is_processed=False).count()
        }

    except Exception as e:
        stats['error'] = str(e)

    return stats