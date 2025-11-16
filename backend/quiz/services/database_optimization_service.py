"""
Database Optimization Service
Advanced database optimization with automated cleanup, performance monitoring, and maintenance.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from django.db import connection, transaction
from django.db.models import Count, Avg, StdDev, Variance, F, Q
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from django.core.cache import cache

from ..models import (
    TempExamSession, TempExamResult, TempExamQuestion,
    AnonymousUser, AnonymousStats, Question,
    PDFProcessingLog, StudentResult, ExamResult
)

logger = logging.getLogger(__name__)


class DatabaseOptimizationService:
    """Advanced database optimization service"""

    # Optimization settings
    CLEANUP_THRESHOLDS = {
        'session_cleanup_days': 7,
        'result_cleanup_days': 30,
        'log_cleanup_days': 90,
        'analytics_retention_days': 180,
        'max_temp_sessions_per_ip': 50,
        'max_anonymous_users_per_ip': 100
    }

    PERFORMANCE_THRESHOLDS = {
        'slow_query_ms': 1000,
        'high_memory_usage_mb': 500,
        'high_disk_usage_percent': 80,
        'large_table_size_mb': 1000
    }

    @classmethod
    def run_full_optimization(cls) -> Dict[str, Any]:
        """
        Run complete database optimization suite
        """
        start_time = timezone.now()
        results = {
            'start_time': start_time.isoformat(),
            'operations': [],
            'performance_metrics': {},
            'errors': []
        }

        try:
            # 1. Performance Analysis
            perf_analysis = cls.analyze_performance()
            results['performance_metrics'] = perf_analysis
            results['operations'].append('performance_analysis_completed')

            # 2. Cleanup Operations
            cleanup_results = cls.perform_cleanup()
            results['cleanup_results'] = cleanup_results
            results['operations'].append('cleanup_completed')

            # 3. Index Optimization
            index_results = cls.optimize_indexes()
            results['index_results'] = index_results
            results['operations'].append('index_optimization_completed')

            # 4. Data Archiving
            archive_results = cls.archive_old_data()
            results['archive_results'] = archive_results
            results['operations'].append('data_archiving_completed')

            # 5. Statistics Update
            stats_results = cls.update_table_statistics()
            results['stats_results'] = stats_results
            results['operations'].append('statistics_updated')

            # 6. Cache Warming
            cache_results = cls.warm_cache()
            results['cache_results'] = cache_results
            results['operations'].append('cache_warmed')

        except Exception as e:
            error_msg = f"Optimization failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        finally:
            end_time = timezone.now()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = (end_time - start_time).total_seconds()

        return results

    @classmethod
    def analyze_performance(cls) -> Dict[str, Any]:
        """Analyze database performance and identify bottlenecks"""
        metrics = {}

        try:
            with connection.cursor() as cursor:
                # Get table sizes
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)

                table_sizes = {}
                for row in cursor.fetchall():
                    table_sizes[row[1]] = {
                        'schema': row[0],
                        'size_pretty': row[2],
                        'size_bytes': row[3],
                        'size_mb': row[3] / (1024 * 1024)
                    }

                metrics['table_sizes'] = table_sizes

                # Get slow queries (PostgreSQL specific)
                cursor.execute("""
                    SELECT query, calls, total_time, mean_time, rows
                    FROM pg_stat_statements
                    WHERE mean_time > %s
                    ORDER BY mean_time DESC
                    LIMIT 10
                """, [cls.PERFORMANCE_THRESHOLDS['slow_query_ms']])

                slow_queries = []
                for row in cursor.fetchall():
                    slow_queries.append({
                        'query': row[0][:200] + '...' if len(row[0]) > 200 else row[0],
                        'calls': row[1],
                        'total_time_ms': row[2],
                        'mean_time_ms': row[3],
                        'rows': row[4]
                    })

                metrics['slow_queries'] = slow_queries

                # Get database connections
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                metrics['active_connections'] = cursor.fetchone()[0]

                # Get index usage
                cursor.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes
                    ORDER BY idx_scan ASC
                """)

                unused_indexes = []
                for row in cursor.fetchall():
                    if row[3] == 0:  # idx_scan = 0 (never used)
                        unused_indexes.append({
                            'schema': row[0],
                            'table': row[1],
                            'index': row[2]
                        })

                metrics['unused_indexes'] = unused_indexes

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            metrics['error'] = str(e)

        return metrics

    @classmethod
    def perform_cleanup(cls) -> Dict[str, Any]:
        """Perform database cleanup operations"""
        results = {
            'cleaned_records': {},
            'errors': []
        }

        try:
            # 1. Clean expired temporary sessions
            expired_sessions = cls._cleanup_expired_sessions()
            results['cleaned_records']['temp_exam_sessions'] = expired_sessions

            # 2. Clean orphaned temp exam questions
            orphaned_questions = cls._cleanup_orphaned_questions()
            results['cleaned_records']['orphaned_questions'] = orphaned_questions

            # 3. Clean old anonymous users
            old_users = cls._cleanup_old_anonymous_users()
            results['cleaned_records']['old_anonymous_users'] = old_users

            # 4. Clean old processing logs
            old_logs = cls._cleanup_old_logs()
            results['cleaned_records']['processing_logs'] = old_logs

            # 5. Clean duplicate anonymous users
            duplicate_users = cls._cleanup_duplicate_users()
            results['cleaned_records']['duplicate_users'] = duplicate_users

            # 6. VACUUM and ANALYZE
            cls._run_vacuum_analyze()

        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    @classmethod
    def optimize_indexes(cls) -> Dict[str, Any]:
        """Optimize database indexes"""
        results = {
            'indexes_created': [],
            'indexes_dropped': [],
            'reindexed_tables': [],
            'errors': []
        }

        try:
            with connection.cursor() as cursor:
                # Create missing indexes for performance
                indexes_to_create = [
                    ("idx_temp_exam_session_browser_ip", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_temp_exam_session_browser_ip ON quiz_tempexamsession(browser_id, ip_address)"),
                    ("idx_temp_exam_session_created_at", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_temp_exam_session_created_at ON quiz_tempexamsession(created_at)"),
                    ("idx_anonymous_user_last_seen", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_anonymous_user_last_seen ON quiz_anonymoususer(last_seen)"),
                    ("idx_anonymous_stats_anonymous_user", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_anonymous_stats_anonymous_user ON quiz_anonymousstats(anonymous_user_id)"),
                    ("idx_temp_exam_question_session", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_temp_exam_question_session ON quiz_tempexamquestion(session_id)"),
                    ("idx_pdf_processing_log_created_at", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pdf_processing_log_created_at ON quiz_pdfprocessinglog(created_at)"),
                    ("idx_student_result_student", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_student_result_student ON quiz_studentresult(student_id)"),
                ]

                for index_name, sql in indexes_to_create:
                    try:
                        cursor.execute(sql)
                        results['indexes_created'].append(index_name)
                        logger.info(f"Created index: {index_name}")
                    except Exception as e:
                        # Index might already exist, which is fine
                        logger.debug(f"Index {index_name} already exists or creation failed: {e}")

                # Reindex large tables
                large_tables = ['quiz_tempexamresult', 'quiz_anonymousstats', 'quiz_studentresult']

                for table in large_tables:
                    try:
                        cursor.execute(f"REINDEX INDEX CONCURRENTLY ON {table}")
                        results['reindexed_tables'].append(table)
                        logger.info(f"Reindexed table: {table}")
                    except Exception as e:
                        logger.warning(f"Could not reindex table {table}: {e}")

        except Exception as e:
            error_msg = f"Index optimization failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    @classmethod
    def archive_old_data(cls) -> Dict[str, Any]:
        """Archive old data to improve performance"""
        results = {
            'archived_records': {},
            'errors': []
        }

        try:
            # Archive old temp exam results (keep only recent ones)
            cutoff_date = timezone.now() - timedelta(days=cls.CLEANUP_THRESHOLDS['result_cleanup_days'])

            # Archive to archive table or just delete old records
            with connection.cursor() as cursor:
                # Create archive table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_tempexamresult_archive AS
                    SELECT * FROM quiz_tempexamresult WHERE 1=0
                """)

                # Move old records to archive
                cursor.execute("""
                    INSERT INTO quiz_tempexamresult_archive
                    SELECT * FROM quiz_tempexamresult
                    WHERE created_at < %s
                    ON CONFLICT DO NOTHING
                """, [cutoff_date])

                # Delete old records from main table
                deleted_count = cursor.execute("""
                    DELETE FROM quiz_tempexamresult
                    WHERE created_at < %s
                """, [cutoff_date])

                results['archived_records']['temp_exam_results'] = deleted_count

            # Archive old PDF processing logs
            log_cutoff = timezone.now() - timedelta(days=cls.CLEANUP_THRESHOLDS['log_cleanup_days'])

            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_pdfprocessinglog_archive AS
                    SELECT * FROM quiz_pdfprocessinglog WHERE 1=0
                """)

                cursor.execute("""
                    INSERT INTO quiz_pdfprocessinglog_archive
                    SELECT * FROM quiz_pdfprocessinglog
                    WHERE created_at < %s
                    ON CONFLICT DO NOTHING
                """, [log_cutoff])

                deleted_logs = cursor.execute("""
                    DELETE FROM quiz_pdfprocessinglog
                    WHERE created_at < %s
                """, [log_cutoff])

                results['archived_records']['processing_logs'] = deleted_logs

        except Exception as e:
            error_msg = f"Data archiving failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    @classmethod
    def update_table_statistics(cls) -> Dict[str, Any]:
        """Update table statistics for query optimizer"""
        results = {
            'updated_tables': [],
            'errors': []
        }

        try:
            with connection.cursor() as cursor:
                # Get all tables in the quiz app
                cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public' AND tablename LIKE 'quiz_%'
                """)

                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    try:
                        cursor.execute(f"ANALYZE {table}")
                        results['updated_tables'].append(table)
                        logger.info(f"Updated statistics for table: {table}")
                    except Exception as e:
                        logger.warning(f"Could not analyze table {table}: {e}")

        except Exception as e:
            error_msg = f"Statistics update failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    @classmethod
    def warm_cache(cls) -> Dict[str, Any]:
        """Warm up frequently accessed cache keys"""
        results = {
            'warmed_keys': [],
            'errors': []
        }

        try:
            # Warm popular queries
            warm_queries = [
                ('popular_subjects', 'SELECT subject_id, COUNT(*) as count FROM quiz_tempexamquestion GROUP BY subject_id ORDER BY count DESC LIMIT 5'),
                ('daily_stats', 'SELECT DATE(created_at) as date, COUNT(*) as count FROM quiz_tempexamresult WHERE created_at >= NOW() - INTERVAL \'24 hours\' GROUP BY DATE(created_at)'),
                ('active_users', 'SELECT COUNT(*) as count FROM quiz_anonymoususer WHERE last_seen >= NOW() - INTERVAL \'1 hour\''),
            ]

            for key, query in warm_queries:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(query)
                        results['warmed_keys'].append(key)

                        # Cache result for 5 minutes
                        cache.set(f'db_opt_{key}', cursor.fetchall(), timeout=300)

                except Exception as e:
                    logger.warning(f"Could not warm cache key {key}: {e}")

        except Exception as e:
            error_msg = f"Cache warming failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    # Helper methods
    @classmethod
    def _cleanup_expired_sessions(cls) -> int:
        """Clean expired temporary sessions"""
        cutoff = timezone.now() - timedelta(hours=24)
        return TempExamSession.objects.filter(
            created_at__lt=cutoff,
            status='active'
        ).update(status='expired')

    @classmethod
    def _cleanup_orphaned_questions(cls) -> int:
        """Clean orphaned temporary exam questions"""
        return TempExamQuestion.objects.filter(
            ~Q(session_id__in=TempExamSession.objects.values('id'))
        ).delete()[0]

    @classmethod
    def _cleanup_old_anonymous_users(cls) -> int:
        """Clean old inactive anonymous users"""
        cutoff = timezone.now() - timedelta(days=30)
        return AnonymousUser.objects.filter(
            last_seen__lt=cutoff,
            is_active=False
        ).delete()[0]

    @classmethod
    def _cleanup_old_logs(cls) -> int:
        """Clean old processing logs"""
        cutoff = timezone.now() - timedelta(days=cls.CLEANUP_THRESHOLDS['log_cleanup_days'])
        return PDFProcessingLog.objects.filter(
            created_at__lt=cutoff
        ).delete()[0]

    @classmethod
    def _cleanup_duplicate_users(cls) -> int:
        """Clean duplicate anonymous users (same browser_id and IP)"""
        duplicates = AnonymousUser.objects.values(
            'browser_id', 'ip_address'
        ).annotate(
            count=Count('id')
        ).filter(
            count__gt=1
        )

        deleted_count = 0
        for duplicate in duplicates:
            # Keep the most recent, delete others
            users_to_delete = AnonymousUser.objects.filter(
                browser_id=duplicate['browser_id'],
                ip_address=duplicate['ip_address']
            ).order_by('-last_seen')[1:]  # Keep first (most recent)

            deleted_count += users_to_delete.count()
            users_to_delete.delete()

        return deleted_count

    @classmethod
    def _run_vacuum_analyze(cls):
        """Run VACUUM and ANALYZE on critical tables"""
        critical_tables = [
            'quiz_tempexamresult',
            'quiz_anonymoususer',
            'quiz_anonymousstats',
            'quiz_tempexamquestion',
            'quiz_studentresult'
        ]

        with connection.cursor() as cursor:
            for table in critical_tables:
                try:
                    # Use VACUUM ANALYZE for better optimization
                    cursor.execute(f"VACUUM ANALYZE {table}")
                    logger.info(f"VACUUM ANALYZE completed for {table}")
                except Exception as e:
                    logger.warning(f"Could not VACUUM ANALYZE {table}: {e}")

    @classmethod
    def get_optimization_status(cls) -> Dict[str, Any]:
        """Get current optimization status and recommendations"""
        status = {
            'last_optimization': None,
            'recommendations': [],
            'health_score': 0,
            'metrics': {}
        }

        try:
            # Get last optimization time from cache
            last_optimization = cache.get('last_db_optimization')
            if last_optimization:
                status['last_optimization'] = last_optimization

            # Get basic health metrics
            with connection.cursor() as cursor:
                # Database size
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                status['metrics']['database_size'] = cursor.fetchone()[0]

                # Connection count
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                status['metrics']['active_connections'] = cursor.fetchone()[0]

                # Table counts
                status['metrics']['temp_sessions'] = TempExamSession.objects.count()
                status['metrics']['temp_results'] = TempExamResult.objects.count()
                status['metrics']['anonymous_users'] = AnonymousUser.objects.count()

            # Calculate health score (0-100)
            health_score = 100

            # Deduct points for various issues
            if status['metrics']['active_connections'] > 50:
                health_score -= 10

            if status['metrics']['temp_sessions'] > 10000:
                health_score -= 15

            if status['metrics']['anonymous_users'] > 50000:
                health_score -= 10

            status['health_score'] = max(0, health_score)

            # Generate recommendations
            if status['health_score'] < 70:
                status['recommendations'].append('Database optimization recommended')

            if not last_optimization or (timezone.now() - last_optimization).days > 7:
                status['recommendations'].append('Run full optimization')

            if status['metrics']['temp_sessions'] > 5000:
                status['recommendations'].append('Consider archiving old session data')

        except Exception as e:
            logger.error(f"Error getting optimization status: {e}")
            status['error'] = str(e)

        return status


# Celery tasks for scheduled optimization
@shared_task
def scheduled_optimization():
    """Scheduled database optimization task"""
    logger.info("Starting scheduled database optimization")

    try:
        results = DatabaseOptimizationService.run_full_optimization()

        # Cache last optimization time
        cache.set('last_db_optimization', timezone.now(), timeout=86400 * 7)

        logger.info(f"Scheduled optimization completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Scheduled optimization failed: {e}")
        raise


@shared_task
def cleanup_expired_sessions():
    """Periodic cleanup of expired sessions"""
    try:
        count = DatabaseOptimizationService._cleanup_expired_sessions()
        logger.info(f"Cleaned {count} expired sessions")
        return {'cleaned_sessions': count}
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise


@shared_task
def update_statistics():
    """Periodic statistics update"""
    try:
        results = DatabaseOptimizationService.update_table_statistics()
        logger.info(f"Updated statistics for {len(results['updated_tables'])} tables")
        return results
    except Exception as e:
        logger.error(f"Statistics update failed: {e}")
        raise