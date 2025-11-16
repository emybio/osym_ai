import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.cache import cache
from django.db.models import Count, Avg, Max
from decimal import Decimal

from quiz.models import AnonymousUser, AnonymousStats, TempExamSession, TempExamResult

logger = logging.getLogger(__name__)


class GamificationService:
    """Oyunlaştırma ve motivasyon servisi"""

    # Cache süreleri
    CACHE_TIMEOUT_SHORT = 300    # 5 dakika
    CACHE_TIMEOUT_MEDIUM = 1800  # 30 dakika

    # Başarı tipleri
    ACHIEVEMENT_TYPES = {
        'first_test': 'İlk Test',
        'streak_3': '3 Test Serisi',
        'streak_7': '7 Test Serisi',
        'streak_14': '14 Test Serisi',
        'streak_30': '30 Test Serisi',
        'perfect_score': 'Mükemmel Skor',
        'score_90_plus': '90+ Skor',
        'score_80_plus': '80+ Skor',
        'improvement_streak': 'İyileşme Serisi',
        'topic_master': 'Konu Ustası',
        'speed_demon': 'Hız Canavarı',
        'persistent': 'Israrcı',
        'weekend_warrior': 'Hafta Savaşçısı',
        'early_bird': 'Erken Kuş',
        'night_owl': 'Gece Baykuşu',
        'consistent': 'İstikrarlı',
        'explorer': 'Kaşif',
        'milestone_10': '10 Test',
        'milestone_25': '25 Test',
        'milestone_50': '50 Test',
        'milestone_100': '100 Test'
    }

    # Rozet seviyeleri
    BADGE_LEVELS = {
        'bronze': {'name': 'Bronz', 'color': '#CD7F32', 'min_points': 0},
        'silver': {'name': 'Gümüş', 'color': '#C0C0C0', 'min_points': 100},
        'gold': {'name': 'Altın', 'color': '#FFD700', 'min_points': 250},
        'platinum': {'name': 'Platin', 'color': '#E5E4E2', 'min_points': 500},
        'diamond': {'name': 'Elmas', 'color': '#B9F2FF', 'min_points': 1000}
    }

    # Puan sistemi
    POINT_SYSTEM = {
        'test_completion': 10,
        'perfect_score': 50,
        'score_90_plus': 25,
        'score_80_plus': 15,
        'streak_bonus': 5,  # her seri testi için
        'improvement': 20,
        'speed_bonus': 10,
        'topic_mastery': 30
    }

    @classmethod
    def check_and_award_achievements(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> Dict[str, Any]:
        """
        Test sonuçlarına göre başarıları kontrol ve ödül ver
        """
        try:
            awarded_achievements = []
            total_points_earned = 0

            # Mevcut istatistikleri al
            stats = anonymous_user.stats
            if not stats:
                stats, _ = AnonymousStats.objects.get_or_create(
                    anonymous_user=anonymous_user,
                    defaults={
                        'total_tests_taken': 0,
                        'total_correct_answers': 0,
                        'total_wrong_answers': 0,
                        'average_score': 0.0,
                        'highest_score': 0.0,
                        'current_streak': 0,
                        'best_streak': 0,
                        'total_time_spent': timedelta(0),
                        'last_test_date': None,
                    }
                )

            # Test tamamlama başarısı
            if stats.total_tests_taken == 1:
                achievement = cls._award_achievement(anonymous_user, 'first_test')
                if achievement:
                    awarded_achievements.append(achievement)
                    total_points_earned += cls.POINT_SYSTEM['test_completion']

            # Seri başarıları
            streak_achievements = cls._check_streak_achievements(anonymous_user, stats.current_streak)
            awarded_achievements.extend(streak_achievements)
            total_points_earned += len(streak_achievements) * cls.POINT_SYSTEM['streak_bonus']

            # Skor başarıları
            score = exam_result.percentage
            score_achievements = cls._check_score_achievements(anonymous_user, score)
            awarded_achievements.extend(score_achievements)

            if score == 100:
                total_points_earned += cls.POINT_SYSTEM['perfect_score']
            elif score >= 90:
                total_points_earned += cls.POINT_SYSTEM['score_90_plus']
            elif score >= 80:
                total_points_earned += cls.POINT_SYSTEM['score_80_plus']

            # Kilometre taşı başarıları
            milestone_achievements = cls._check_milestone_achievements(anonymous_user, stats.total_tests_taken)
            awarded_achievements.extend(milestone_achievements)

            # Zaman bazlı başarılar
            time_achievements = cls._check_time_achievements(anonymous_user, exam_result.created_at)
            awarded_achievements.extend(time_achievements)

            # Performans bazlı başarılar
            performance_achievements = cls._check_performance_achievements(anonymous_user, exam_result)
            awarded_achievements.extend(performance_achievements)

            # Hız bonusu
            if cls._check_speed_bonus(anonymous_user, exam_result):
                total_points_earned += cls.POINT_SYSTEM['speed_bonus']

            # İyileşme bonusu
            if cls._check_improvement_bonus(anonymous_user, exam_result):
                total_points_earned += cls.POINT_SYSTEM['improvement']

            # Puanları güncelle
            if total_points_earned > 0:
                cls._update_user_points(anonymous_user, total_points_earned)

            # Rozet seviyesini güncelle
            new_badge_level = cls._update_badge_level(anonymous_user)

            result = {
                'awarded_achievements': awarded_achievements,
                'total_points_earned': total_points_earned,
                'new_badge_level': new_badge_level,
                'current_level': cls.get_user_level(anonymous_user),
                'progress_to_next_level': cls.get_progress_to_next_level(anonymous_user)
            }

            logger.info(f"Gamification: User {anonymous_user.id} earned {len(awarded_achievements)} achievements, {total_points_earned} points")
            return result

        except Exception as e:
            logger.error(f"Gamification achievement check error: {e}")
            return {'awarded_achievements': [], 'total_points_earned': 0}

    @classmethod
    def _check_streak_achievements(cls, anonymous_user: AnonymousUser, current_streak: int) -> List[Dict]:
        """
        Seri (streak) başarılarını kontrol et
        """
        achievements = []
        streak_milestones = [3, 7, 14, 30]

        for milestone in streak_milestones:
            if current_streak == milestone:
                achievement_key = f'streak_{milestone}'
                achievement = cls._award_achievement(anonymous_user, achievement_key)
                if achievement:
                    achievements.append(achievement)

        return achievements

    @classmethod
    def _check_score_achievements(cls, anonymous_user: AnonymousUser, score: float) -> List[Dict]:
        """
        Skor bazlı başarıları kontrol et
        """
        achievements = []

        if score == 100:
            achievement = cls._award_achievement(anonymous_user, 'perfect_score')
            if achievement:
                achievements.append(achievement)
        elif score >= 90:
            achievement = cls._award_achievement(anonymous_user, 'score_90_plus')
            if achievement:
                achievements.append(achievement)
        elif score >= 80:
            achievement = cls._award_achievement(anonymous_user, 'score_80_plus')
            if achievement:
                achievements.append(achievement)

        return achievements

    @classmethod
    def _check_milestone_achievements(cls, anonymous_user: AnonymousUser, total_tests: int) -> List[Dict]:
        """
        Kilometre taşı başarılarını kontrol et
        """
        achievements = []
        milestones = [10, 25, 50, 100]

        for milestone in milestones:
            if total_tests == milestone:
                achievement_key = f'milestone_{milestone}'
                achievement = cls._award_achievement(anonymous_user, achievement_key)
                if achievement:
                    achievements.append(achievement)

        return achievements

    @classmethod
    def _check_time_achievements(cls, anonymous_user: AnonymousUser, test_time: datetime) -> List[Dict]:
        """
        Zaman bazlı başarıları kontrol et
        """
        achievements = []
        hour = test_time.hour

        # Erken kuş (6-10 arası)
        if 6 <= hour < 10:
            achievement = cls._award_achievement(anonymous_user, 'early_bird')
            if achievement:
                achievements.append(achievement)

        # Gece baykuşu (22-02 arası)
        elif hour >= 22 or hour < 2:
            achievement = cls._award_achievement(anonymous_user, 'night_owl')
            if achievement:
                achievements.append(achievement)

        # Hafta sonu savaşçısı
        if test_time.weekday() in [5, 6]:  # Cumartesi, Pazar
            achievement = cls._award_achievement(anonymous_user, 'weekend_warrior')
            if achievement:
                achievements.append(achievement)

        return achievements

    @classmethod
    def _check_performance_achievements(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> List[Dict]:
        """
        Performans bazlı başarıları kontrol et
        """
        achievements = []

        # Hız kontrolü (ortalama süreden hızlı)
        if cls._is_fast_performance(anonymous_user, exam_result):
            achievement = cls._award_achievement(anonymous_user, 'speed_demon')
            if achievement:
                achievements.append(achievement)

        # Israrcı (çok sayıda deneme)
        if cls._is_persistent_user(anonymous_user):
            achievement = cls._award_achievement(anonymous_user, 'persistent')
            if achievement:
                achievements.append(achievement)

        # İstikrarlı (düzenli test çözen)
        if cls._is_consistent_user(anonymous_user):
            achievement = cls._award_achievement(anonymous_user, 'consistent')
            if achievement:
                achievements.append(achievement)

        return achievements

    @classmethod
    def _check_speed_bonus(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> bool:
        """
        Hız bonusunu kontrol et
        """
        try:
            # Kullanıcının ortalama süresini hesapla
            recent_results = TempExamResult.objects.filter(
                anonymous_user=anonymous_user,
                time_taken__isnull=False
            ).order_by('-created_at')[:10]

            if len(recent_results) < 3:
                return False

            total_time = sum(r.time_taken.total_seconds() for r in recent_results if r.time_taken)
            avg_time = total_time / len(recent_results)

            # Bu test ortalamanın %20'sinden hızlı mı?
            current_time = exam_result.time_taken.total_seconds() if exam_result.time_taken else 0
            return current_time > 0 and current_time < (avg_time * 0.8)

        except Exception as e:
            logger.error(f"Speed bonus check error: {e}")
            return False

    @classmethod
    def _check_improvement_bonus(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> bool:
        """
        İyileşme bonusunu kontrol et
        """
        try:
            # Son 3 testin ortalamasını al
            recent_results = TempExamResult.objects.filter(
                anonymous_user=anonymous_user
            ).order_by('-created_at')[:4]  # 4 alıp sonuncuyu karşılaştıracağız

            if len(recent_results) < 4:
                return False

            # Son 3 testin ortalaması (en son test hariç)
            older_avg = sum(r.percentage for r in recent_results[1:]) / 3
            current_score = exam_result.percentage

            # %10'dan fazla iyileşme var mı?
            return current_score > (older_avg * 1.1)

        except Exception as e:
            logger.error(f"Improvement bonus check error: {e}")
            return False

    @classmethod
    def _is_fast_performance(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> bool:
        """
        Hızlı performans kontrolü
        """
        try:
            if not exam_result.time_taken:
                return False

            # Soru sayısına göre hız kontrolü
            session = exam_result.session
            if not session:
                return False

            question_count = session.questions.count()
            if question_count == 0:
                return False

            # Soru başına ortalama süre (saniye)
            time_per_question = exam_result.time_taken.total_seconds() / question_count

            # 30 saniyeden hızlı mı?
            return time_per_question < 30

        except Exception as e:
            logger.error(f"Fast performance check error: {e}")
            return False

    @classmethod
    def _is_persistent_user(cls, anonymous_user: AnonymousUser) -> bool:
        """
        Israrcı kullanıcı kontrolü
        """
        try:
            # Son 30 günde 15+ test mi?
            thirty_days_ago = timezone.now() - timedelta(days=30)
            test_count = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                created_at__gte=thirty_days_ago,
                status='completed'
            ).count()

            return test_count >= 15

        except Exception as e:
            logger.error(f"Persistent user check error: {e}")
            return False

    @classmethod
    def _is_consistent_user(cls, anonymous_user: AnonymousUser) -> bool:
        """
        İstikrarlı kullanıcı kontrolü
        """
        try:
            # Son 14 günde en az 10 farklı günde test mi?
            fourteen_days_ago = timezone.now() - timedelta(days=14)
            sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                created_at__gte=fourteen_days_ago,
                status='completed'
            ).values('created_at__date').distinct()

            unique_days = len(sessions)
            return unique_days >= 10

        except Exception as e:
            logger.error(f"Consistent user check error: {e}")
            return False

    @classmethod
    def _award_achievement(cls, anonymous_user: AnonymousUser, achievement_key: str) -> Optional[Dict]:
        """
        Başarı ver (daha önce alınmadıysa)
        """
        try:
            # Cache'te kontrol et
            cache_key = f"achievements_{anonymous_user.id}"
            user_achievements = cache.get(cache_key, [])

            if achievement_key in user_achievements:
                return None  # Zaten alınmış

            # Başarı ekle
            user_achievements.append(achievement_key)
            cache.set(cache_key, user_achievements, timeout=cls.CACHE_TIMEOUT_MEDIUM)

            achievement = {
                'key': achievement_key,
                'name': cls.ACHIEVEMENT_TYPES.get(achievement_key, achievement_key),
                'earned_at': timezone.now().isoformat(),
                'points': cls.POINT_SYSTEM.get(achievement_key, 10)
            }

            # Log kaydı
            logger.info(f"Achievement awarded: User {anonymous_user.id}, Achievement: {achievement_key}")

            return achievement

        except Exception as e:
            logger.error(f"Achievement award error: {e}")
            return None

    @classmethod
    def _update_user_points(cls, anonymous_user: AnonymousUser, points: int) -> None:
        """
        Kullanıcı puanlarını güncelle
        """
        try:
            cache_key = f"user_points_{anonymous_user.id}"
            current_points = cache.get(cache_key, 0)
            new_points = current_points + points
            cache.set(cache_key, new_points, timeout=cls.CACHE_TIMEOUT_MEDIUM)

        except Exception as e:
            logger.error(f"User points update error: {e}")

    @classmethod
    def _update_badge_level(cls, anonymous_user: AnonymousUser) -> Optional[str]:
        """
        Rozet seviyesini güncelle
        """
        try:
            current_level = cls.get_user_level(anonymous_user)
            new_level = cls.calculate_badge_level(cls.get_user_points(anonymous_user))

            if current_level != new_level:
                # Seviye atladı
                cache_key = f"badge_level_{anonymous_user.id}"
                cache.set(cache_key, new_level, timeout=cls.CACHE_TIMEOUT_MEDIUM)
                logger.info(f"Badge level up: User {anonymous_user.id}, Level: {current_level} -> {new_level}")
                return new_level

            return None

        except Exception as e:
            logger.error(f"Badge level update error: {e}")
            return None

    @classmethod
    def get_user_points(cls, anonymous_user: AnonymousUser) -> int:
        """
        Kullanıcının toplam puanını al
        """
        try:
            cache_key = f"user_points_{anonymous_user.id}"
            return cache.get(cache_key, 0)
        except Exception:
            return 0

    @classmethod
    def get_user_level(cls, anonymous_user: AnonymousUser) -> str:
        """
        Kullanıcının mevcut rozet seviyesini al
        """
        try:
            cache_key = f"badge_level_{anonymous_user.id}"
            level = cache.get(cache_key)
            if level:
                return level

            points = cls.get_user_points(anonymous_user)
            level = cls.calculate_badge_level(points)
            cache.set(cache_key, level, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return level

        except Exception:
            return 'bronze'

    @classmethod
    def calculate_badge_level(cls, points: int) -> str:
        """
        Puana göre rozet seviyesi hesapla
        """
        for level_name, level_data in reversed(cls.BADGE_LEVELS.items()):
            if points >= level_data['min_points']:
                return level_name
        return 'bronze'

    @classmethod
    def get_progress_to_next_level(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Bir sonraki seviyeye kalan ilerlemeyi hesapla
        """
        try:
            current_points = cls.get_user_points(anonymous_user)
            current_level = cls.get_user_level(anonymous_user)

            # Mevcut seviyeyi bul
            level_names = list(cls.BADGE_LEVELS.keys())
            current_index = level_names.index(current_level)

            if current_index >= len(level_names) - 1:
                # En üst seviye
                return {
                    'current_level': current_level,
                    'next_level': None,
                    'current_points': current_points,
                    'next_level_points': None,
                    'points_needed': 0,
                    'progress_percentage': 100
                }

            next_level = level_names[current_index + 1]
            next_level_points = cls.BADGE_LEVELS[next_level]['min_points']
            points_needed = max(0, next_level_points - current_points)

            # İlerleme yüzdesi
            current_level_points = cls.BADGE_LEVELS[current_level]['min_points']
            if current_index == 0:
                level_range = next_level_points - current_level_points
            else:
                level_range = next_level_points - current_level_points

            progress_in_level = current_points - current_level_points
            progress_percentage = min(100, (progress_in_level / level_range) * 100) if level_range > 0 else 100

            return {
                'current_level': current_level,
                'next_level': next_level,
                'current_points': current_points,
                'next_level_points': next_level_points,
                'points_needed': points_needed,
                'progress_percentage': round(progress_percentage, 1)
            }

        except Exception as e:
            logger.error(f"Progress to next level calculation error: {e}")
            return {
                'current_level': 'bronze',
                'next_level': 'silver',
                'current_points': 0,
                'next_level_points': 100,
                'points_needed': 100,
                'progress_percentage': 0
            }

    @classmethod
    def get_user_achievements(cls, anonymous_user: AnonymousUser) -> List[Dict[str, Any]]:
        """
        Kullanıcının tüm başarılarını al
        """
        try:
            cache_key = f"achievements_{anonymous_user.id}"
            achievement_keys = cache.get(cache_key, [])

            achievements = []
            for key in achievement_keys:
                achievements.append({
                    'key': key,
                    'name': cls.ACHIEVEMENT_TYPES.get(key, key),
                    'earned_at': timezone.now().isoformat(),  # Gerçek tarih tutulabilir
                    'icon': cls._get_achievement_icon(key)
                })

            return achievements

        except Exception as e:
            logger.error(f"Get user achievements error: {e}")
            return []

    @classmethod
    def _get_achievement_icon(cls, achievement_key: str) -> str:
        """
        Başarı ikonunu al
        """
        icon_map = {
            'first_test': '🎯',
            'streak_3': '🔥',
            'streak_7': '💥',
            'streak_14': '⚡',
            'streak_30': '🌟',
            'perfect_score': '💯',
            'score_90_plus': '🎖️',
            'score_80_plus': '🏅',
            'milestone_10': '📊',
            'milestone_25': '📈',
            'milestone_50': '🚀',
            'milestone_100': '👑',
            'early_bird': '🐦',
            'night_owl': '🦉',
            'weekend_warrior': '⚔️',
            'speed_demon': '⚡',
            'persistent': '💪',
            'consistent': '🎯'
        }
        return icon_map.get(achievement_key, '🏆')

    @classmethod
    def get_leaderboard(cls, limit: int = 10, period: str = 'all_time') -> List[Dict[str, Any]]:
        """
        Lider tablosunu al
        """
        try:
            cache_key = f"leaderboard_{period}_{limit}"
            cached_leaderboard = cache.get(cache_key)

            if cached_leaderboard:
                return cached_leaderboard

            # Tarih aralığını belirle
            if period == 'weekly':
                start_date = timezone.now() - timedelta(weeks=1)
            elif period == 'monthly':
                start_date = timezone.now() - timedelta(days=30)
            else:  # all_time
                start_date = None

            # En iyi performans gösteren kullanıcıları al
            queryset = AnonymousStats.objects.all()

            if start_date:
                queryset = queryset.filter(last_test_date__gte=start_date)

            leaderboard = []
            for stats in queryset.select_related('anonymous_user').order_by('-average_score')[:limit]:
                user = stats.anonymous_user
                leaderboard.append({
                    'user_id': user.id,
                    'points': cls.get_user_points(user),
                    'level': cls.get_user_level(user),
                    'average_score': stats.average_score,
                    'total_tests': stats.total_tests_taken,
                    'current_streak': stats.current_streak,
                    'best_streak': stats.best_streak
                })

            # Puanlara göre sırala
            leaderboard.sort(key=lambda x: x['points'], reverse=True)

            # Sıralama numaralarını ekle
            for i, entry in enumerate(leaderboard, 1):
                entry['rank'] = i

            # Cache'e kaydet
            cache.set(cache_key, leaderboard, timeout=cls.CACHE_TIMEOUT_SHORT)
            return leaderboard

        except Exception as e:
            logger.error(f"Leaderboard generation error: {e}")
            return []

    @classmethod
    def get_user_rank(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Kullanıcının sıralamasını al
        """
        try:
            # Lider tablosundaki yerini bul
            leaderboard = cls.get_leaderboard(limit=1000)  # İlk 1000 kullanıcı

            user_entry = next((entry for entry in leaderboard if entry['user_id'] == anonymous_user.id), None)

            if user_entry:
                return {
                    'rank': user_entry['rank'],
                    'total_users': len(leaderboard),
                    'top_percentage': round((user_entry['rank'] / len(leaderboard)) * 100, 1)
                }
            else:
                return {
                    'rank': None,
                    'total_users': len(leaderboard),
                    'top_percentage': None
                }

        except Exception as e:
            logger.error(f"User rank calculation error: {e}")
            return {'rank': None, 'total_users': 0, 'top_percentage': None}

    @classmethod
    def get_motivational_message(cls, anonymous_user: AnonymousUser) -> str:
        """
        Kullanıcıya motivasyon mesajı ver
        """
        try:
            stats = anonymous_user.stats
            if not stats:
                return "Hoş geldin! İlk testini yapmaya hazır mısın? 🎯"

            messages = []

            # Seri mesajları
            if stats.current_streak >= 7:
                messages.append(f"🔥 Harika! {stats.current_streak} günlük serin devam ediyor!")
            elif stats.current_streak >= 3:
                messages.append(f"👏 {stats.current_streak} günlük serin var. Devam et!")

            # Skor mesajları
            if stats.average_score >= 90:
                messages.append("🏆 Mükemmel performans! Sen bir uzmanısın.")
            elif stats.average_score >= 80:
                messages.append("🌟 Çok iyi gidiyorsun! Bu performans harika.")
            elif stats.average_score >= 70:
                messages.append("💪 İyi ilerleme. Devam ettikçe daha da iyi olacaksın.")

            # Seviye mesajları
            level = cls.get_user_level(anonymous_user)
            if level == 'diamond':
                messages.append("💎 Elmas seviyesinde! Inanılmaz bir başarı.")
            elif level == 'platinum':
                messages.append("🥇 Platin seviye! Çok az kişi bu seviyeye ulaşır.")
            elif level == 'gold':
                messages.append("🥇 Altın seviye! Performansın parlıyor.")
            elif level == 'silver':
                messages.append("🥈 Gümüş seviye! İlerleme kaydediyorsun.")

            # Son test mesajı
            if stats.last_test_date:
                days_since_last = (timezone.now().date() - stats.last_test_date.date()).days
                if days_since_last == 1:
                    messages.append("😊 Dünkü harika performansından sonra bugün de pratik yapmaya ne dersin?")
                elif days_since_last >= 3:
                    messages.append("💡 Bir süredir test çözmüyorsun. Pratik yapmak performansını artırır!")

            return messages[0] if messages else "📚 Her test seni daha da ileriye taşıyor. Devam et!"

        except Exception as e:
            logger.error(f"Motivational message error: {e}")
            return "🎯 Hedeflerine ulaşmak için devam et!"

    @classmethod
    def get_daily_challenge(cls, anonymous_user: AnonymousUser) -> Optional[Dict[str, Any]]:
        """
        Günlük meydan okuma oluştur
        """
        try:
            # Cache'te mevcut meydan okumayı kontrol et
            today = timezone.now().date()
            cache_key = f"daily_challenge_{anonymous_user.id}_{today}"
            cached_challenge = cache.get(cache_key)

            if cached_challenge:
                return cached_challenge

            # Kullanıcı performansına göre meydan okuma oluştur
            stats = anonymous_user.stats
            if not stats or stats.total_tests_taken < 2:
                return {
                    'type': 'first_test',
                    'title': 'İlk Test Meydan Okuması',
                    'description': 'Bugün ilk testini yap ve 10 puan kazan!',
                    'target': 1,
                    'reward_points': 10,
                    'completed': False
                }

            # Rastgele meydan okuma türü seç
            import random
            challenge_types = ['score_target', 'streak_continue', 'speed_run', 'consistency']
            challenge_type = random.choice(challenge_types)

            if challenge_type == 'score_target':
                target_score = min(95, stats.highest_score + 5)
                return {
                    'type': 'score_target',
                    'title': f'{target_score}% Skor Hedefi',
                    'description': f"Bugün bir testte %{target_score} veya üzeri skor yap ve 20 puan kazan!",
                    'target_score': target_score,
                    'reward_points': 20,
                    'completed': False
                }

            elif challenge_type == 'streak_continue':
                return {
                    'type': 'streak_continue',
                    'title': 'Seri Devam',
                    'description': 'Seriğini kaybetme! Bugün en az bir test çöz ve 15 puan kazan!',
                    'reward_points': 15,
                    'completed': False
                }

            elif challenge_type == 'speed_run':
                return {
                    'type': 'speed_run',
                    'title': 'Hızlı Çözüm',
                    'description': 'Normal hızından %20 daha hızlı bir test tamamla ve 25 puan kazan!',
                    'reward_points': 25,
                    'completed': False
                }

            elif challenge_type == 'consistency':
                return {
                    'type': 'consistency',
                    'title': 'İstikrarlı Ol',
                    'description': 'Bu hafta en az 5 farklı günde test çöz ve 30 puan kazan!',
                    'target_days': 5,
                    'reward_points': 30,
                    'completed': False
                }

        except Exception as e:
            logger.error(f"Daily challenge generation error: {e}")
            return None

    @classmethod
    def check_daily_challenge_completion(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> Optional[Dict[str, Any]]:
        """
        Günlük meydan okuma tamamlanmasını kontrol et
        """
        try:
            challenge = cls.get_daily_challenge(anonymous_user)
            if not challenge or challenge.get('completed'):
                return None

            completed = False
            reward_points = 0

            if challenge['type'] == 'first_test':
                completed = True
                reward_points = challenge['reward_points']

            elif challenge['type'] == 'score_target':
                if exam_result.percentage >= challenge['target_score']:
                    completed = True
                    reward_points = challenge['reward_points']

            elif challenge['type'] == 'streak_continue':
                # Seri devam kontrolü zaten achievement check'te yapılıyor
                completed = True
                reward_points = challenge['reward_points']

            elif challenge['type'] == 'speed_run':
                if cls._check_speed_bonus(anonymous_user, exam_result):
                    completed = True
                    reward_points = challenge['reward_points']

            if completed:
                # Meydan okumayı tamamlandı olarak işaretle
                today = timezone.now().date()
                cache_key = f"daily_challenge_{anonymous_user.id}_{today}"
                challenge['completed'] = True
                challenge['completed_at'] = timezone.now().isoformat()
                cache.set(cache_key, challenge, timeout=86400)  # 1 gün

                # Ödül puanlarını ver
                cls._update_user_points(anonymous_user, reward_points)

                return {
                    'challenge': challenge,
                    'reward_points': reward_points,
                    'message': f"🎉 Günlük meydan okuma tamamlandı! {reward_points} puan kazandın!"
                }

            return None

        except Exception as e:
            logger.error(f"Daily challenge completion check error: {e}")
            return None