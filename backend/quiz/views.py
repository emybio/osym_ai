import logging
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from django.db import models

from .models import Question, PDFDocument, PDFProcessingLog, Subject, TempExamSession, TempExamResult
from .serializers import (
    QuestionSerializer, PDFDocumentSerializer, TempExamSessionCreateSerializer,
    TempExamSessionSerializer, TempExamAnswerSerializer, TempExamResultSerializer,
    ExamResultSerializer, RegisterAndMergeSerializer
)
from .services import question_service
from .pdf_processor import process_pdf_document, get_embedding_stats
# from .services.quick_test_service import merge_temp_results, generate_quick_test_questions, calculate_temp_exam_result
from .services.anonymous_user_service import AnonymousUserService
from .services.progressive_statistics_service import ProgressiveStatisticsService
from .services.gamification_service import GamificationService
from .services.adaptive_difficulty_service import AdaptiveDifficultyService
from .services.rate_limiting_service import RateLimitingService
from .services.analytics_service import AnalyticsService
from .services.database_optimization_service import DatabaseOptimizationService
from .services.ab_testing_service import ABTestService

# Temporary placeholders for quick test functions (to be fixed)
def merge_temp_results(session, answers):
    return {"message": "Temporary placeholder"}

def generate_quick_test_questions(session):
    return []

def calculate_temp_exam_result(session, answers):
    return {"score": 0, "total": 1}

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

        # Generate and save solution immediately
        try:
            solution, solution_error = question_service.explain_question(
                question.id,
                question.source
            )

            if solution and not solution_error:
                # Update the question with the generated solution
                question.rubric = solution
                question.save()
                logger.info(f"Solution generated and saved for question {question.id}")
            else:
                logger.warning(f"Failed to generate solution for question {question.id}: {solution_error}")
        except Exception as e:
            logger.error(f"Error generating solution for question {question.id}: {e}")

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
            request.data.get("provider")  # Boş olursa sorunun kendi source'unu kullanır
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
def question_list(request):
    """List all questions in the database"""
    try:
        questions = Question.objects.all().order_by('-created_at')
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error getting question list: {e}")
        return Response(
            {"error": "Sorular listelenemedi", "detail": str(e)},
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


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def bulk_pdf_upload(request):
    """Bulk upload PDF files (admin only)"""
    if not request.user.is_staff:
        return Response(
            {"error": "Bu işlem için admin yetkisi gereklidir"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {"error": "Hiç PDF dosyası yüklenmedi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'uploaded_files': []
        }

        for file in files:
            try:
                # File validation
                if not file.name.lower().endswith('.pdf'):
                    raise ValueError("Sadece PDF dosyaları kabul edilir")

                if file.size > 50 * 1024 * 1024:  # 50MB
                    raise ValueError("Dosya boyutu 50MB'den küçük olmalıdır")

                # Extract metadata from filename or form data
                title = request.POST.get(f'title_{file.name}', file.name.replace('.pdf', ''))
                description = request.POST.get(f'description_{file.name}', '')
                document_type = request.POST.get(f'document_type_{file.name}', 'PAST_EXAM')
                subject_code = request.POST.get(f'subject_code_{file.name}', '')
                exam_type = request.POST.get(f'exam_type_{file.name}', 'TYT')
                year = request.POST.get(f'year_{file.name}', '')

                # Validate required fields
                if document_type not in ['CURRICULUM', 'PAST_EXAM']:
                    raise ValueError("Geçersiz doküman türü")

                # Find subject if provided
                subject = None
                if subject_code:
                    from .models import Subject
                    try:
                        subject = Subject.objects.get(code=subject_code)
                    except Subject.DoesNotExist:
                        raise ValueError(f"Ders kodu bulunamadı: {subject_code}")

                # Convert year to int if provided
                year_int = None
                if year:
                    try:
                        year_int = int(year)
                    except ValueError:
                        raise ValueError("Geçersiz yıl formatı")

                # Create PDFDocument
                pdf_doc = PDFDocument.objects.create(
                    title=title,
                    description=description,
                    document_type=document_type,
                    subject=subject,
                    exam_type=exam_type,
                    year=year_int,
                    file=file
                )

                results['uploaded_files'].append({
                    'id': pdf_doc.id,
                    'title': pdf_doc.title,
                    'filename': file.name
                })
                results['success_count'] += 1

            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'file': file.name,
                    'error': str(e)
                })

        return Response({
            'message': f"Toplam {len(files)} dosyadan {results['success_count']} tanesi yüklendi, {results['error_count']} tanesi hata verdi.",
            'success_count': results['success_count'],
            'error_count': results['error_count'],
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in bulk_pdf_upload: {e}")
        return Response(
            {"error": "PDF yükleme işlemi başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def pdf_stats(request):
    """Get PDF and embedding statistics (admin only)"""
    if not request.user.is_staff:
        return Response(
            {"error": "Bu işlem için admin yetkisi gereklidir"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Database stats
        db_stats = {
            'total_pdfs': PDFDocument.objects.count(),
            'processed_pdfs': PDFDocument.objects.filter(is_processed=True).count(),
            'pending_pdfs': PDFDocument.objects.filter(is_processed=False).count(),
            'curriculum_pdfs': PDFDocument.objects.filter(document_type='CURRICULUM').count(),
            'past_exam_pdfs': PDFDocument.objects.filter(document_type='PAST_EXAM').count(),
        }

        # Processing logs
        processing_stats = {
            'total_logs': PDFProcessingLog.objects.count(),
            'completed': PDFProcessingLog.objects.filter(status='COMPLETED').count(),
            'failed': PDFProcessingLog.objects.filter(status='FAILED').count(),
            'processing': PDFProcessingLog.objects.filter(status='PROCESSING').count(),
        }

        # Embedding stats
        embedding_stats = get_embedding_stats()

        return Response({
            'database': db_stats,
            'processing': processing_stats,
            'embeddings': embedding_stats
        })

    except Exception as e:
        logger.error(f"Error getting PDF stats: {e}")
        return Response(
            {"error": "İstatistikler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def process_pdf(request, pdf_id):
    """Process a single PDF (admin only)"""
    if not request.user.is_staff:
        return Response(
            {"error": "Bu işlem için admin yetkisi gereklidir"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        pdf_obj = get_object_or_404(PDFDocument, id=pdf_id)

        if pdf_obj.is_processed:
            return Response(
                {"error": "Bu PDF zaten işlenmiş"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create processing log
        log = PDFProcessingLog.objects.create(
            pdf_document=pdf_obj,
            status="PROCESSING",
            message="API tarafından tetiklendi"
        )

        # Process the PDF
        result = process_pdf_document(pdf_obj)

        if result['success']:
            pdf_obj.is_processed = True
            pdf_obj.save()

            log.status = "COMPLETED"
            log.message = result['message']
            log.save()

            return Response({
                'message': 'PDF başarıyla işlendi',
                'result': result
            })

        else:
            log.status = "FAILED"
            log.message = result['message']
            log.error_details = result.get('errors', {})
            log.save()

            return Response(
                {'error': 'PDF işlenemedi', 'details': result},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Error processing PDF {pdf_id}: {e}")
        return Response(
            {"error": "PDF işleme sırasında hata oluştu", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_subjects(request):
    """Get all subjects"""
    try:
        subjects = Subject.objects.all().order_by('name')
        data = [
            {
                'id': subject.id,
                'code': subject.code,
                'name': subject.name
            }
            for subject in subjects
        ]
        return Response(data)
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}")
        return Response(
            {"error": "Dersler alınamadı"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ================== HIZLI TEST APİLERİ ==================

@api_view(["POST"])
@permission_classes([AllowAny])
def init_temp_exam(request):
    """Yeni hızlı test oturumu başlat"""
    try:
        # Rate limiting kontrolü
        rate_limit_check = RateLimitingService.check_rate_limit(request, 'test_creation')
        if not rate_limit_check['allowed']:
            return Response(
                {"error": "Çok fazla test oluşturma denemesi. Lütfen bekleyin.", "retry_after": rate_limit_check.get('reset_time', 60)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # TODO: Re-enable anti-spam when anonymous_user is properly implemented
        # Anti-spam kontrolü
        # anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)
        # anti_spam_check = RateLimitingService.check_anti_spam(request, anonymous_user)
        # if not anti_spam_check['allowed']:
        #     violations = anti_spam_check.get('violations', [])
        #     violation_reason = violations[0].get('reason', 'Suspicious activity detected') if violations else 'Suspicious activity detected'
        #     return Response(
        #         {"error": f"Güvenlik kontrolü başarısız: {violation_reason}"},
        #         status=status.HTTP_429_TOO_MANY_REQUESTS
        #     )

        # # Test limitlerini kontrol et
        # can_take, message = anonymous_user.can_take_test()
        # if not can_take:
        #     return Response(
        #         {"error": message},
        #         status=status.HTTP_429_TOO_MANY_REQUESTS
        #     )

        serializer = TempExamSessionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session = serializer.save()

        # TODO: Oturumu anonim kullanıcıyla ilişkilendir when anonymous_user field is added to TempExamSession
        # session.anonymous_user = anonymous_user
        # session.save()

        # Adaptif zorluk ile soruları oluştur
        try:
            # Önce basit soru oluşturmayı dene
            from .services.quick_test_service import generate_quick_test_questions

            # Kullanıcıyı tanımlamak için IP adresi kullan
            user_identifier = request.META.get('REMOTE_ADDR', 'anonymous')
            questions = generate_quick_test_questions(session, user_identifier)

            # Eğer adaptif zorluk hizmeti düzgün çalışıyorsa onu kullan
            if questions:
                # TODO: anonymous_user eklendiğinde adaptif zorluğu tekrar aktif et
                # from .services.adaptive_difficulty_service import AdaptiveDifficultyService
                # questions = AdaptiveDifficultyService.generate_adaptive_questions(session, anonymous_user)
                pass

        except Exception as e:
            logger.error(f"Question generation error: {e}")
            questions = []

        if not questions:
            return Response(
                {"error": "Test soruları oluşturulamadı. Lütfen farklı bir branş seçin."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Oturum bilgileriyle birlikte döndür
        session_serializer = TempExamSessionSerializer(session)
        return Response(session_serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in init_temp_exam: {e}")
        return Response(
            {"error": "Test başlatılamadı", "detail": str(e)},
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
            session = TempExamSession.objects.get(uuid=uuid, status="active")
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


@api_view(["POST"])
@permission_classes([AllowAny])
def save_temp_exam(request):
    """Hızlı test cevaplarını kaydet ve sonuçları hesapla"""
    try:
        # Rate limiting kontrolü
        rate_limit_check = RateLimitingService.check_rate_limit(request, 'test_submission')
        if not rate_limit_check['allowed']:
            return Response(
                {"error": "Çok fazla test gönderme denemesi. Lütfen bekleyin.", "retry_after": rate_limit_check.get('reset_time', 60)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = TempExamAnswerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uuid = serializer.validated_data['uuid']
        answers = serializer.validated_data['answers']

        try:
            session = TempExamSession.objects.get(uuid=uuid, status="active")
        except TempExamSession.DoesNotExist:
            return Response(
                {"error": "Geçersiz veya bulunamayan test oturumu"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Sonuçları hesapla
        from .services.quick_test_service import calculate_temp_exam_result
        result = calculate_temp_exam_result(session, answers)

        # TODO: Anonim kullanıcı özellikleri ileride eklenecek
        # Anonim kullanıcıyı al veya oluştur
        # anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Oturumu tamamlandı olarak işaretle
        # session.anonymous_user = anonymous_user
        session.status = 'completed'
        session.save()

        # TODO: Sonucu anonim kullanıcıyla ilişkilendir
        # result.anonymous_user = anonymous_user
        # result.save()

        # Gelişmiş servisler geçici olarak devre dışı
        # Progressive statistics'i güncelle
        # ProgressiveStatisticsService.update_user_statistics(anonymous_user, result)

        # Gamification özelliklerini kontrol et
        # gamification_result = GamificationService.check_and_award_achievements(anonymous_user, result)
        # daily_challenge_result = GamificationService.check_daily_challenge_completion(anonymous_user, result)

        # Adaptif zorluk profilini güncelle
        # difficulty_update = AdaptiveDifficultyService.update_difficulty_profile(anonymous_user, result)

        # Basit rate limiting kaydet (anonim user olmadan)
        test_success = result.percentage >= 50  # %50 ve üzeri başarılı sayılıyor
        # TODO: anonymous_user eklendiğinde tekrar aktif et
        # RateLimitingService.record_action(
        #     request,
        #     'test_submission',
        #     success=test_success,
        #     metadata={
        #         'score': result.percentage,
        #         'correct_answers': result.correct_answers,
        #         'total_questions': result.total_questions,
        #         'test_type': session.exam_type,
        #         'branch': session.branch,
        #         'anonymous_user_id': anonymous_user.id
        #     }
        # )

        logger.info(f"Test tamamlandı: Score={result.percentage}%")

        # Sonuçları döndür
        result_serializer = TempExamResultSerializer(result)

        # Basit response (gamification olmadan)
        response_data = result_serializer.data
        # TODO: Gamification eklendiğinde tekrar aktif et
        # response_data['gamification'] = gamification_result
        # if daily_challenge_result:
        #     response_data['daily_challenge'] = daily_challenge_result

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in save_temp_exam: {e}")
        return Response(
            {"error": "Cevaplar kaydedilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def temp_exam_summary(request):
    """Hızlı test sonuç özetini getir"""
    try:
        uuid = request.query_params.get('uuid')
        if not uuid:
            return Response(
                {"error": "UUID parametresi gerekli"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = TempExamResult.objects.get(uuid=uuid, merged=False)
        except TempExamResult.DoesNotExist:
            return Response(
                {"error": "Geçersiz veya bulunamayan test sonucu"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TempExamResultSerializer(result)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error in temp_exam_summary: {e}")
        return Response(
            {"error": "Sonuçlar alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_and_merge(request):
    """Kayıt ol ve test sonucunu hesaba taşı"""
    try:
        serializer = RegisterAndMergeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        temp_result_uuid = serializer.validated_data['temp_result_uuid']
        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            with transaction.atomic():
                # Yeni kullanıcı oluştur
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                # Test sonucunu merge et
                success, message, exam_result = merge_temp_results(temp_result_uuid, user)

                if not success:
                    # User'ı sil
                    user.delete()
                    return Response(
                        {"error": message},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Başarılı response
                return Response({
                    "message": message,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email
                    },
                    "exam_result": ExamResultSerializer(exam_result).data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error in register_and_merge transaction: {e}")
            return Response(
                {"error": "Kayıt işlemi başarısız", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error in register_and_merge: {e}")
        return Response(
            {"error": "İşlem başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quicktest_results(request):
    """Kullanıcının hızlı test sonuçlarını getir"""
    try:
        from .models import ExamResult

        results = ExamResult.objects.filter(
            user=request.user,
            is_quick_test=True
        ).order_by('-created_at')

        serializer = ExamResultSerializer(results, many=True)
        return Response(serializer.data)

    except Exception as e:
        logger.error(f"Error in quicktest_results: {e}")
        return Response(
            {"error": "Sonuçlar alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Dashboard istatistikleri"""
    try:
        from .models import ExamResult

        # Hızlı test istatistikleri
        quick_tests = ExamResult.objects.filter(user=request.user, is_quick_test=True)
        quick_test_count = quick_tests.count()
        avg_score = quick_tests.aggregate(avg_score=models.Avg('percentage'))['avg_score'] or 0

        # Branş bazında performans
        branch_stats = {}
        for test in quick_tests:
            branch = test.branch
            if branch not in branch_stats:
                branch_stats[branch] = {
                    'count': 0,
                    'avg_score': 0,
                    'scores': []
                }
            branch_stats[branch]['count'] += 1
            branch_stats[branch]['scores'].append(test.percentage)

        for branch in branch_stats:
            scores = branch_stats[branch]['scores']
            branch_stats[branch]['avg_score'] = sum(scores) / len(scores) if scores else 0

        return Response({
            'quick_test_count': quick_test_count,
            'average_score': round(avg_score, 2),
            'branch_performance': branch_stats,
            'recent_tests': ExamResultSerializer(
                quick_tests[:5], many=True
            ).data
        })

    except Exception as e:
        logger.error(f"Error in dashboard_stats: {e}")
        return Response(
            {"error": "İstatistikler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== PROGRESSIVE STATISTICS API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_anonymous_performance_overview(request):
    """Anonim kullanıcı performans özetini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Performans özetini al
        performance = ProgressiveStatisticsService.get_user_performance_overview(anonymous_user)

        return Response(performance, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_anonymous_performance_overview: {e}")
        return Response(
            {"error": "Performans verileri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_anonymous_progress_chart(request):
    """Anonim kullanıcı ilerleme grafiği verilerini al"""
    try:
        period = request.query_params.get('period', 'weekly')
        if period not in ['daily', 'weekly', 'monthly', 'all_time']:
            return Response(
                {"error": "Geçersiz dönem parametresi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # İlerleme grafiği verilerini al
        progress_chart = ProgressiveStatisticsService.get_detailed_progress_chart(anonymous_user, period)

        return Response(progress_chart, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_anonymous_progress_chart: {e}")
        return Response(
            {"error": "İlerleme verileri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_anonymous_topic_analysis(request):
    """Anonim kullanıcı konu analizi al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Konu analizini al
        topic_analysis = ProgressiveStatisticsService.get_topic_wise_analysis(anonymous_user)

        return Response(topic_analysis, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_anonymous_topic_analysis: {e}")
        return Response(
            {"error": "Konu analizi alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_anonymous_recommendations(request):
    """Anonim kullanıcı öğrenme önerilerini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Öğrenme önerilerini al
        recommendations = ProgressiveStatisticsService.get_learning_recommendations(anonymous_user)

        return Response(recommendations, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_anonymous_recommendations: {e}")
        return Response(
            {"error": "Öneriler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def export_anonymous_statistics(request):
    """Anonim kullanıcı istatistiklerini dışa aktar"""
    try:
        format_type = request.query_params.get('format', 'json')
        if format_type not in ['json']:
            return Response(
                {"error": "Sadece JSON formatı desteklenmektedir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # İstatistikleri dışa aktar
        export_data = ProgressiveStatisticsService.export_user_statistics(anonymous_user, format_type)

        return Response(export_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in export_anonymous_statistics: {e}")
        return Response(
            {"error": "İstatistikler dışa aktarılamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def clear_anonymous_cache(request):
    """Anonim kullanıcı cache'ini temizle"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Cache'i temizle
        ProgressiveStatisticsService.clear_user_cache(anonymous_user)

        return Response(
            {"message": "Cache başarıyla temizlendi"},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error in clear_anonymous_cache: {e}")
        return Response(
            {"error": "Cache temizlenemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== GAMIFICATION API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_gamification_profile(request):
    """Anonim kullanıcı oyunlaştırma profilini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Gamification verilerini al
        points = GamificationService.get_user_points(anonymous_user)
        level = GamificationService.get_user_level(anonymous_user)
        level_progress = GamificationService.get_progress_to_next_level(anonymous_user)
        achievements = GamificationService.get_user_achievements(anonymous_user)
        user_rank = GamificationService.get_user_rank(anonymous_user)
        motivational_message = GamificationService.get_motivational_message(anonymous_user)

        profile = {
            'user_id': anonymous_user.id,
            'points': points,
            'level': level,
            'level_info': {
                'name': GamificationService.BADGE_LEVELS[level]['name'],
                'color': GamificationService.BADGE_LEVELS[level]['color']
            },
            'level_progress': level_progress,
            'achievements_count': len(achievements),
            'total_possible_achievements': len(GamificationService.ACHIEVEMENT_TYPES),
            'achievements': achievements,
            'rank': user_rank,
            'motivational_message': motivational_message,
            'badge_levels': GamificationService.BADGE_LEVELS
        }

        return Response(profile, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_gamification_profile: {e}")
        return Response(
            {"error": "Oyunlaştırma profili alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_leaderboard(request):
    """Lider tablosunu al"""
    try:
        limit = int(request.query_params.get('limit', 10))
        period = request.query_params.get('period', 'all_time')

        if period not in ['all_time', 'weekly', 'monthly']:
            return Response(
                {"error": "Geçersiz dönem parametresi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if limit < 1 or limit > 100:
            return Response(
                {"error": "Limit 1-100 arasında olmalıdır"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al (sıralaması için)
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Lider tablosunu al
        leaderboard = GamificationService.get_leaderboard(limit, period)
        user_rank = GamificationService.get_user_rank(anonymous_user)

        # Anonimleştir - kullanıcı ID'lerini gizle
        for entry in leaderboard:
            entry['user_id'] = None  # Gizlilik için
            # Rastgele kullanıcı adı oluştur
            entry['display_name'] = f"Kullanıcı {entry['rank']}"
            # Mevcut kullanıcıyı işaretle
            if entry['rank'] == user_rank.get('rank'):
                entry['is_current_user'] = True
            else:
                entry['is_current_user'] = False

        response = {
            'leaderboard': leaderboard,
            'period': period,
            'user_rank': user_rank,
            'total_users': user_rank.get('total_users', 0),
            'user_in_top_100': user_rank.get('rank') is not None and user_rank['rank'] <= 100
        }

        return Response(response, status=status.HTTP_200_OK)

    except ValueError:
        return Response(
            {"error": "Geçersiz limit parametresi"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in get_leaderboard: {e}")
        return Response(
            {"error": "Lider tablosu alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_daily_challenge(request):
    """Günlük meydan okumayı al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Günlük meydan okumayı al
        challenge = GamificationService.get_daily_challenge(anonymous_user)

        if not challenge:
            return Response(
                {"error": "Meydan okuma oluşturulamadı"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(challenge, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_daily_challenge: {e}")
        return Response(
            {"error": "Günlük meydan okuma alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_achievements_list(request):
    """Tüm başarıları listele"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Kullanıcının başarılarını al
        user_achievements = GamificationService.get_user_achievements(anonymous_user)
        user_achievement_keys = {a['key'] for a in user_achievements}

        # Tüm başarıları oluştur
        all_achievements = []
        for key, name in GamificationService.ACHIEVEMENT_TYPES.items():
            achievement_data = {
                'key': key,
                'name': name,
                'icon': GamificationService._get_achievement_icon(key),
                'earned': key in user_achievement_keys,
                'points': GamificationService.POINT_SYSTEM.get(key, 10)
            }

            if key in user_achievement_keys:
                # Kazanılan başarıyı bul
                user_achievement = next(a for a in user_achievements if a['key'] == key)
                achievement_data['earned_at'] = user_achievement['earned_at']

            all_achievements.append(achievement_data)

        # Kategorilere ayır
        categories = {
            'streak': [a for a in all_achievements if 'streak' in a['key']],
            'score': [a for a in all_achievements if any(x in a['key'] for x in ['perfect', 'score'])],
            'milestone': [a for a in all_achievements if 'milestone' in a['key']],
            'time': [a for a in all_achievements if any(x in a['key'] for x in ['early', 'night', 'weekend'])],
            'performance': [a for a in all_achievements if any(x in a['key'] for x in ['speed', 'persistent', 'consistent', 'improvement'])],
            'special': [a for a in all_achievements if a['key'] == 'first_test']
        }

        stats = {
            'total_achievements': len(all_achievements),
            'earned_achievements': len(user_achievements),
            'completion_percentage': round((len(user_achievements) / len(all_achievements)) * 100, 1),
            'total_points': sum(GamificationService.POINT_SYSTEM.get(a['key'], 10) for a in user_achievements)
        }

        response = {
            'categories': categories,
            'stats': stats,
            'recent_achievements': sorted(user_achievements, key=lambda x: x['earned_at'], reverse=True)[:5]
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_achievements_list: {e}")
        return Response(
            {"error": "Başarılar listelenemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def claim_reward(request):
    """Ödül talep et (gelecekteki özellik için)"""
    try:
        reward_type = request.data.get('reward_type')
        reward_id = request.data.get('reward_id')

        if not reward_type:
            return Response(
                {"error": "Ödül tipi gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Şimdilik basit bir yanıt döndür
        # Gelecekte bu daha karmaşık hale getirilebilir
        response = {
            'message': 'Ödül başarıyla talep edildi!',
            'reward_type': reward_type,
            'reward_id': reward_id,
            'claimed_at': timezone.now().isoformat()
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in claim_reward: {e}")
        return Response(
            {"error": "Ödül talep edilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== ADAPTIVE DIFFICULTY API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_adaptive_difficulty_profile(request):
    """Anonim kullanıcı adaptif zorluk profilini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Zorluk profilini al
        profile = AdaptiveDifficultyService.get_user_difficulty_profile(anonymous_user)

        return Response(profile, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_adaptive_difficulty_profile: {e}")
        return Response(
            {"error": "Zorluk profili alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_adaptive_recommendations(request):
    """Adaptif zorluk tabanlı öğrenme önerilerini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Önerileri al
        recommendations = AdaptiveDifficultyService.get_difficulty_recommendations(anonymous_user)

        response = {
            'recommendations': recommendations,
            'difficulty_levels': AdaptiveDifficultyService.DIFFICULTY_LEVELS,
            'generated_at': timezone.now().isoformat()
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_adaptive_recommendations: {e}")
        return Response(
            {"error": "Öneriler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_difficulty_profile(request):
    """Kullanıcının zorluk profilini sıfırla"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Cache'i temizle
        from django.core.cache import cache
        cache_key = f"difficulty_profile_{anonymous_user.id}"
        cache.delete(cache_key)

        # Yeni profil al (varsayılan)
        new_profile = AdaptiveDifficultyService.get_user_difficulty_profile(anonymous_user)

        return Response({
            'message': 'Zorluk profili başarıyla sıfırlandı',
            'new_profile': new_profile,
            'reset_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in reset_difficulty_profile: {e}")
        return Response(
            {"error": "Profil sıfırlanamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_difficulty_analytics(request):
    """Kullanıcının zorluk analitiklerini al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Profil ve önerileri al
        profile = AdaptiveDifficultyService.get_user_difficulty_profile(anonymous_user)
        recommendations = AdaptiveDifficultyService.get_difficulty_recommendations(anonymous_user)

        # Ek analizler
        analytics = {
            'profile': profile,
            'recommendations': recommendations,
            'difficulty_distribution': _calculate_difficulty_distribution(anonymous_user),
            'learning_trend': _calculate_learning_trend(anonymous_user),
            'confidence_trend': _calculate_confidence_trend(anonymous_user),
            'optimal_study_areas': _identify_optimal_study_areas(anonymous_user)
        }

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_difficulty_analytics: {e}")
        return Response(
            {"error": "Analitikler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def set_manual_difficulty_preference(request):
    """Manuel zorluk tercihi ayarla"""
    try:
        data = request.data
        subject_code = data.get('subject_code')
        preferred_difficulty = data.get('difficulty')

        if not subject_code or not preferred_difficulty:
            return Response(
                {"error": "Konu kodu ve zorluk seviyesi gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (1 <= preferred_difficulty <= 5):
            return Response(
                {"error": "Zorluk seviyesi 1-5 arasında olmalıdır"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Manuel tercihi cache'e kaydet
        from django.core.cache import cache
        cache_key = f"manual_difficulty_{anonymous_user.id}_{subject_code}"
        cache.set(cache_key, {
            'difficulty': preferred_difficulty,
            'set_at': timezone.now().isoformat(),
            'reason': 'manual_preference'
        }, timeout=86400 * 7)  # 1 hafta

        return Response({
            'message': 'Manuel zorluk tercihi ayarlandı',
            'subject_code': subject_code,
            'preferred_difficulty': preferred_difficulty,
            'set_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in set_manual_difficulty_preference: {e}")
        return Response(
            {"error": "Tercih ayarlanamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Helper functions for analytics
def _calculate_difficulty_distribution(anonymous_user):
    """Kullanıcının zorluk dağılımını hesapla"""
    try:
        from quiz.models import TempExamQuestion, TempExamResult

        # Son testlerdeki soru zorluklarını al
        recent_sessions = TempExamSession.objects.filter(
            anonymous_user=anonymous_user,
            status='completed'
        ).order_by('-created_at')[:5]

        difficulty_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_questions = 0

        for session in recent_sessions:
            questions = session.questions.filter(is_adaptive=True)
            for question in questions:
                difficulty = int(question.target_difficulty) if question.target_difficulty else 3
                difficulty_counts[difficulty] += 1
                total_questions += 1

        if total_questions == 0:
            return {str(i): 0 for i in range(1, 6)}

        # Yüzdeleri hesapla
        return {str(i): round((count / total_questions) * 100, 1) for i, count in difficulty_counts.items()}

    except Exception:
        return {str(i): 0 for i in range(1, 6)}


def _calculate_learning_trend(anonymous_user):
    """Öğrenme trendini hesapla"""
    try:
        from quiz.models import TempExamResult

        # Son 10 testin skorlarını al
        recent_results = TempExamResult.objects.filter(
            session__anonymous_user=anonymous_user,
            session__status='completed'
        ).order_by('-created_at')[:10]

        if len(recent_results) < 3:
            return {'trend': 'insufficient_data', 'value': 0}

        scores = [result.percentage for result in recent_results]

        # İlk yarının ortalaması vs son yarının ortalaması
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        trend_value = second_avg - first_avg

        if trend_value > 5:
            trend = 'improving'
        elif trend_value < -5:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'value': round(trend_value, 1),
            'first_average': round(first_avg, 1),
            'second_average': round(second_avg, 1)
        }

    except Exception:
        return {'trend': 'error', 'value': 0}


def _calculate_confidence_trend(anonymous_user):
    """Güven seviyesi trendini hesapla"""
    try:
        profile = AdaptiveDifficultyService.get_user_difficulty_profile(anonymous_user)
        current_confidence = profile.get('confidence_level', 0.5)

        return {
            'current_confidence': round(current_confidence, 2),
            'level': 'high' if current_confidence > 0.7 else 'medium' if current_confidence > 0.3 else 'low'
        }

    except Exception:
        return {'current_confidence': 0.5, 'level': 'medium'}


def _identify_optimal_study_areas(anonymous_user):
    """Optimal çalışma alanlarını belirle"""
    try:
        profile = AdaptiveDifficultyService.get_user_difficulty_profile(anonymous_user)
        recommendations = AdaptiveDifficultyService.get_difficulty_recommendations(anonymous_user)

        optimal_areas = []
        areas_to_improve = []

        for subject_code, data in profile.get('subject_difficulties', {}).items():
            performance = data.get('performance_data', {})
            success_rate = performance.get('success_rate', 0)
            confidence = data.get('confidence', 0)

            if success_rate >= 0.7 and confidence >= 0.7:
                optimal_areas.append({
                    'subject': subject_code,
                    'difficulty': data['recommended_difficulty'],
                    'success_rate': success_rate,
                    'confidence': confidence
                })
            elif success_rate < 0.5 and confidence >= 0.3:
                areas_to_improve.append({
                    'subject': subject_code,
                    'difficulty': data['recommended_difficulty'],
                    'success_rate': success_rate,
                    'confidence': confidence
                })

        return {
            'optimal_areas': optimal_areas,
            'areas_to_improve': areas_to_improve,
            'recommendations_count': len(recommendations)
        }

    except Exception:
        return {
            'optimal_areas': [],
            'areas_to_improve': [],
            'recommendations_count': 0
        }


# ==================== RATE LIMITING API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_rate_limits_status(request):
    """Kullanıcının rate limiting durumunu al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # İstatistikleri al
        stats = RateLimitingService.get_user_stats(request, anonymous_user)

        return Response(stats, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_rate_limits_status: {e}")
        return Response(
            {"error": "Rate limiting durumu alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def check_rate_limits(request):
    """Manuel rate limiting kontrolü yap"""
    try:
        data = request.data
        action = data.get('action', 'test_creation')

        if action not in RateLimitingService.RATE_LIMITS.keys():
            return Response(
                {"error": "Geçersiz aksiyon tipi", "valid_actions": list(RateLimitingService.RATE_LIMITS.keys())},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Rate limit kontrolü
        rate_limit_result = RateLimitingService.check_rate_limit(request, action, str(anonymous_user.id))

        # Anti-spam kontrolü
        anti_spam_result = RateLimitingService.check_anti_spam(request, anonymous_user)

        # Block durumunu kontrol et
        block_status = RateLimitingService.is_user_blocked(str(anonymous_user.id))

        response = {
            'action': action,
            'rate_limit': rate_limit_result,
            'anti_spam': anti_spam_result,
            'block_status': block_status,
            'user_id': str(anonymous_user.id),
            'timestamp': timezone.now().isoformat()
        }

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in check_rate_limits: {e}")
        return Response(
            {"error": "Rate limiting kontrolü başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def report_suspicious_activity(request):
    """
    Şüpheli aktivite bildirimi
    """
    try:
        data = request.data
        activity_type = data.get('activity_type')
        description = data.get('description', '')
        user_id = data.get('user_id')

        if not activity_type:
            return Response(
                {"error": "Aktivite tipi gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        # Şüpheli aktiviteyi kaydet
        suspicious_key = f"suspicious_{timezone.now().date()}_{activity_type}"
        suspicious_activities = cache.get(suspicious_key, [])

        activity = {
            'timestamp': timezone.now().isoformat(),
            'activity_type': activity_type,
            'description': description,
            'reported_by': str(anonymous_user.id),
            'reported_user_id': user_id,
            'ip_address': RateLimitingService._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
        }

        suspicious_activities.append(activity)

        # Son 100 aktiviteyi sakla
        if len(suspicious_activities) > 100:
            suspicious_activities = suspicious_activities[-100:]

        cache.set(suspicious_key, suspicious_activities, timeout=86400)  # 1 gün

        # Yoğun aktivite kontrolü
        recent_activities = [a for a in suspicious_activities
                            if (timezone.now() - datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00'))).total_seconds() < 3600]

        if len(recent_activities) > 20:  # 1 saatte 20'den fazla bildirim
            # Yönetici için bildirim oluştur
            logger.warning(f"High suspicious activity reports: {len(recent_activities)} in last hour")

        return Response({
            'message': 'Şüpheli aktivite başarıyla bildirildi',
            'activity_id': len(suspicious_activities),
            'total_today': len(suspicious_activities)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in report_suspicious_activity: {e}")
        return Response(
            {"error": "Bildirim gönderilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_suspicious_activities(request):
    """
    Şüpheli aktiviteleri getir (admin için)
    """
    try:
        # Admin kontrolü (basit bir kontrol)
        # Gerçek bir uygulamada burası daha güvenli olmalı
        admin_key = request.query_params.get('admin_key')
        if admin_key != 'admin123':  # Basit bir admin key - gerçek uygulamada değil!
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Son 7 günlük aktiviteleri al
        activities = []
        for i in range(7):
            date = (timezone.now().date() - timedelta(days=i)).strftime('%Y-%m-%d')
            for activity_type in ['bot_behavior', 'spam_pattern', 'abuse', 'cheating']:
                key = f"suspicious_{date}_{activity_type}"
                day_activities = cache.get(key, [])
                activities.extend(day_activities)

        # Tarihe göre sırala
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        # İstatistikler
        stats = {
            'total_activities': len(activities),
            'by_type': {},
            'by_date': {},
            'top_reporters': {}
        }

        for activity in activities:
            activity_date = activity['timestamp'][:10]
            activity_type = activity['activity_type']
            reporter = activity['reported_by']

            stats['by_type'][activity_type] = stats['by_type'].get(activity_type, 0) + 1
            stats['by_date'][activity_date] = stats['by_date'].get(activity_date, 0) + 1
            stats['top_reporters'][reporter] = stats['top_reporters'].get(reporter, 0) + 1

        return Response({
            'activities': activities[:100],  # Son 100 aktivite
            'stats': stats,
            'generated_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_suspicious_activities: {e}")
        return Response(
            {"error": "Aktiviteler alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def manual_block_user(request):
    """
    Manuel kullanıcı block'lama (admin için)
    """
    try:
        # Admin kontrolü
        admin_key = request.data.get('admin_key')
        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        user_id = data.get('user_id')
        reason = data.get('reason', 'Admin block')
        duration = data.get('duration', 3600)

        if not user_id:
            return Response(
                {"error": "Kullanıcı ID gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kullanıcıyı block'la
        success = RateLimitingService.block_user(user_id, reason, duration, {
            'blocked_by': 'admin',
            'admin_ip': RateLimitingService._get_client_ip(request)
        })

        if success:
            return Response({
                'message': f'Kullanıcı {user_id} başarıyla blocklandı',
                'reason': reason,
                'duration': duration,
                'blocked_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Block işlemi başarısız"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error in manual_block_user: {e}")
        return Response(
            {"error": "Block işlemi başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def manual_unblock_user(request):
    """
    Manuel kullanıcı unblock'lama (admin için)
    """
    try:
        # Admin kontrolü
        admin_key = request.data.get('admin_key')
        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        user_id = data.get('user_id')
        reason = data.get('reason', 'Admin unblock')

        if not user_id:
            return Response(
                {"error": "Kullanıcı ID gereklidir"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kullanıcının block'ını kaldır
        success = RateLimitingService.unblock_user(user_id, reason)

        if success:
            return Response({
                'message': f'Kullanıcı {user_id} block\'ı kaldırıldı',
                'reason': reason,
                'unblocked_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Unblock işlemi başarısız"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error in manual_unblock_user: {e}")
        return Response(
            {"error": "Unblock işlemi başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== ANALYTICS API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_analytics_dashboard(request):
    """Dashboard analitiklerini al"""
    try:
        period = request.GET.get('period', 'week')

        if period not in ['day', 'week', 'month', 'year']:
            period = 'week'

        # Dashboard analitiklerini al
        analytics = AnalyticsService.get_dashboard_analytics(period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_analytics_dashboard: {e}")
        return Response(
            {"error": "Dashboard analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_analytics_user(request):
    """Kullanıcı bazlı analitikleri al"""
    try:
        # Anonim kullanıcıyı al
        anonymous_user, created = AnonymousUserService.get_or_create_anonymous_user(request)

        period = request.GET.get('period', 'month')

        if period not in ['day', 'week', 'month', 'year']:
            period = 'month'

        # Kullanıcı analitiklerini al
        analytics = AnalyticsService.get_user_analytics(anonymous_user, period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_analytics_user: {e}")
        return Response(
            {"error": "Kullanıcı analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_analytics_content(request):
    """İçerik bazlı analitikleri al"""
    try:
        period = request.GET.get('period', 'month')

        if period not in ['day', 'week', 'month', 'year']:
            period = 'month'

        # İçerik analitiklerini al
        analytics = AnalyticsService.get_content_analytics(period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_analytics_content: {e}")
        return Response(
            {"error": "İçerik analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_analytics_engagement(request):
    """Etkileşim analitiklerini al"""
    try:
        period = request.GET.get('period', 'week')

        if period not in ['day', 'week', 'month', 'year']:
            period = 'week'

        # Etkileşim analitiklerini al
        analytics = AnalyticsService.get_engagement_analytics(period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_analytics_engagement: {e}")
        return Response(
            {"error": "Etkileşim analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_analytics_conversion_funnel(request):
    """Conversion funnel analitiklerini al"""
    try:
        period = request.GET.get('period', 'week')

        if period not in ['day', 'week', 'month', 'year']:
            period = 'week'

        # Conversion funnel analitiklerini al
        analytics = AnalyticsService.get_conversion_funnel_analytics(period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_analytics_conversion_funnel: {e}")
        return Response(
            {"error": "Conversion funnel analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== DATABASE OPTIMIZATION API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_database_status(request):
    """Veritabanı durumu ve sağlık metrikleri"""
    try:
        status = DatabaseOptimizationService.get_optimization_status()

        return Response(status, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_database_status: {e}")
        return Response(
            {"error": "Veritabanı durumu alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_database_metrics(request):
    """Detaylı veritabanı metrikleri"""
    try:
        metrics = DatabaseOptimizationService.analyze_performance()

        return Response(metrics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_database_metrics: {e}")
        return Response(
            {"error": "Veritabanı metrikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def run_database_optimization(request):
    """Veritabanı optimizasyonu çalıştır"""
    try:
        # Admin key check for security
        data = request.data
        admin_key = data.get('admin_key', '')

        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Run optimization
        results = DatabaseOptimizationService.run_full_optimization()

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in run_database_optimization: {e}")
        return Response(
            {"error": "Veritabanı optimizasyonu başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def run_cleanup(request):
    """Sadece temizlik işlemlerini çalıştır"""
    try:
        # Admin key check for security
        data = request.data
        admin_key = data.get('admin_key', '')

        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Run cleanup only
        results = DatabaseOptimizationService.perform_cleanup()

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in run_cleanup: {e}")
        return Response(
            {"error": "Temizlik işlemi başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def optimize_indexes(request):
    """İndeks optimizasyonu çalıştır"""
    try:
        # Admin key check for security
        data = request.data
        admin_key = data.get('admin_key', '')

        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Run index optimization
        results = DatabaseOptimizationService.optimize_indexes()

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in optimize_indexes: {e}")
        return Response(
            {"error": "İndeks optimizasyonu başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== A/B TESTING API ====================

@api_view(["GET"])
@permission_classes([AllowAny])
def get_ab_test_config(request):
    """Get A/B test configuration for user"""
    try:
        # Get user identifier (from anonymous user or request)
        user_id = request.GET.get('user_id', 'anonymous')
        test_name = request.GET.get('test_name')

        if not test_name:
            return Response(
                {"error": "Test name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get test configuration
        config = ABTestService.get_test_config(test_name, user_id)

        # Track impression event
        ABTestService.track_test_event(test_name, user_id, 'impression', {
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'timestamp': timezone.now().isoformat()
        })

        return Response(config, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_ab_test_config: {e}")
        return Response(
            {"error": "A/B test configuration alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def track_ab_test_event(request):
    """Track A/B test event"""
    try:
        data = request.data
        test_name = data.get('test_name')
        user_id = data.get('user_id', 'anonymous')
        event_type = data.get('event_type')
        event_data = data.get('event_data', {})

        if not all([test_name, event_type]):
            return Response(
                {"error": "Test name and event type are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add request metadata to event data
        event_data.update({
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'referrer': request.META.get('HTTP_REFERER', ''),
            'timestamp': timezone.now().isoformat()
        })

        # Track event
        success = ABTestService.track_test_event(test_name, user_id, event_type, event_data)

        if success:
            return Response(
                {"message": "Event tracked successfully", "test_name": test_name, "event_type": event_type},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Failed to track event"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error in track_ab_test_event: {e}")
        return Response(
            {"error": "Event tracking failed", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_ab_test_analytics(request):
    """Get A/B test analytics"""
    try:
        test_name = request.GET.get('test_name')
        period = request.GET.get('period', '7d')

        if not test_name:
            return Response(
                {"error": "Test name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get analytics
        analytics = ABTestService.get_test_analytics(test_name, period)

        return Response(analytics, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_ab_test_analytics: {e}")
        return Response(
            {"error": "A/B test analitikleri alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_active_ab_tests(request):
    """Get all active A/B tests"""
    try:
        active_tests = ABTestService.get_all_active_tests()

        return Response({
            'active_tests': active_tests,
            'total_count': len(active_tests)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_active_ab_tests: {e}")
        return Response(
            {"error": "Active A/B tests alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def create_ab_test(request):
    """Create custom A/B test"""
    try:
        # Admin key check for security
        data = request.data
        admin_key = data.get('admin_key', '')

        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        test_name = data.get('test_name')
        test_config = data.get('test_config')

        if not all([test_name, test_config]):
            return Response(
                {"error": "Test name and config are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create test
        success = ABTestService.create_custom_test(test_name, test_config)

        if success:
            return Response({
                "message": f"A/B test '{test_name}' created successfully",
                "test_name": test_name
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"error": "Failed to create A/B test"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except Exception as e:
        logger.error(f"Error in create_ab_test: {e}")
        return Response(
            {"error": "A/B test oluşturulamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def end_ab_test(request):
    """End A/B test"""
    try:
        # Admin key check for security
        data = request.data
        admin_key = data.get('admin_key', '')

        if admin_key != 'admin123':
            return Response(
                {"error": "Yetkisiz erişim"},
                status=status.HTTP_403_FORBIDDEN
            )

        test_name = data.get('test_name')
        implement_winner = data.get('implement_winner', False)

        if not test_name:
            return Response(
                {"error": "Test name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # End test
        result = ABTestService.end_test(test_name, implement_winner)

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in end_ab_test: {e}")
        return Response(
            {"error": "A/B test bitirilemedi", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def get_client_ab_config(request):
    """Get client-side A/B testing configuration"""
    try:
        test_name = request.GET.get('test_name')
        user_identifier = request.GET.get('user_id', 'anonymous')

        if not test_name:
            return Response(
                {"error": "Test name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get client config
        client_config = ABTestService.ClientSideABTesting.get_client_config(test_name, user_identifier)

        return Response(client_config, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in get_client_ab_config: {e}")
        return Response(
            {"error": "Client A/B config alınamadı", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def check_feature_flag(request):
    """Check if feature should be enabled for user"""
    try:
        feature_name = request.GET.get('feature_name')
        user_identifier = request.GET.get('user_id', 'anonymous')

        if not feature_name:
            return Response(
                {"error": "Feature name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check feature flag
        should_show = ABTestService.ClientSideABTesting.should_show_feature(feature_name, user_identifier)

        return Response({
            'feature_name': feature_name,
            'enabled': should_show,
            'user_identifier': user_identifier
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in check_feature_flag: {e}")
        return Response(
            {"error": "Feature flag kontrolü başarısız", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )