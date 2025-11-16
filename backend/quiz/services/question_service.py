from typing import Dict, Any, Optional
import logging

from django.db import transaction
from rest_framework import status

from ..models import Question, Subject, Topic, Subskill, Choice, Measure, Misconception
from .ai_service import ai_service, AIProviderError

logger = logging.getLogger(__name__)

class QuestionService:
    """Service for handling question-related business logic"""

    @staticmethod
    def generate_question(data: Dict[str, Any]) -> tuple[Question, Optional[str]]:
        """Generate a new question using AI"""
        subject_name = data.get("subject", "Matematik")
        topic_name = data.get("topic", "Temel Kavramlar")
        difficulty = int(data.get("difficulty", 3))
        provider = data.get("provider", "openai")

        try:
            # Get or create subject
            subject, _ = Subject.objects.get_or_create(
                code="MAT",
                defaults={"name": "Matematik"}
            )

            # Get or create topic
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=topic_name,
                defaults={"phase": "TYT"}
            )

            # Use new AI generator
            from ..ai_generator import generate_question_for_topic
            question = generate_question_for_topic(topic, difficulty)

            if not question:
                return None, "Soru üretilemedi"

            return question, None

        except Exception as e:
            logger.error(f"Unexpected error while generating question: {e}")
            return None, f"Beklenmedik hata: {str(e)}"

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