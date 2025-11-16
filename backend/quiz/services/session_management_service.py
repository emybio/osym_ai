import logging
from django.utils import timezone
from django.core.management.base import BaseCommand
from datetime import timedelta

from quiz.models import TempExamSession, TempExamResult, AnonymousUser

logger = logging.getLogger(__name__)


class SessionManagementService:
    """Oturum yönetim ve temizleme servisi"""

    # Oturum durumları
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'
    STATUS_EXPIRED = 'expired'

    # Temizleme zamanları
    ABANDONED_AFTER_HOURS = 2  # 2 saat sonra terk edilmiş sayılır
    EXPIRED_AFTER_DAYS = 7    # 7 gün sonra süresi dolmuş sayılır
    INACTIVE_USER_DAYS = 90   # 90 gün inaktif kullanıcıları sil

    @classmethod
    def get_session_statistics(cls):
        """
        Oturum istatistiklerini döndür
        """
        now = timezone.now()

        # Tüm oturumlar
        total_sessions = TempExamSession.objects.count()

        # Durumlara göre
        active_sessions = TempExamSession.objects.filter(status=cls.STATUS_ACTIVE).count()
        completed_sessions = TempExamSession.objects.filter(status=cls.STATUS_COMPLETED).count()
        abandoned_sessions = TempExamSession.objects.filter(status=cls.STATUS_ABANDONED).count()
        expired_sessions = TempExamSession.objects.filter(status=cls.STATUS_EXPIRED).count()

        # Zaman bazlı
        today = now.date()
        today_sessions = TempExamSession.objects.filter(created_at__date=today).count()
        week_ago = now - timedelta(days=7)
        week_sessions = TempExamSession.objects.filter(created_at__gte=week_ago).count()
        month_ago = now - timedelta(days=30)
        month_sessions = TempExamSession.objects.filter(created_at__gte=month_ago).count()

        # Tamamlanma oranları
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        abandonment_rate = (abandoned_sessions / total_sessions * 100) if total_sessions > 0 else 0

        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'completed_sessions': completed_sessions,
            'abandoned_sessions': abandoned_sessions,
            'expired_sessions': expired_sessions,
            'today_sessions': today_sessions,
            'week_sessions': week_sessions,
            'month_sessions': month_sessions,
            'completion_rate': round(completion_rate, 1),
            'abandonment_rate': round(abandonment_rate, 1),
            'last_cleanup': cls.get_last_cleanup_time()
        }

    @classmethod
    def cleanup_abandoned_sessions(cls):
        """
        Terk edilmiş oturumları temizle
        """
        cutoff_time = timezone.now() - timedelta(hours=cls.ABANDONED_AFTER_HOURS)

        # Aktif ama süresi geçmiş oturumları bul
        abandoned_sessions = TempExamSession.objects.filter(
            status=cls.STATUS_ACTIVE,
            created_at__lt=cutoff_time
        )

        # Terk edilmiş olarak işaretle
        abandoned_count = abandoned_sessions.update(status=cls.STATUS_ABANDONED)

        logger.info(f"{abandoned_count} adet terk edilmiş oturum temizlendi")
        return abandoned_count

    @classmethod
    def cleanup_expired_sessions(cls):
        """
        Süresi dolmuş oturumları temizle
        """
        cutoff_time = timezone.now() - timedelta(days=cls.EXPIRED_AFTER_DAYS)

        # Eski tamamlanmamış oturumları sil
        expired_sessions = TempExamSession.objects.filter(
            created_at__lt=cutoff_time,
            status__in=[cls.STATUS_ACTIVE, cls.STATUS_ABANDONED]
        )

        # İlişkili TempExamQuestion'ları da sil (cascade delete)
        expired_count = expired_sessions.count()

        if expired_count > 0:
            expired_sessions.delete()
            logger.info(f"{expired_count} adet süresi dolmuş oturum silindi")

        return expired_count

    @classmethod
    def cleanup_inactive_users(cls):
        """
        Inaktif kullanıcıları temizle
        """
        cutoff_time = timezone.now() - timedelta(days=cls.INACTIVE_USER_DAYS)

        # Hiç test çözmeyen ve çok eski kullanıcıları sil
        inactive_users = AnonymousUser.objects.filter(
            last_seen__lt=cutoff_time,
            total_test_count=0
        )

        # İlişkili verileri temizle
        deleted_count = inactive_users.count()

        if deleted_count > 0:
            # Önce ilişkili verileri sil
            user_ids = list(inactive_users.values_list('id', flat=True))

            # TempExamResult ve TempExamSession ilişkili kullanıcıları güncelle
            # TODO: Fix when anonymous_user field is properly added to models
            # TempExamResult.objects.filter(anonymous_user_id__in=user_ids).update(anonymous_user=None)
            # TempExamSession.objects.filter(anonymous_user_id__in=user_ids).update(anonymous_user=None)

            # Sonra kullanıcıları sil
            inactive_users.delete()
            logger.info(f"{deleted_count} adet inaktif kullanıcı silindi")

        return deleted_count

    @classmethod
    def run_full_cleanup(cls):
        """
        Tam temizleme çalıştır
        """
        results = {
            'abandoned_sessions': cls.cleanup_abandoned_sessions(),
            'expired_sessions': cls.cleanup_expired_sessions(),
            'inactive_users': cls.cleanup_inactive_users(),
            'timestamp': timezone.now().isoformat()
        }

        # Son temizleme zamanını kaydet
        cls._save_cleanup_time()

        return results

    @classmethod
    def get_last_cleanup_time(cls):
        """Son temizleme zamanını döndür"""
        from django.core.cache import cache
        return cache.get('last_cleanup_time')

    @classmethod
    def _save_cleanup_time(cls):
        """Son temizleme zamanını kaydet"""
        from django.core.cache import cache
        cache.set('last_cleanup_time', timezone.now().isoformat(), timeout=86400)  # 1 gün

    @classmethod
    def cleanup_orphaned_results(cls):
        """
        Sahibi olmayan sonuçları temizle
        """
        # Session'ı olmayan TempExamResult'ları bul
        orphaned_results = TempExamResult.objects.filter(
            session_id__isnull=True
        )

        deleted_count = orphaned_results.count()
        orphaned_results.delete()

        logger.info(f"{deleted_count} adet sahipsiz sonuç temizlendi")
        return deleted_count

    @classmethod
    def optimize_database(cls):
        """
        Veritabanı optimizasyonu
        """
        # VACUUM ve ANALYZE işlemleri (PostgreSQL için)
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                # Dead rows temizle
                cursor.execute("VACUUM ANALYZE quiz_tempexamsession;")
                cursor.execute("VACUUM ANALYZE quiz_tempexamresult;")
                cursor.execute("VACUUM ANALYZE quiz_anonymoususer;")
                cursor.execute("VACUUM ANALYZE quiz_anonymousstats;")

                # Index'leri yeniden oluştur
                cursor.execute("REINDEX INDEX idx_browser_id;")
                cursor.execute("REINDEX INDEX idx_user_exam_branch;")
                cursor.execute("REINDEX INDEX idx_last_seen;")
                cursor.execute("REINDEX INDEX idx_last_test_date;")

                logger.info("Veritabanı optimizasyonu tamamlandı")
                return True

            except Exception as e:
                logger.error(f"Veritabanı optimizasyonu hatası: {e}")
                return False

    @classmethod
    def get_session_health_report(cls):
        """
        Oturum sağlığı raporu
        """
        stats = cls.get_session_statistics()

        # Sağlık kontrolü
        health_issues = []

        # Yüksek abandon oranı
        if stats['abandonment_rate'] > 50:
            health_issues.append(f"Yüksek abandon oranı: %{stats['abandonment_rate']}")

        # Çok sayıda aktif oturum
        if stats['active_sessions'] > 100:
            health_issues.append(f"Fazla aktif oturum: {stats['active_sessions']}")

        # Tamamlanma oranı düşük
        if stats['completion_rate'] < 30:
            health_issues.append(f"Düşük tamamlanma oranı: %{stats['completion_rate']}")

        return {
            'health_status': 'HEALTHY' if not health_issues else 'WARNING',
            'statistics': stats,
            'health_issues': health_issues,
            'recommendations': cls._get_health_recommendations(stats, health_issues)
        }

    @classmethod
    def _get_health_recommendations(cls, stats, issues):
        """
        Sağlık önerileri
        """
        recommendations = []

        if stats['abandonment_rate'] > 50:
            recommendations.append("Oturum sürelerini kısaltın veya reminder'ler ekleyin")

        if stats['active_sessions'] > 100:
            recommendations.append("Daha sık temizleme çalıştırın")

        if stats['completion_rate'] < 30:
            recommendations.append("Soru kalitesini kontrol edin veya test süresini uzatın")

        if 'Süresi dolmuş oturumlar' in [issue for issue in issues]:
            recommendations.append("Otomatik temizleme sıklığını artırın")

        return recommendations