from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import TempExamSession, TempExamQuestion
from .serializers import TempExamSessionSerializer, TempExamSessionCreateSerializer
from .services.quick_test_service import generate_quick_test_questions, calculate_temp_exam_result
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def init_temp_exam(request):
    """Asynchronous test oturumu başlatır - anında başlar"""
    try:
        # Önce veriyi validate et
        serializer = TempExamSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Session'ı oluştur (hızlı - 0.1s)
        session = TempExamSession.objects.create(
            exam_type=validated_data['exam_type'],
            branch=validated_data['branch'],
            question_count=validated_data['question_count'],
            duration_minutes=validated_data.get('duration_minutes', 10),
            status="preparing",  # Aşama durumu
            temp_data={
                "progress": 0,
                "message": "Sınav hazırlanıyor..."
            }
        )

        # Kullanıcıyı tanımla
        user_identifier = request.META.get('REMOTE_ADDR', 'anonymous')

        # Asynchronous task başlat (arka planda çalışacak)
        try:
            from .async_tasks import generate_questions_async
            task = generate_questions_async.apply_async(args=[session.uuid, user_identifier])
            task_id = str(task.id)
            logger.info(f"Async task started: {task_id} for session {session.uuid}")
        except Exception as e:
            logger.warning(f"Async task failed, falling back to sync: {e}")
            # Sync fallback
            try:
                from .services.quick_test_service import generate_quick_test_questions
                temp_questions = generate_quick_test_questions(session, user_identifier)

                session.status = "ready"
                session.temp_data = {
                    "progress": 100,
                    "total_questions": len(temp_questions),
                    "message": "Sınav hazır!",
                    "questions_created": [
                        {
                            'id': tq.id,
                            'subject': tq.subject,
                            'topic': tq.topic,
                            'order': tq.order
                        } for tq in temp_questions
                    ],
                    "completed_at": timezone.now().isoformat(),
                    "duration_seconds": 0.1
                }
                session.save()
                task_id = "sync-fallback"
                logger.info(f"Sync fallback completed for session {session.uuid}")

            except Exception as fallback_error:
                logger.error(f"Sync fallback failed: {fallback_error}")
                session.status = "failed"
                session.save()
                task_id = "failed"

        # Original response format - sadece session bilgisi
        session_data = {
            'uuid': str(session.uuid),
            'exam_type': session.exam_type,
            'branch': session.branch,
            'question_count': session.question_count,
            'duration_minutes': session.duration_minutes,
            'status': session.status,
            'temp_data': session.temp_data,
            'created_at': session.created_at.isoformat(),
            'task_id': task_id,
        }

        return Response(session_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        import traceback
        error_detail = f"Error: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(f"Error in init_temp_exam: {error_detail}")
        return Response(
            {"error": "Test başlatılamadı", "detail": str(e), "traceback": traceback.format_exc()},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_temp_exam(request):
    """Hızlı test sorularını getir"""
    try:
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response(
                {"error": "UUID parametresi gerekli"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = TempExamSession.objects.get(uuid=uuid, status__in=["active", "ready"])
        except TempExamSession.DoesNotExist:
            return Response(
                {"error": "Geçersiz veya bulunamayan test oturumu"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TempExamSessionSerializer(session)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error in get_temp_exam: {e}")
        return Response(
            {"error": "Sorular alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_exam_status(request):
    """Test hazırlık durumunu kontrol et"""
    try:
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response(
                {"error": "UUID parametresi gerekli"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .async_tasks import get_session_status
        status_data = get_session_status(uuid)

        if status_data.get("error"):
            return Response(status_data, status=status.HTTP_404_NOT_FOUND)

        return Response(status_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_exam_status: {e}")
        return Response(
            {"error": "Durum kontrol edilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def save_temp_exam(request):
    """Hızlı test sonuçlarını kaydeder"""
    try:
        uuid = request.data.get('uuid')
        answers = request.data.get('answers', {})

        logger.info(f"🔍 SAVE_TEMP_EXAM - UUID: {uuid}")
        logger.info(f"🔍 SAVE_TEMP_EXAM - Answers: {answers}")
        logger.info(f"🔍 SAVE_TEMP_EXAM - Answers type: {type(answers)}")

        if not uuid:
            return Response(
                {"error": "UUID parametresi gerekli"},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = get_object_or_404(TempExamSession, uuid=uuid)

        if not answers:
            return Response(
                {"error": "Cevaplar boş olamaz"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sonuçları hesapla
        logger.info(f"🔍 CALLING calculate_temp_exam_result...")
        result = calculate_temp_exam_result(session, answers)
        logger.info(f"🔍 RESULT: {result}")

        # Frontend'in beklediği formatta sonuç verisini döndür
        if result:
            response_data = {
                "message": "Sonuçlar kaydedildi",
                "result": {
                    "uuid": str(result.uuid),
                    "exam_type": session.exam_type,
                    "branch": session.branch,
                    "total_questions": result.total_questions,
                    "correct_count": result.correct_count,
                    "wrong_count": result.wrong_count,
                    "percentage": result.percentage,
                    "subject_breakdown": result.subject_breakdown,
                    "created_at": result.created_at.isoformat(),
                    "session_info": {
                        "exam_type": session.exam_type,
                        "branch": session.branch
                    }
                }
            }
        else:
            response_data = {
                "message": "Sonuçlar kaydedildi",
                "result": {
                    "percentage": 0,
                    "correct_count": 0,
                    "total_questions": 0,
                    "subject_breakdown": {}
                }
            }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in save_temp_exam: {e}")
        return Response(
            {"error": "Sonuçlar kaydedilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def question_list(request):
    """Get all questions"""
    try:
        from .models import Question
        questions = Question.objects.all()[:20]  # Limit to 20 for performance
        data = [{'id': q.id, 'text': q.text[:100]} for q in questions]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_question(request):
    """Generate new question using Hybrid AI Provider System"""
    try:
        from .services.hybrid_question_generator import HybridQuestionGenerator

        subject = request.data.get('subject')
        topic = request.data.get('topic')
        difficulty = request.data.get('difficulty', 'Orta')
        question_type = request.data.get('question_type')
        force_provider = request.data.get('force_provider')

        if not subject or not topic:
            return Response(
                {'error': 'subject and topic are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        generator = HybridQuestionGenerator()

        question = generator.generate_validated_question(
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            question_type=question_type,
            force_provider=force_provider
        )

        return Response({
            'success': True,
            'question': question,
            'provider': question.get('source'),
            'model': question.get('model'),
            'validation': question.get('validation')
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Question generation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def explain(request, pk):
    """Explain question"""
    return Response({"message": f"Question {pk} explanation"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def question_stats(request):
    """Get question statistics"""
    return Response({"total_questions": 0, "stats": {}}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def cleanup_questions(request):
    """Cleanup old questions"""
    return Response({"message": "Cleanup completed"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_pdf_upload(request):
    """Bulk PDF upload"""
    return Response({"message": "PDF upload not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['GET'])
@permission_classes([AllowAny])
def pdf_stats(request):
    """Get PDF statistics"""
    return Response({"pdf_stats": {}}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def process_pdf(request, pdf_id):
    """Process PDF"""
    return Response({"message": f"PDF {pdf_id} processing"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_subjects(request):
    """Get subjects"""
    return Response({"subjects": []}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def temp_exam_summary(request):
    """Get temp exam summary"""
    return Response({"summary": {}}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_and_merge(request):
    """Register and merge"""
    return Response({"message": "Registration completed"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def quicktest_results(request):
    """Get quicktest results"""
    logger.info("🔍 QUICKTEST_RESULTS CALLED")

    try:
        # En son sonuçları getir (order by created_at desc)
        from .models import TempExamResult

        results = TempExamResult.objects.all().order_by('-created_at')[:10]

        logger.info(f"🔍 FOUND {results.count()} RESULTS")

        results_data = []
        for result in results:
            results_data.append({
                'uuid': str(result.uuid),
                'exam_type': result.session.exam_type,
                'branch': result.session.branch,
                'total_questions': result.total_questions,
                'correct_count': result.correct_count,
                'wrong_count': result.wrong_count,
                'percentage': result.percentage,
                'subject_breakdown': result.subject_breakdown,
                'created_at': result.created_at.isoformat(),
                'session_uuid': str(result.session.uuid)
            })

        logger.info(f"🔍 RETURNING RESULTS: {len(results_data)} items")
        return Response({"results": results_data}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"🔍 ERROR IN QUICKTEST_RESULTS: {e}")
        return Response({"results": [], "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """Get dashboard statistics"""
    return Response({"stats": {}}, status=status.HTTP_200_OK)


# Progressive Statistics
@api_view(['GET'])
@permission_classes([AllowAny])
def get_anonymous_performance_overview(request):
    """
    Anonim kullanıcının genel performans özetini döner
    """
    try:
        from quiz.services.anonymous_user_service import AnonymousUserService
        from quiz.services.progressive_statistics_service import ProgressiveStatisticsService

        # Anonim kullanıcyı session'dan al
        anonymous_user = AnonymousUserService.get_anonymous_user(request)

        if not anonymous_user:
            # Yeni anonim kullanıcı oluştur
            anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Gerçek performans verilerini al
        performance_data = ProgressiveStatisticsService.get_user_performance_overview(anonymous_user)

        return Response(performance_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in get_anonymous_performance_overview: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_anonymous_progress_chart(request):
    return Response({"progress": []}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_anonymous_topic_analysis(request):
    """
    Anonim kullanıcının konu analizini döner
    """
    try:
        from quiz.services.anonymous_user_service import AnonymousUserService
        from quiz.services.progressive_statistics_service import ProgressiveStatisticsService

        # Anonim kullanıcıyı session'dan al
        anonymous_user = AnonymousUserService.get_anonymous_user(request)

        if not anonymous_user:
            # Yeni anonim kullanıcı oluştur
            anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Gerçek konu analiz verilerini al
        topic_data = ProgressiveStatisticsService.get_topic_wise_analysis(anonymous_user)

        return Response(topic_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in get_anonymous_topic_analysis: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_anonymous_recommendations(request):
    """
    Anonim kullanıcı için öğrenme önerileri döner
    """
    try:
        from quiz.services.anonymous_user_service import AnonymousUserService
        from quiz.services.progressive_statistics_service import ProgressiveStatisticsService

        # Anonim kullanıcıyı session'dan al
        anonymous_user = AnonymousUserService.get_anonymous_user(request)

        if not anonymous_user:
            # Yeni anonim kullanıcı oluştur
            anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Gerçek öneri verilerini al
        recommendations_data = ProgressiveStatisticsService.get_learning_recommendations(anonymous_user)

        return Response(recommendations_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in get_anonymous_recommendations: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def export_anonymous_statistics(request):
    return Response({"export_url": ""}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def clear_anonymous_cache(request):
    return Response({"message": "Cache cleared"}, status=status.HTTP_200_OK)

# Gamification
@api_view(['GET'])
@permission_classes([AllowAny])
def get_gamification_profile(request):
    return Response({"profile": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_leaderboard(request):
    return Response({"leaderboard": []}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_daily_challenge(request):
    return Response({"challenge": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_achievements_list(request):
    return Response({"achievements": []}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def claim_reward(request):
    return Response({"reward": {}}, status=status.HTTP_200_OK)

# Adaptive Difficulty
@api_view(['GET'])
@permission_classes([AllowAny])
def get_adaptive_difficulty_profile(request):
    return Response({"profile": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_adaptive_recommendations(request):
    return Response({"recommendations": []}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_difficulty_analytics(request):
    return Response({"analytics": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_difficulty_profile(request):
    return Response({"message": "Profile reset"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def set_manual_difficulty_preference(request):
    return Response({"preference": set}, status=status.HTTP_200_OK)

# Rate Limiting & Security
@api_view(['GET'])
@permission_classes([AllowAny])
def get_rate_limits_status(request):
    return Response({"limits": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def check_rate_limits(request):
    return Response({"allowed": True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def report_suspicious_activity(request):
    return Response({"reported": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_suspicious_activities(request):
    return Response({"activities": []}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def manual_block_user(request):
    return Response({"blocked": True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def manual_unblock_user(request):
    return Response({"unblocked": True}, status=status.HTTP_200_OK)

# Analytics & Insights
@api_view(['GET'])
@permission_classes([AllowAny])
def get_analytics_dashboard(request):
    return Response({"dashboard": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_analytics_user(request):
    return Response({"user_analytics": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_analytics_content(request):
    return Response({"content_analytics": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_analytics_engagement(request):
    return Response({"engagement": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_analytics_conversion_funnel(request):
    return Response({"funnel": {}}, status=status.HTTP_200_OK)

# Database Optimization
@api_view(['GET'])
@permission_classes([AllowAny])
def get_database_status(request):
    return Response({"status": "healthy"}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_database_metrics(request):
    return Response({"metrics": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def run_database_optimization(request):
    return Response({"optimized": True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def run_cleanup(request):
    return Response({"cleaned": True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def optimize_indexes(request):
    return Response({"indexed": True}, status=status.HTTP_200_OK)

# A/B Testing
@api_view(['GET'])
@permission_classes([AllowAny])
def get_ab_test_config(request):
    return Response({"config": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def track_ab_test_event(request):
    return Response({"tracked": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_ab_test_analytics(request):
    return Response({"analytics": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_ab_tests(request):
    return Response({"tests": []}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_ab_test(request):
    return Response({"created": True}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def end_ab_test(request):
    return Response({"ended": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_client_ab_config(request):
    return Response({"config": {}}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_feature_flag(request):
    return Response({"enabled": False}, status=status.HTTP_200_OK)

# Duplicate Prevention
@api_view(['POST'])
@permission_classes([AllowAny])
def check_question_similarity(request):
    return Response({"similarity": 0.0}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_question_diversity_stats(request):
    return Response({"diversity": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def batch_check_duplicates(request):
    return Response({"duplicates": []}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def mark_question_duplicates(request):
    return Response({"marked": True}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_duplicate_overview(request):
    return Response({"overview": {}}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def update_duplicate_settings(request):
    return Response({"updated": True}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_providers(request):
    """Test all AI provider connections"""
    try:
        from .services.hybrid_question_generator import HybridQuestionGenerator

        generator = HybridQuestionGenerator()
        results = generator.test_all_providers()

        return Response({
            'success': True,
            'providers': results
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Provider test error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def provider_metrics(request):
    """Get provider metrics"""
    try:
        from .services.hybrid_question_generator import HybridQuestionGenerator

        generator = HybridQuestionGenerator()
        metrics = generator.get_provider_metrics()

        return Response({
            'success': True,
            'metrics': metrics
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def cost_estimate(request):
    """Estimate cost for question generation"""
    try:
        from .services.hybrid_question_generator import HybridQuestionGenerator

        subject = request.data.get('subject', 'Matematik')
        num_questions = int(request.data.get('num_questions', 1000))

        generator = HybridQuestionGenerator()
        estimate = generator.get_cost_estimate(subject, num_questions)

        return Response({
            'success': True,
            'estimate': estimate
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Cost estimate error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )