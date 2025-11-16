"""
Production-ready Celery Configuration
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')

app = Celery('osym_ai')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Production Celery Settings
app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Task routing
    task_routes={
        'quiz.services.pdf_processor_service.process_pdf_document_task': {
            'queue': 'pdf_processing',
        },
    },

    # Task time limits
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes

    # Result backend
    result_backend=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    result_expires=3600,  # 1 hour

    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Optional: Configure Beat Scheduler for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-processing-logs': {
        'task': 'quiz.tasks.cleanup_processing_logs',
        'schedule': 24 * 60 * 60.0,  # Run daily
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connectivity"""
    print(f'Request: {self.request!r}')


# Health check task
@app.task
def health_check():
    """Health check task for monitoring"""
    return {"status": "healthy", "service": "celery"}