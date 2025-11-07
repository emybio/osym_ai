from typing import Dict, Any, Optional
import logging

from django.db import transaction
from rest_framework import status

from ..models import Question, Subject, Topic, Difficulty
from .ai_service import ai_service, AIProviderError

logger = logging.getLogger(__name__)

class QuestionService:
    """Service for handling question-related business logic"""

    @staticmethod
    def generate_question(data: Dict[str, Any]) -> tuple[Question, Optional[str]]:
        """Generate a new question using AI"""
        subject_name = data.get("subject", "Matematik")
        topic_name = data.get("topic", "Temel Kavramlar")
        difficulty_name = data.get("difficulty", "Orta")
        provider = data.get("provider", "openai")

        # Map subject name to database code
        subject_mapping = {
            "Matematik": Subject.MATEMATIK,
            "Fizik": Subject.FIZIK,
            "Kimya": Subject.KIMYA,
            "Biyoloji": Subject.BIYOLOJI,
            "Geometri": Subject.GEOMETRI,
        }
        subject = subject_mapping.get(subject_name, Subject.MATEMATIK)

        # Map difficulty name to database code
        difficulty_mapping = {
            "Kolay": Difficulty.EASY,
            "Orta": Difficulty.MEDIUM,
            "Zor": Difficulty.HARD,
        }
        difficulty = difficulty_mapping.get(difficulty_name, Difficulty.MEDIUM)

        try:
            # Generate question content using AI
            ai_data = ai_service.generate_question(subject_name, topic_name, difficulty_name, provider)

            # Get or create topic
            topic = Topic.objects.filter(name=topic_name).first()

            # Create question in database
            with transaction.atomic():
                question = Question.objects.create(
                    subject=subject,
                    topic=topic,
                    difficulty=difficulty,
                    stem=ai_data["stem"],
                    choices=ai_data["choices"],
                    answer=ai_data["answer"],
                    rubric=ai_data["rubric"],
                    source=ai_data["source"],
                )

            return question, None

        except AIProviderError as e:
            logger.error(f"AI provider error while generating question: {e}")
            return None, f"AI sağlayıcı hatası: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error while generating question: {e}")
            return None, f"Beklenmedik hata: {str(e)}"

    @staticmethod
    def explain_question(question_id: int, provider: str = None, force_generate: bool = False) -> tuple[str, Optional[str]]:
        """Get explanation for a question"""
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return None, "Soru bulunamadı"

        # Eğer zorla generate et değilse ve veritabanında çözüm varsa onu kullan
        if not force_generate and question.rubric and len(question.rubric.strip()) > 200:
            logger.info(f"Using saved solution for question {question_id}")
            return question.rubric, None

        # Eğer provider belirtilmemişse, sorunun kendi provider'ını kullan
        if not provider:
            provider = question.source or "openai"

        try:
            logger.info(f"Generating new solution for question {question_id} using {provider}")
            explanation = ai_service.explain_question(
                question.stem,
                question.choices,
                provider
            )

            # Yeni açıklamayı veritabanına kaydet
            question.rubric = explanation
            question.save()
            logger.info(f"Generated and saved solution for question {question_id}")

            return explanation, None
        except AIProviderError as e:
            logger.error(f"AI provider error while explaining question: {e}")
            return None, f"AI sağlayıcı hatası: {str(e)}"
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
                "by_source": {},
            }

            # Stats by subject
            for subject_choice, subject_name in Subject.choices:
                count = Question.objects.filter(subject=subject_choice).count()
                if count > 0:
                    stats["by_subject"][subject_name] = count

            # Stats by difficulty
            for diff_choice, diff_name in Difficulty.choices:
                count = Question.objects.filter(difficulty=diff_choice).count()
                if count > 0:
                    stats["by_difficulty"][diff_name] = count

            # Stats by source
            sources = Question.objects.values_list("source", flat=True).distinct()
            for source in sources:
                if source:
                    count = Question.objects.filter(source=source).count()
                    stats["by_source"][source] = count

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