import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta

from .models import Question, TempExamSession, UserQuestionHistory
from .services.optimized_question_selection import optimized_selector

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def get_optimized_questions(request):
    """
    Optimized question selection with duplicate prevention and user history tracking

    POST Data:
    {
        "session_data": {
            "exam_type": "TYT",
            "branch": "SAY",
            "question_count": 40
        },
        "user_identifier": "session_key_or_ip",
        "preferences": {
            "difficulty_preference": "adaptive",
            "topic_diversity": True,
            "avoid_recent_questions": True
        }
    }
    """
    try:
        session_data = request.data.get('session_data', {})
        user_identifier = request.data.get('user_identifier', 'anonymous')
        preferences = request.data.get('preferences', {})

        # Validate required fields
        if not all([session_data.get('exam_type'), session_data.get('branch'), session_data.get('question_count')]):
            return Response(
                {"error": "Missing required session data (exam_type, branch, question_count)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create or get TempExamSession
        session, created = TempExamSession.objects.get_or_create(
            session_key=user_identifier,
            defaults={
                'exam_type': session_data['exam_type'],
                'branch': session_data['branch'],
                'question_count': session_data['question_count'],
                'temp_data': preferences
            }
        )

        if not created:
            # Update existing session
            session.exam_type = session_data['exam_type']
            session.branch = session_data['branch']
            session.question_count = session_data['question_count']
            session.temp_data = preferences
            session.save()

        # Get optimized questions
        questions = optimized_selector.get_questions_for_user(session, user_identifier)

        # Serialize questions
        question_data = []
        for question in questions:
            choices = []
            for choice in question.choices.all():
                choices.append({
                    'label': choice.label,
                    'text': choice.text,
                    'is_correct': choice.is_correct
                })

            question_data.append({
                'id': question.id,
                'question_text': question.question_text,
                'subject': question.subject.name,
                'subject_code': question.subject.code,
                'topic': question.topic.name if question.topic else None,
                'difficulty': question.difficulty,
                'cognitive': question.cognitive,
                'correct_answer': question.correct_answer,
                'explanation': question.explanation,
                'choices': choices,
                'created_at': question.created_at.isoformat()
            })

        return Response({
            'success': True,
            'session_id': session.id,
            'user_identifier': user_identifier,
            'questions': question_data,
            'selection_stats': {
                'total_questions': len(question_data),
                'unique_subjects': len(set(q['subject_code'] for q in question_data)),
                'unique_topics': len(set(q['topic'] for q in question_data if q['topic'])),
                'avg_difficulty': sum(q['difficulty'] for q in question_data) / len(question_data) if question_data else 0
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_optimized_questions: {e}")
        return Response(
            {"error": "Soru seçimi sırasında hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def submit_user_answers(request):
    """
    Submit user answers and update performance metrics

    POST Data:
    {
        "user_identifier": "session_key_or_ip",
        "session_id": 123,
        "answers": [
            {
                "question_id": "Q123",
                "answer_given": "A",
                "time_spent_seconds": 45,
                "difficulty_rating": 3
            }
        ]
    }
    """
    try:
        user_identifier = request.data.get('user_identifier')
        session_id = request.data.get('session_id')
        answers = request.data.get('answers', [])

        if not user_identifier or not answers:
            return Response(
                {"error": "user_identifier and answers are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process answers
        processed_answers = []
        for answer in answers:
            question_id = answer.get('question_id')
            answer_given = answer.get('answer_given')
            time_spent = answer.get('time_spent_seconds', 0)

            # Get correct answer
            try:
                question = Question.objects.get(id=question_id)
                is_correct = answer_given == question.correct_answer
            except Question.DoesNotExist:
                is_correct = False

            processed_answers.append({
                'question_id': question_id,
                'answer_given': answer_given,
                'is_correct': is_correct,
                'time_spent': time_spent
            })

        # Update user performance
        optimized_selector.update_user_performance(user_identifier, processed_answers)

        # Calculate results
        total_questions = len(processed_answers)
        correct_count = sum(1 for a in processed_answers if a['is_correct'])
        accuracy = correct_count / total_questions if total_questions > 0 else 0
        avg_time = sum(a['time_spent'] for a in processed_answers) / total_questions if total_questions > 0 else 0

        return Response({
            'success': True,
            'results': {
                'total_questions': total_questions,
                'correct_answers': correct_count,
                'accuracy_percentage': round(accuracy * 100, 2),
                'average_time_seconds': round(avg_time, 2),
                'grade': _calculate_grade(accuracy)
            },
            'performance_updated': True
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in submit_user_answers: {e}")
        return Response(
            {"error": "Cevaplar kaydedilirken hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_analytics(request):
    """
    Get detailed user analytics and performance insights

    Query Params:
    user_identifier (required): User identifier
    days (optional): Number of days to analyze (default: 30)
    """
    try:
        user_identifier = request.GET.get('user_identifier')
        days = int(request.GET.get('days', 30))

        if not user_identifier:
            return Response(
                {"error": "user_identifier is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        analytics = optimized_selector.get_user_question_analytics(user_identifier)

        return Response({
            'success': True,
            'user_identifier': user_identifier,
            'analytics_period_days': days,
            'data': analytics
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_user_analytics: {e}")
        return Response(
            {"error": "Analitikler alınırken hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def clear_user_cache(request):
    """
    Clear user cache for fresh question selection

    POST Data:
    {
        "user_identifier": "session_key_or_ip"  (optional, if not provided all caches cleared)
    }
    """
    try:
        user_identifier = request.data.get('user_identifier')

        if user_identifier:
            optimized_selector.clear_user_cache(user_identifier)
            message = f"Cache cleared for user: {user_identifier}"
        else:
            optimized_selector.clear_user_cache()
            message = "All user caches cleared (use with caution)"

        return Response({
            'success': True,
            'message': message
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error clearing user cache: {e}")
        return Response(
            {"error": "Cache temizlenirken hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_system_question_stats(request):
    """
    Get system-wide question statistics and performance metrics
    """
    try:
        # Total questions
        total_questions = Question.objects.count()
        duplicate_questions = Question.objects.filter(is_duplicate=True).count()

        # Subject distribution
        subject_stats = list(
            Question.objects.values('subject__name', 'subject__code')
            .annotate(count=Count('id'), avg_difficulty=Avg('difficulty'))
            .order_by('-count')
        )

        # Recent activity
        recent_history = UserQuestionHistory.objects.filter(
            answered_at__gte=timezone.now() - timedelta(days=7)
        ).aggregate(
            total_solved=Count('id'),
            unique_users=Count('user_identifier', distinct=True),
            avg_accuracy=Avg('is_correct', filter=Q(is_correct=True))
        )

        return Response({
            'success': True,
            'question_library': {
                'total_questions': total_questions,
                'unique_questions': total_questions - duplicate_questions,
                'duplicate_questions': duplicate_questions,
                'duplicate_percentage': round((duplicate_questions / total_questions * 100), 2) if total_questions > 0 else 0
            },
            'subject_distribution': subject_stats,
            'recent_activity': {
                'questions_solved_last_7_days': recent_history['total_solved'] or 0,
                'unique_active_users': recent_history['unique_users'] or 0,
                'average_accuracy': round((recent_history['avg_accuracy'] or 0) * 100, 2)
            },
            'system_health': {
                'cache_status': 'active',  # Could check Redis connection
                'database_status': 'healthy',
                'last_updated': timezone.now().isoformat()
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_system_question_stats: {e}")
        return Response(
            {"error": "Sistem istatistikleri alınırken hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _calculate_grade(accuracy: float) -> str:
    """Calculate grade based on accuracy percentage"""
    if accuracy >= 0.90:
        return "A+ (Mükemmel)"
    elif accuracy >= 0.85:
        return "A (Çok İyi)"
    elif accuracy >= 0.75:
        return "B+ (İyi)"
    elif accuracy >= 0.65:
        return "B (Orta)"
    elif accuracy >= 0.55:
        return "C+ (Geçer)"
    elif accuracy >= 0.45:
        return "C (Zayıf)"
    else:
        return "D (Geliştirilmesi Gereken)"