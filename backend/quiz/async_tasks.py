"""
Asynchronous question generation tasks
Sadece performans optimizasyonu için - çalışanı sistem korundu
"""
from celery import shared_task
from django.db import transaction
from django.utils import timezone
import logging

from .models import TempExamSession, TempExamQuestion
from .services.smart_question_selection_simple import simple_selector

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_questions_async(session_uuid, user_identifier='anonymous'):
    """
    Asynchronous soru üretimi
    Sadece soru oluşturma yavaşladığı için - çalışanı sisteme zarar vermez
    """
    try:
        # Task başlangı zamanını kaydet
        task_start = timezone.now()
        logger.info(f"Async question generation started for session {session_uuid}")

        # Session'ı bul
        try:
            session = TempExamSession.objects.get(uuid=session_uuid)
        except TempExamSession.DoesNotExist:
            logger.error(f"Session not found: {session_uuid}")
            return {"error": "Session not found", "status": "failed"}

        # Session status'ını güncelle
        session.status = "preparing"
        session.save()

        # Soru seçimi (quick service kullanarak)
        try:
            # Simple selector'ı kullan - daha hızlı
            selected_questions = simple_selector.get_questions_for_user(
                session=session,
                user_identifier=user_identifier
            )

            if not selected_questions:
                logger.error(f"No questions selected for session {session_uuid}")
                session.status = "failed"
                session.save()
                return {"error": "No questions available", "status": "failed"}

            # İlerlemeyi güncelle (%25)
            session.status = "preparing"
            session.temp_data = {
                "progress": 25,
                "total_questions": len(selected_questions),
                "message": "Sorular seçiliyor..."
            }
            session.save()

            # TempExamQuestion'ları oluştur
            questions_created = []
            from .services.quick_test_service import generate_quick_test_questions

            with transaction.atomic():
                temp_questions = generate_quick_test_questions(session, user_identifier)
                questions_created = [
                    {
                        'id': tq.id,
                        'subject': tq.subject,
                        'topic': tq.topic,
                        'order': tq.order
                    } for tq in temp_questions
                ]

            # İlerlemeyi güncelle (%75)
            session.status = "preparing"
            session.temp_data = {
                "progress": 75,
                "total_questions": len(questions_created),
                "message": "Sorular hazırlanıyor...",
                "questions_created": questions_created
            }
            session.save()

            # Son durum
            session.status = "ready"
            session.temp_data = {
                "progress": 100,
                "total_questions": len(questions_created),
                "message": "Sınav hazır!",
                "questions_created": questions_created,
                "completed_at": timezone.now().isoformat(),
                "duration_seconds": (timezone.now() - task_start).total_seconds()
            }
            session.save()

            logger.info(f"Async question generation completed for session {session_uuid}")

            return {
                "status": "completed",
                "session_uuid": str(session_uuid),
                "questions_count": len(questions_created),
                "duration_seconds": (timezone.now() - task_start).total_seconds()
            }

        except Exception as e:
            logger.error(f"Error in async question generation: {e}")
            session.status = "failed"
            session.save()
            return {"error": str(e), "status": "failed"}

    except Exception as e:
        logger.error(f"Critical error in async task: {e}")
        return {"error": f"Critical error: {e}", "status": "failed"}


@shared_task
def update_session_progress(session_uuid, progress, message):
    """
    Session ilerlemesini güncelle
    """
    try:
        session = TempExamSession.objects.get(uuid=session_uuid)
        if session.status in ["preparing", "loading"]:
            session.temp_data = session.temp_data or {}
            session.temp_data.update({
                "progress": progress,
                "message": message,
                "updated_at": timezone.now().isoformat()
            })
            session.save()
    except Exception as e:
        logger.error(f"Error updating progress: {e}")


@shared_task
def cleanup_old_sessions():
    """Eski session'ları temizle - sadece optimizasyon için"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(hours=24)
        old_sessions = TempExamSession.objects.filter(
            created_at__lt=cutoff_date,
            status__in=["preparing", "failed"]
        )
        deleted_count = old_sessions.count()
        old_sessions.delete()
        logger.info(f"Cleaned up {deleted_count} old sessions")
        return {"deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {"error": str(e)}


# Status kontrol için helper function (task değil, normal function)
def get_session_status(session_uuid):
    """
    Session durumunu getir
    """
    try:
        session = TempExamSession.objects.get(uuid=session_uuid)

        return {
            "uuid": str(session.uuid),
            "status": session.status,
            "progress": session.temp_data.get('progress', 0) if session.temp_data else 0,
            "message": session.temp_data.get('message', 'Hazırlanıyor...') if session.temp_data else 'Hazırlanıyor...',
            "total_questions": session.question_count,
            "completed_at": session.temp_data.get('completed_at') if session.temp_data else None,
            "duration_seconds": session.temp_data.get('duration_seconds', 0) if session.temp_data else 0,
            "questions_count": session.temp_data.get('questions_count', 0) if session.temp_data else 0
        }
    except TempExamSession.DoesNotExist:
        return {"error": "Session not found", "status": "not_found"}
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return {"error": str(e), "status": "error"}