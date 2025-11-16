"""
Celery Configuration for OSYM AI
Configures Celery with Redis broker and scheduled tasks
"""

import os
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')

app = Celery('osym_ai')

# Using Redis as broker
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Istanbul',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # Optimizations
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Redis connection pooling
    broker_pool_limit=10,
    result_expires=3600,  # 1 hour
    result_backend_max_retries=10,
    result_backend_base_sleep_interval=0.1,
)

# Discover tasks in all registered Django app configs.
app.autodiscover_tasks()

# Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Database optimization tasks
    'cleanup-expired-sessions': {
        'task': 'quiz.services.database_optimization_service.cleanup_expired_sessions',
        'schedule': crontab(hour='*/6', minute=0),  # Every 6 hours
        'options': {'queue': 'maintenance'},
    },
    'update-statistics': {
        'task': 'quiz.services.database_optimization_service.update_statistics',
        'schedule': crontab(hour='*/12', minute=30),  # Every 12 hours
        'options': {'queue': 'maintenance'},
    },
    'scheduled-optimization': {
        'task': 'quiz.services.database_optimization_service.scheduled_optimization',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Every Monday at 2 AM
        'options': {'queue': 'maintenance'},
    },

    # Analytics cache warming
    'warm-analytics-cache': {
        'task': 'quiz.services.analytics_service.warm_analytics_cache',
        'schedule': crontab(hour='*/4', minute=0),  # Every 4 hours
        'options': {'queue': 'analytics'},
    },

    # Gamification tasks
    'update-streaks': {
        'task': 'quiz.services.gamification_service.update_daily_streaks',
        'schedule': crontab(hour=0, minute=5),  # Daily at 00:05
        'options': {'queue': 'gamification'},
    },
    'calculate-weekly-leaderboard': {
        'task': 'quiz.services.gamification_service.calculate_weekly_leaderboard',
        'schedule': crontab(hour=0, minute=10, day_of_week=0),  # Sunday at 00:10
        'options': {'queue': 'gamification'},
    },
    'reset-daily-challenges': {
        'task': 'quiz.services.gamification_service.reset_daily_challenges',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        'options': {'queue': 'gamification'},
    },

    # Rate limiting cleanup
    'cleanup-rate-limits': {
        'task': 'quiz.services.rate_limiting_service.cleanup_expired_rate_limits',
        'schedule': crontab(hour='*/8', minute=0),  # Every 8 hours
        'options': {'queue': 'maintenance'},
    },

    # Adaptive difficulty recalculations
    'recalculate-difficulty-profiles': {
        'task': 'quiz.services.adaptive_difficulty_service.recalculate_all_difficulty_profiles',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),  # Monday at 1 AM
        'options': {'queue': 'analytics'},
    },

    # Performance monitoring
    'collect-performance-metrics': {
        'task': 'quiz.services.analytics_service.collect_performance_metrics',
        'schedule': crontab(hour='*', minute=0),  # Every hour
        'options': {'queue': 'monitoring'},
    },
}

# Queue configurations
app.conf.task_routes = {
    'quiz.services.database_optimization_service.*': {'queue': 'maintenance'},
    'quiz.services.analytics_service.*': {'queue': 'analytics'},
    'quiz.services.gamification_service.*': {'queue': 'gamification'},
    'quiz.services.rate_limiting_service.*': {'queue': 'maintenance'},
    'quiz.services.adaptive_difficulty_service.*': {'queue': 'analytics'},
    'quiz.services.monitoring_service.*': {'queue': 'monitoring'},
}

# Worker configurations
app.conf.worker_queues = ['default', 'maintenance', 'analytics', 'gamification', 'monitoring']

# Task priority
app.conf.task_annotations = {
    'quiz.services.database_optimization_service.scheduled_optimization': {
        'rate_limit': '1/m',  # Maximum once per minute
        'priority': 5,  # Lower priority for maintenance tasks
    },
    'quiz.services.analytics_service.warm_analytics_cache': {
        'rate_limit': '10/m',
        'priority': 3,
    },
    'quiz.services.gamification_service.update_daily_streaks': {
        'rate_limit': '20/m',
        'priority': 7,  # Higher priority for user-facing features
    },
}

# Error handling
app.conf.task_reject_on_worker_lost = True
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1

# Monitoring
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Security
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.task_serializer = 'json'

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')