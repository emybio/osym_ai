import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ..models import Question

logger = logging.getLogger(__name__)

class DuplicatePreventionService:
    """
    Soru benzerlik kontrol servisi - Semantic duplicate prevention

    Bu servis, yeni oluşturulan soruların mevcut sorularla benzerliğini kontrol eder
    ve kopya soru oluşturmayı önler. TF-IDF vektörleme ve cosine similarity kullanır.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the duplicate prevention service

        Args:
            similarity_threshold (float): Benzerlik eşiği (0-1 arası)
        """
        self.similarity_threshold = similarity_threshold
        self._vectorizer = None  # Lazy initialization
        self._initialized = False

        # Türkçe stop words
        self.turkish_stop_words = {
            've', 'ile', 'ama', 'fakat', 'ancak', 'için', 'gibi', 'kadar', 'olarak',
            'bu', 'şu', 'o', 'bir', 'iki', 'üç', 'dört', 'beş', 'da', 'de', 'mi', 'mı',
            'mu', 'mü', 'çok', 'az', 'daha', 'en', 'her', 'tüm', 'bütün', 'hangi',
            'nasıl', 'ne', 'neden', 'nerede', 'ne zaman', 'kaç', 'kim', 'neyi', 'kime'
        }

    @property
    def vectorizer(self):
        """Lazy initialization of vectorizer"""
        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # Turkish stop words will be handled manually
                ngram_range=(1, 3),  # 1-3 gram arası
                min_df=1,  # Minimum document frequency
                max_df=0.95,  # Maximum document frequency
                lowercase=True,
                analyzer='word',
                token_pattern=r'\b\w+\b'
            )
            # Initialize vectorizer with existing questions only when first used
            self._initialize_vectorizer()
        return self._vectorizer

    def _initialize_vectorizer(self):
        """Mevcut sorular ile vectorizer'ı başlat"""
        try:
            # Performans için sadece ilk 100 soruyu al
            existing_questions = Question.objects.all()[:100]
            question_texts = [self._preprocess_text(q.question_text) for q in existing_questions]

            # Boş olmayan metinleri filtrele
            question_texts = [text for text in question_texts if text.strip()]

            if question_texts:
                self._vectorizer.fit(question_texts)
                self._initialized = True
                logger.info(f"Vectorizer {len(question_texts)} soru ile başlatıldı")
            else:
                logger.warning("Başlangıç için soru bulunamadı")
                self._initialized = True

        except Exception as e:
            logger.error(f"Vectorizer başlatılırken hata: {e}")
            self._initialized = True  # Hata durumunda tekrar denemesin

    def _preprocess_text(self, text: str) -> str:
        """
        Türkçe metni ön işlemden geçir

        Args:
            text (str): İşlenecek metin

        Returns:
            str: İşlenmiş metin
        """
        # Lowercase
        text = text.lower()

        # Türkçe karakterleri normalize et
        text = text.replace('ı', 'i')
        text = text.replace('ö', 'o')
        text = text.replace('ü', 'u')
        text = text.replace('ş', 's')
        text = text.replace('ç', 'c')
        text = text.replace('ğ', 'g')

        # Noktalama işaretlerini kaldır
        import re
        text = re.sub(r'[^\w\s]', ' ', text)

        # Ekstra boşlukları kaldır
        text = re.sub(r'\s+', ' ', text).strip()

        # Stop words'leri kaldır
        words = text.split()
        words = [word for word in words if word not in self.turkish_stop_words]

        return ' '.join(words)

    def check_similarity(self, new_question_text: str, exclude_recent_hours: int = 24) -> Dict:
        """
        Yeni sorunun mevcut sorularla benzerliğini kontrol et

        Args:
            new_question_text (str): Yeni soru metni
            exclude_recent_hours (int): Kontrol dışı bırakılacak son X saat

        Returns:
            dict: {
                'is_duplicate': bool,
                'similar_questions': list,
                'max_similarity': float,
                'recommendations': list,
                'subject_distribution': dict
            }
        """
        try:
            # Ön işlemden geçir
            processed_new_text = self._preprocess_text(new_question_text)

            if not processed_new_text.strip():
                return {
                    'is_duplicate': False,
                    'similar_questions': [],
                    'max_similarity': 0.0,
                    'recommendations': ['Soru metni boş veya geçersiz'],
                    'subject_distribution': {}
                }

            # Performans optimizasyonu: Son 50 soru ile sınırla
            cutoff_time = timezone.now() - timedelta(hours=exclude_recent_hours)
            existing_questions = Question.objects.exclude(
                created_at__gte=cutoff_time
            ).order_by('-created_at')[:50]  # Sadece son 50 soruyu kontrol et

            if not existing_questions:
                logger.info("Kontrol için mevcut soru bulunamadı")
                return {
                    'is_duplicate': False,
                    'similar_questions': [],
                    'max_similarity': 0.0,
                    'recommendations': ['İlk soru oluşturuluyor'],
                    'subject_distribution': {}
                }

            # Mevcut soruları ön işlemden geçir
            existing_texts = []
            question_objects = []

            for question in existing_questions:
                processed_text = self._preprocess_text(question.question_text)
                if processed_text.strip():
                    existing_texts.append(processed_text)
                    question_objects.append(question)

            if not existing_texts:
                return {
                    'is_duplicate': False,
                    'similar_questions': [],
                    'max_similarity': 0.0,
                    'recommendations': ['İşlenebilir mevcut soru bulunamadı'],
                    'subject_distribution': {}
                }

            # Vectorizer'ı güncelle
            all_texts = existing_texts + [processed_new_text]

            # Vektörleri oluştur
            try:
                text_vectors = self.vectorizer.fit_transform(all_texts)
            except ValueError as e:
                # Eğer vocabulary boş ise, basit vectorizer kullan
                logger.warning(f"TF-IDF hatası: {e}, basit vectorizer kullanılıyor")
                simple_vectorizer = TfidfVectorizer(
                    max_features=100,
                    min_df=1,
                    lowercase=True,
                    token_pattern=r'\b\w+\b'
                )
                text_vectors = simple_vectorizer.fit_transform(all_texts)

            # Yeni sorunun vektörünü al
            new_question_vector = text_vectors[-1]

            # Benzerlik skorlarını hesapla
            similarity_scores = cosine_similarity(new_question_vector, text_vectors[:-1])[0]

            # Eşik değerini aşan benzerlikleri bul
            similar_indices = np.where(similarity_scores >= self.similarity_threshold)[0]
            similar_questions = []

            for idx in similar_indices:
                similar_question = question_objects[idx]
                similarity_score = similarity_scores[idx]

                similar_questions.append({
                    'id': similar_question.id,
                    'subject': similar_question.subject.name,
                    'subject_code': similar_question.subject.code,
                    'topic': similar_question.topic.name if similar_question.topic else None,
                    'difficulty': similar_question.difficulty,
                    'similarity_score': float(similarity_score),
                    'question_text_preview': similar_question.question_text[:100] + "..." if len(similar_question.question_text) > 100 else similar_question.question_text,
                    'created_at': similar_question.created_at.isoformat()
                })

            # En yüksek benzerlik skoru
            max_similarity = float(similarity_scores.max()) if len(similarity_scores) > 0 else 0.0

            # Konu dağılımı analizi
            subject_distribution = {}
            for question in question_objects:
                subject_name = question.subject.name
                if subject_name not in subject_distribution:
                    subject_distribution[subject_name] = 0
                subject_distribution[subject_name] += 1

            # Öneriler oluştur
            recommendations = self._generate_recommendations(
                new_question_text, similar_questions, max_similarity, subject_distribution
            )

            # En çok tekrarlanan konuları tespit et
            if subject_distribution:
                max_subject_count = max(subject_distribution.values())
                most_common_subjects = [
                    subject for subject, count in subject_distribution.items()
                    if count >= max_subject_count * 0.8
                ]
                if most_common_subjects and len(most_common_subjects) < len(subject_distribution):
                    recommendations.append(f"Daha az kullanılan konuları deneyin: {', '.join(most_common_subjects)} dışındaki konular")

            result = {
                'is_duplicate': max_similarity >= self.similarity_threshold,
                'similar_questions': similar_questions,
                'max_similarity': max_similarity,
                'recommendations': recommendations,
                'subject_distribution': subject_distribution,
                'total_checked_questions': len(existing_texts)
            }

            # Loglama
            if result['is_duplicate']:
                logger.warning(f"Kopya soru tespit edildi! Benzerlik: {max_similarity:.3f}")
                logger.info(f"Benzer soru sayısı: {len(similar_questions)}")

            return result

        except Exception as e:
            logger.error(f"Benzerlik kontrolü sırasında hata: {e}")
            return {
                'is_duplicate': False,
                'similar_questions': [],
                'max_similarity': 0.0,
                'recommendations': [f'Benzerlik kontrolü sırasında hata oluştu: {str(e)}'],
                'subject_distribution': {}
            }

    def _generate_recommendations(self, new_text: str, similar_questions: List, max_similarity: float, subject_distribution: Dict) -> List[str]:
        """Benzerlik durumuna göre öneriler oluştur"""
        recommendations = []

        if max_similarity >= 0.95:
            recommendations.append("Soru neredeyse identical - tamamen farklı bir konu veya yaklaşım deneyin")
        elif max_similarity >= 0.90:
            recommendations.append("Soru çok benzer - konuyu farklı bir perspektiften ele alın")
        elif max_similarity >= 0.85:
            recommendations.append("Yüksek benzerlik - soruyu önemli ölçüde değiştirin")
        elif max_similarity >= 0.75:
            recommendations.append("Orta seviye benzerlik - zorluk seviyesini veya soru tipini değiştirin")

        # Konu spesifik öneriler
        if similar_questions:
            subjects = set(q['subject'] for q in similar_questions)
            if len(subjects) == 1:
                subject_name = list(subjects)[0]
                recommendations.append(f"Tekrarlanan ders: {subject_name} - Farklı bir ders deneyin")

            # Zorluk seviyesi analizi
            difficulties = [q['difficulty'] for q in similar_questions]
            if difficulties:
                avg_difficulty = sum(difficulties) / len(difficulties)
                recommendations.append(f"Benzer soruların ortalama zorluğu: {avg_difficulty:.1f} - Farklı zorluk deneyin")

        # Konu dağılımı önerileri
        if subject_distribution:
            total_questions = sum(subject_distribution.values())
            for subject, count in subject_distribution.items():
                percentage = (count / total_questions) * 100
                if percentage > 40:  # %40'tan fazlası bir konudaysa
                    recommendations.append(f"{subject} konusu zaten %{percentage:.0f} oranında - daha az kullanılan konuları deneyin")
                    break

        return recommendations

    def get_question_diversity_stats(self) -> Dict:
        """Mevcut soru çeşitlilik istatistikleri"""
        try:
            questions = Question.objects.all()

            if not questions.exists():
                return {
                    'total_questions': 0,
                    'subject_distribution': {},
                    'topic_distribution': {},
                    'difficulty_distribution': {},
                    'avg_questions_per_subject': 0,
                    'diversity_score': 0
                }

            # Konu dağılımı
            subjects = questions.values('subject__name').annotate(count=Count('id'))
            subject_distribution = {item['subject__name']: item['count'] for item in subjects}

            # Konu başlığı dağılımı
            topics = questions.values('topic__name').annotate(count=Count('id'))
            topic_distribution = {item['topic__name']: item['count'] for item in topics if item['topic__name']}

            # Zorluk dağılımı
            difficulties = questions.values('difficulty').annotate(count=Count('id'))
            difficulty_distribution = {f"Zorluk {item['difficulty']}": item['count'] for item in difficulties}

            # Çeşitlilik skoru ( Shannon entropi )
            total_questions = questions.count()
            diversity_score = 0
            if total_questions > 0:
                for count in subject_distribution.values():
                    probability = count / total_questions
                    if probability > 0:
                        diversity_score -= probability * np.log2(probability)
                diversity_score = round(diversity_score, 3)

            return {
                'total_questions': total_questions,
                'subject_distribution': subject_distribution,
                'topic_distribution': topic_distribution,
                'difficulty_distribution': difficulty_distribution,
                'avg_questions_per_subject': round(total_questions / max(len(subject_distribution), 1), 1),
                'diversity_score': diversity_score
            }

        except Exception as e:
            logger.error(f"Çeşitlilik istatistikleri alınırken hata: {e}")
            return {
                'total_questions': 0,
                'subject_distribution': {},
                'topic_distribution': {},
                'difficulty_distribution': {},
                'avg_questions_per_subject': 0,
                'diversity_score': 0
            }

    def batch_check_existing_questions(self, batch_size: int = 100) -> Dict:
        """Mevcut sorular için toplu benzerlik kontrolü"""
        try:
            questions = Question.objects.all()
            total_questions = questions.count()
            duplicate_groups = []
            processed_count = 0

            logger.info(f"Toplu benzerlik kontrolü başlatılıyor: {total_questions} soru")

            # Her soruyu diğerleriyle karşılaştır
            for i, question in enumerate(questions):
                if i % batch_size == 0:
                    logger.info(f"İşlenen soru: {i}/{total_questions}")

                # Bu soru için benzerlik kontrolü
                similarity_check = self.check_similarity(
                    question.question_text,
                    exclude_recent_hours=0  # Tüm soruları kontrol et
                )

                if similarity_check['is_duplicate']:
                    duplicate_groups.append({
                        'question_id': question.id,
                        'similar_to': similarity_check['similar_questions'][:3],  # İlk 3 benzer
                        'max_similarity': similarity_check['max_similarity']
                    })

                processed_count += 1

            logger.info(f"Toplu kontrol tamamlandı: {processed_count} soru, {len(duplicate_groups)} potansiyel kopya")

            return {
                'total_questions': total_questions,
                'processed_count': processed_count,
                'duplicate_groups': duplicate_groups,
                'duplicate_rate': round(len(duplicate_groups) / total_questions * 100, 2) if total_questions > 0 else 0
            }

        except Exception as e:
            logger.error(f"Toplu kontrol sırasında hata: {e}")
            return {
                'total_questions': 0,
                'processed_count': 0,
                'duplicate_groups': [],
                'duplicate_rate': 0,
                'error': str(e)
            }

# Global instance with lazy initialization
_duplicate_prevention_service = None

def get_duplicate_prevention_service():
    """Get or create the duplicate prevention service instance"""
    global _duplicate_prevention_service
    if _duplicate_prevention_service is None:
        _duplicate_prevention_service = DuplicatePreventionService()
    return _duplicate_prevention_service

# Keep backward compatibility - this will be evaluated when accessed
class _DuplicatePreventionServiceProxy:
    def __getattr__(self, name):
        service = get_duplicate_prevention_service()
        return getattr(service, name)

duplicate_prevention_service = _DuplicatePreventionServiceProxy()