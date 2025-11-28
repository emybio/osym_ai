from typing import Dict, Any, Optional
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status

from ..models import Question, Subject, Topic, Subskill, Choice, Measure, Misconception
from .ai_service import ai_service, AIProviderError
from .duplicate_prevention_service import duplicate_prevention_service

logger = logging.getLogger(__name__)

class QuestionService:
    """Service for handling question-related business logic"""

    @staticmethod
    def generate_question(data: Dict[str, Any]) -> tuple[Question, Optional[str]]:
        """
        Generate a new question using AI with duplicate prevention

        Args:
            data (Dict[str, Any]): Generation parameters including subject, topic, difficulty, provider

        Returns:
            tuple[Question, Optional[str]]: Generated question and error message if any
        """
        subject_name = data.get("subject", "Matematik")
        topic_name = data.get("topic", "Temel Kavramlar")
        difficulty = int(data.get("difficulty", 3))
        provider = data.get("provider", "openai")
        enable_duplicate_check = data.get("enable_duplicate_check", True)
        max_attempts = data.get("max_attempts", 3)  # Maksimum deneme sayısı kopya için

        try:
            # Get or create subject
            subject_code = data.get("subject_code", "MAT")
            subject, _ = Subject.objects.get_or_create(
                code=subject_code,
                defaults={"name": subject_name}
            )

            # Get or create topic
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=topic_name,
                defaults={"phase": data.get("phase", "TYT")}
            )

            # Soru üretme döngüsü (kopya kontrolü ile)
            for attempt in range(max_attempts):
                logger.info(f"Soru üretme denemesi {attempt + 1}/{max_attempts}")

                # Use new AI generator
                from ..ai_generator import generate_question_for_topic
                question = generate_question_for_topic(topic, difficulty)

                if not question:
                    logger.warning(f"Soru üretilemedi (deneme {attempt + 1})")
                    if attempt == max_attempts - 1:
                        return None, "Soru üretilemedi"
                    continue

                # Kopya kontrolü etkinse
                if enable_duplicate_check:
                    logger.info(f"Benzerlik kontrolü yapılıyor: {question.id}")

                    # Benzerlik kontrolü yap
                    similarity_check = duplicate_prevention_service.check_similarity(
                        question.question_text,
                        exclude_recent_hours=24  # Son 24 saati hariç tut
                    )

                    # Benzerlik verilerini soruya kaydet
                    question.similarity_score = similarity_check['max_similarity']
                    question.last_similarity_check = timezone.now()

                    if similarity_check['is_duplicate']:
                        logger.warning(f"Kopya soru tespit edildi! Benzerlik: {similarity_check['max_similarity']:.3f}")

                        # Benzerlik önerilerini logla
                        for recommendation in similarity_check['recommendations']:
                            logger.info(f"Öneri: {recommendation}")

                        question.is_duplicate = True
                        question.save()

                        # Son deneme ise kopya soruyu da uyarıyla birlikte döndür
                        if attempt == max_attempts - 1:
                            logger.error(f"Maksimum deneme sayısı ulaşıldı. Kopya soru kabul ediliyor.")
                            return question, f"Kopya soru tespit edildi (benzerlik: {similarity_check['max_similarity']:.2f}). Öneriler: {'; '.join(similarity_check['recommendations'][:2])}"

                        # Değilse yeni deneme yap
                        logger.info(f"Yeni soru üretilecek (deneme {attempt + 2})")
                        continue
                    else:
                        logger.info(f"Soru benzersiz kabul edildi (benzerlik: {similarity_check['max_similarity']:.3f})")
                        question.is_duplicate = False

                # Soruyu kaydet
                question.save()

                logger.info(f"Soru başarıyla üretildi: {question.id}")
                return question, None

            return None, "Maksimum deneme sayısı aşıldı"

        except Exception as e:
            logger.error(f"Unexpected error while generating question: {e}")
            return None, f"Beklenmedik hata: {str(e)}"

    @staticmethod
    def check_question_similarity(question_text: str) -> Dict[str, Any]:
        """
        Check similarity of a question text against existing questions

        Args:
            question_text (str): Question text to check

        Returns:
            Dict[str, Any]: Similarity check results
        """
        try:
            return duplicate_prevention_service.check_similarity(question_text)
        except Exception as e:
            logger.error(f"Error checking question similarity: {e}")
            return {
                'is_duplicate': False,
                'similar_questions': [],
                'max_similarity': 0.0,
                'recommendations': [f'Benzerlik kontrolü sırasında hata: {str(e)}'],
                'subject_distribution': {},
                'total_checked_questions': 0,
                'error': str(e)
            }

    @staticmethod
    def get_question_diversity_stats() -> Dict[str, Any]:
        """
        Get diversity statistics for existing questions

        Returns:
            Dict[str, Any]: Diversity statistics
        """
        try:
            return duplicate_prevention_service.get_question_diversity_stats()
        except Exception as e:
            logger.error(f"Error getting diversity stats: {e}")
            return {
                'total_questions': 0,
                'subject_distribution': {},
                'topic_distribution': {},
                'difficulty_distribution': {},
                'avg_questions_per_subject': 0,
                'diversity_score': 0,
                'error': str(e)
            }

    @staticmethod
    def batch_check_duplicates(batch_size: int = 100) -> Dict[str, Any]:
        """
        Perform batch duplicate checking on existing questions

        Args:
            batch_size (int): Batch size for processing

        Returns:
            Dict[str, Any]: Batch check results
        """
        try:
            return duplicate_prevention_service.batch_check_existing_questions(batch_size)
        except Exception as e:
            logger.error(f"Error in batch duplicate checking: {e}")
            return {
                'total_questions': 0,
                'processed_count': 0,
                'duplicate_groups': [],
                'duplicate_rate': 0,
                'error': str(e)
            }

    @staticmethod
    def mark_question_duplicates(question_ids: list) -> Dict[str, Any]:
        """
        Manually mark questions as duplicates based on similarity check

        Args:
            question_ids (list): List of question IDs to check and mark

        Returns:
            Dict[str, Any]: Results of duplicate marking
        """
        try:
            marked_count = 0
            errors = []

            for question_id in question_ids:
                try:
                    question = Question.objects.get(id=question_id)

                    # Benzerlik kontrolü yap
                    similarity_check = duplicate_prevention_service.check_similarity(
                        question.question_text,
                        exclude_recent_hours=0  # Tüm soruları kontrol et
                    )

                    # Sonuçları soruya kaydet
                    question.similarity_score = similarity_check['max_similarity']
                    question.last_similarity_check = timezone.now()
                    question.is_duplicate = similarity_check['is_duplicate']
                    question.save()

                    if similarity_check['is_duplicate']:
                        marked_count += 1
                        logger.info(f"Question {question_id} marked as duplicate")

                except Question.DoesNotExist:
                    errors.append(f"Question {question_id} not found")
                except Exception as e:
                    errors.append(f"Error processing question {question_id}: {str(e)}")

            return {
                'processed_count': len(question_ids),
                'marked_count': marked_count,
                'errors': errors
            }

        except Exception as e:
            logger.error(f"Error marking question duplicates: {e}")
            return {
                'processed_count': 0,
                'marked_count': 0,
                'errors': [str(e)]
            }

    @staticmethod
    def explain_question(question_id: str, provider: str = None, force_generate: bool = False) -> tuple[str, Optional[str]]:
        """Get explanation for a question"""
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return None, "Soru bulunamadı"

        # Eğer zorla generate et değilse ve veritabanında çözüm varsa onu kullan
        if not force_generate and question.explanation and len(question.explanation.strip()) > 200:
            logger.info(f"Using saved explanation for question {question_id}")
            return question.explanation, None

        try:
            logger.info(f"Question {question_id} already has explanation in database")
            return question.explanation or "Açıklama bulunmuyor", None
        except Exception as e:
            logger.error(f"Unexpected error while explaining question: {e}")
            return None, f"Beklenmedik hata: {str(e)}"

    @staticmethod
    def get_question_stats() -> Dict[str, Any]:
        """Get statistics about generated questions"""
        try:
            stats = {
                "total_questions": Question.objects.count(),
                "by_subject": {},
                "by_difficulty": {},
                "by_cognitive": {},
            }

            # Stats by subject
            subjects = Subject.objects.all()
            for subject in subjects:
                count = Question.objects.filter(subject=subject).count()
                if count > 0:
                    stats["by_subject"][subject.name] = count

            # Stats by difficulty (1-5 scale)
            for difficulty in range(1, 6):
                count = Question.objects.filter(difficulty=difficulty).count()
                if count > 0:
                    difficulty_name = ["Çok Kolay", "Kolay", "Orta", "Zor", "Çok Zor"][difficulty-1]
                    stats["by_difficulty"][difficulty_name] = count

            # Stats by cognitive level
            cognitive_levels = Question.objects.values_list("cognitive", flat=True).distinct()
            for cognitive in cognitive_levels:
                if cognitive:
                    count = Question.objects.filter(cognitive=cognitive).count()
                    stats["by_cognitive"][cognitive] = count

            return stats
        except Exception as e:
            logger.error(f"Error getting question stats: {e}")
            return {}

    @staticmethod
    def delete_old_questions(days_old: int = 30) -> int:
        """Delete questions older than specified days"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_old)
        deleted_count, _ = Question.objects.filter(created_at__lt=cutoff_date).delete()
        logger.info(f"Deleted {deleted_count} old questions")
        return deleted_count

# Singleton instance
question_service = QuestionService()