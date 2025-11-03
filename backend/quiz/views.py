import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Question
from .serializers import QuestionSerializer
from .services import question_service

logger = logging.getLogger(__name__)

@api_view(["POST"])
def generate_question(request):
    """Generate a new question using AI"""
    try:
        question, error = question_service.generate_question(request.data)

        if error:
            return Response(
                {"error": error, "detail": error},
                status=status.HTTP_502_BAD_GATEWAY
            )

        serializer = QuestionSerializer(question)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Unexpected error in generate_question: {e}")
        return Response(
            {"error": "Beklenmedik bir hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
def explain(request, pk: int):
    """Generate explanation for a question"""
    try:
        explanation, error = question_service.explain_question(
            pk,
            request.data.get("provider", "openai")
        )

        if error:
            return Response(
                {"error": error, "detail": error},
                status=status.HTTP_502_BAD_GATEWAY if "AI sağlayıcı" in error else status.HTTP_404_NOT_FOUND
            )

        return Response({"explanation": explanation})

    except Exception as e:
        logger.error(f"Unexpected error in explain: {e}")
        return Response(
            {"error": "Beklenmedik bir hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def question_stats(request):
    """Get statistics about generated questions"""
    try:
        stats = question_service.get_question_stats()
        return Response(stats)
    except Exception as e:
        logger.error(f"Error getting question stats: {e}")
        return Response(
            {"error": "İstatistikler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["DELETE"])
def cleanup_questions(request):
    """Delete old questions (admin only)"""
    if not request.user.is_staff:
        return Response(
            {"error": "Bu işlem için yetkiniz yok"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        days_old = int(request.query_params.get("days_old", 30))
        deleted_count = question_service.delete_old_questions(days_old)
        return Response({
            "message": f"{deleted_count} adet eski soru silindi",
            "deleted_count": deleted_count
        })
    except ValueError:
        return Response(
            {"error": "Geçersiz days_old parametresi"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in cleanup_questions: {e}")
        return Response(
            {"error": "Temizlik işlemi başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )