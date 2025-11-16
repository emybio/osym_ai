import hashlib
import secrets
from django.utils import timezone
from django.http import HttpRequest
from quiz.models import AnonymousUser, AnonymousStats


class AnonymousUserService:
    """Anonim kullanıcı yönetim servisi"""

    COOKIE_NAME = "anonymous_user_id"
    COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 yıl
    BROWSER_ID_LENGTH = 32

    @classmethod
    def get_or_create_anonymous_user(cls, request: HttpRequest) -> tuple[AnonymousUser, bool]:
        """
        İstekten anonim kullanıcı al veya oluştur
        Returns: (anonymous_user, created)
        """
        # 1. Cookie'den browser_id'yi al
        browser_id = cls._get_browser_id_from_cookie(request)

        # 2. IP adresini al
        ip_address = cls._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # 3. Mevcut kullanıcıyı bul
        if browser_id:
            try:
                anonymous_user = AnonymousUser.objects.get(browser_id=browser_id)

                # IP değişirse güncelle (dilersen)
                if anonymous_user.ip_address != ip_address:
                    anonymous_user.ip_address = ip_address
                    anonymous_user.save()

                return anonymous_user, False
            except AnonymousUser.DoesNotExist:
                pass

        # 4. Yeni kullanıcı oluştur
        browser_id = browser_id or cls._generate_browser_id()

        anonymous_user = AnonymousUser.objects.create(
            browser_id=browser_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return anonymous_user, True

    @classmethod
    def get_anonymous_user(cls, request: HttpRequest) -> AnonymousUser | None:
        """Sadece mevcut anonim kullanıcıyı al"""
        browser_id = cls._get_browser_id_from_cookie(request)
        if not browser_id:
            return None

        try:
            return AnonymousUser.objects.get(browser_id=browser_id)
        except AnonymousUser.DoesNotExist:
            return None

    @classmethod
    def can_take_test(cls, anonymous_user: AnonymousUser) -> tuple[bool, str]:
        """
        Kullanıcının test çözebilip çözemeyeceğini kontrol et
        Returns: (can_take, message)
        """
        return anonymous_user.can_take_test()

    @classmethod
    def block_user(cls, anonymous_user: AnonymousUser, hours: int = 1, reason: str = "Suspicious activity"):
        """
        Kullanıcıyı block'la
        """
        blocked_until = timezone.now() + timezone.timedelta(hours=hours)
        anonymous_user.blocked_until = blocked_until
        anonymous_user.block_reason = reason
        anonymous_user.save()

    @classmethod
    def get_user_stats(cls, anonymous_user: AnonymousUser, exam_type: str, branch: str) -> AnonymousStats:
        """
        Kullanıcının istatistiklerini al veya oluştur
        """
        stats, created = AnonymousStats.objects.get_or_create(
            anonymous_user=anonymous_user,
            exam_type=exam_type,
            branch=branch
        )

        return stats

    @classmethod
    def update_user_activity(cls, anonymous_user: AnonymousUser):
        """
        Kullanıcının aktivitesini güncelle
        """
        anonymous_user.last_seen = timezone.now()
        anonymous_user.save(update_fields=['last_seen'])

    @classmethod
    def cleanup_inactive_users(cls, days: int = 90):
        """
        Inaktiv kullanıcıları temizle
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = AnonymousUser.objects.filter(
            last_seen__lt=cutoff_date,
            total_test_count=0  # Hiç test çözmemiş olanlar
        ).delete()
        return deleted_count

    @staticmethod
    def _get_browser_id_from_cookie(request: HttpRequest) -> str | None:
        """Cookie'den browser_id'yi al"""
        return request.COOKIES.get(AnonymousUserService.COOKIE_NAME)

    @staticmethod
    def _generate_browser_id() -> str:
        """Yeni browser_id oluştur"""
        return secrets.token_urlsafe(AnonymousUserService.BROWSER_ID_LENGTH)

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Client IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def generate_browser_hash(user_agent: str, ip: str) -> str:
        """
        Browser bilgilerinden güvenlik hash'i oluştur
        Bu, cookie theft'ini tespit etmek için kullanılabilir
        """
        combined = f"{user_agent}{ip}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @classmethod
    def verify_user_integrity(cls, request: HttpRequest, anonymous_user: AnonymousUser) -> bool:
        """
        Kullanıcının bütünlüğünü kontrol et
        Farklı IP'den cookie kullanımı gibi durumları tespit et
        """
        current_ip = cls._get_client_ip(request)
        current_agent = request.META.get('HTTP_USER_AGENT', '')

        # IP değişikliği kontrolü (farklı şehir/kullanıcı olabilir ama şüpheli)
        if anonymous_user.ip_address != current_ip:
            # İlk IP kaydet
            if not hasattr(anonymous_user, '_previous_ips'):
                anonymous_user._previous_ips = []

            if current_ip not in anonymous_user._previous_ips:
                anonymous_user._previous_ips.append(current_ip)

                # 3+ farklı IP şüpheli
                if len(anonymous_user._previous_ips) >= 3:
                    return False

        return True

    @classmethod
    def get_user_dashboard_data(cls, anonymous_user: AnonymousUser):
        """
        Dashboard için kullanıcı verileri
        """
        # Tüm istatistikleri al
        all_stats = AnonymousStats.objects.filter(anonymous_user=anonymous_user)

        # Genel özet
        total_tests = sum(s.total_tests for s in all_stats)
        total_questions = sum(s.total_questions for s in all_stats)
        total_correct = sum(s.total_correct for s in all_stats)

        overall_avg = (total_correct / total_questions * 100) if total_questions > 0 else 0

        # En iyi skor
        best_score = max((s.best_score for s in all_stats), default=0)

        # Son test tarihi
        last_test_date = max(
            (s.last_test_date for s in all_stats if s.last_test_date),
            default=None
        )

        # En aktif branş
        most_active_stats = max(all_stats, key=lambda s: s.total_tests, default=None)

        # Zayıf konular
        weak_subjects = []
        for stats in all_stats:
            for subject, data in stats.subject_mastery.items():
                mastery = data.get('mastery', 1.0)
                if mastery < 0.7:  # %70 altı
                    weak_subjects.append(f"{subject} ({mastery:.0%})")

        return {
            'total_tests': total_tests,
            'total_questions': total_questions,
            'total_correct': total_correct,
            'overall_average': round(overall_avg, 1),
            'best_score': round(best_score, 1),
            'last_test_date': last_test_date,
            'most_active_exam_branch': (
                f"{most_active_stats.exam_type}/{most_active_stats.branch}"
                if most_active_stats else None
            ),
            'weak_subjects': weak_subjects[:3],  # En çok 3 tane
            'can_take_test': cls.can_take_test(anonymous_user),
            'daily_tests_remaining': max(0, 5 - anonymous_user.daily_test_count),
            'weekly_tests_remaining': max(0, 20 - anonymous_user.weekly_test_count),
        }