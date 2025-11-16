import logging
from typing import Dict, List, Tuple, Optional, Any
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Count, Avg, Sum, Max, Min, StdDev, Variance, Q, F
from django.db.models.functions import Trunc, Extract
from collections import defaultdict
import json

from quiz.models import AnonymousUser, AnonymousStats, TempExamSession, TempExamResult, Question, Subject, Topic

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Kapsamlı Analitik ve İçgörü Servisi"""

    # Cache süreleri
    CACHE_TIMEOUT_SHORT = 300    # 5 dakika
    CACHE_TIMEOUT_MEDIUM = 1800  # 30 dakika
    CACHE_TIMEOUT_LONG = 3600    # 1 saat

    # Analitik periyotları
    PERIODS = {
        'today': 1,
        'week': 7,
        'month': 30,
        'quarter': 90,
        'year': 365
    }

    @classmethod
    def get_dashboard_analytics(cls, period: str = 'week') -> Dict[str, Any]:
        """
        Dashboard analitik verilerini al
        """
        try:
            cache_key = f"dashboard_analytics_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            days = cls.PERIODS.get(period, 7)
            start_date = timezone.now().date() - timedelta(days=days)

            # Genel istatistikler
            total_sessions = TempExamSession.objects.filter(
                created_at__date__gte=start_date
            ).count()

            completed_sessions = TempExamSession.objects.filter(
                created_at__date__gte=start_date,
                status='completed'
            ).count()

            total_users = AnonymousUser.objects.filter(
                created_at__date__gte=start_date
            ).count()

            active_users = AnonymousUser.objects.filter(
                last_seen__date__gte=start_date
            ).count()

            # Performans istatistikleri
            avg_score = TempExamResult.objects.filter(
                created_at__date__gte=start_date
            ).aggregate(avg_score=Avg('percentage'))['avg_score'] or 0

            total_tests_completed = TempExamResult.objects.filter(
                created_at__date__date__gte=start_date
            ).count()

            high_performers = TempExamResult.objects.filter(
                created_at__date__date__gte=start_date,
                percentage__gte=80
            ).count()

            # Günlük trend verileri
            daily_stats = cls._get_daily_trends(start_date)

            # Konu bazında performans
            subject_performance = cls._get_subject_performance(start_date)

            # Demografik veriler
            demographics = cls._get_demographics(start_date)

            analytics = {
                'period': period,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': timezone.now().date().isoformat()
                },
                'overview': {
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'completion_rate': round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 1),
                    'total_users': total_users,
                    'active_users': active_users,
                    'user_retention': round((active_users / total_users * 100) if total_users > 0 else 0, 1)
                },
                'performance': {
                    'average_score': round(avg_score, 1),
                    'total_tests_completed': total_tests_completed,
                    'high_performers': high_performers,
                    'high_performance_rate': round((high_performers / total_tests_completed * 100) if total_tests_completed > 0 else 0, 1)
                },
                'daily_trends': daily_stats,
                'subject_performance': subject_performance,
                'demographics': demographics,
                'generated_at': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, analytics, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return analytics

        except Exception as e:
            logger.error(f"Dashboard analytics error: {e}")
            return cls._get_empty_analytics(period)

    @classmethod
    def get_user_analytics(cls, anonymous_user: AnonymousUser, period: str = 'month') -> Dict[str, Any]:
        """
        Kullanıcı bazında detaylı analitikler
        """
        try:
            cache_key = f"user_analytics_{anonymous_user.id}_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            days = cls.PERIODS.get(period, 30)
            start_date = timezone.now() - timedelta(days=days)

            # Kullanıcının test sonuçları
            user_results = TempExamResult.objects.filter(
                anonymous_user=anonymous_user,
                created_at__gte=start_date
            ).order_by('-created_at')

            # Performans trend'i
            performance_trend = cls._calculate_performance_trend(user_results)

            # Konu bazında performans
            subject_performance = cls._get_user_subject_performance(user_results)

            # Zaman bazında performans
            time_performance = cls._get_user_time_performance(user_results)

            # İyileşme alanları
            improvement_areas = cls._identify_improvement_areas(user_results)

            # Başarı metrikleri
            success_metrics = cls._calculate_success_metrics(user_results)

            analytics = {
                'user_id': anonymous_user.id,
                'period': period,
                'overview': {
                    'total_tests': user_results.count(),
                    'average_score': round(user_results.aggregate(Avg('percentage'))['percentage'] or 0, 1),
                    'highest_score': user_results.aggregate(Max('percentage'))['percentage'] or 0,
                    'lowest_score': user_results.aggregate(Min('percentage'))['percentage'] or 0,
                    'score_improvement': performance_trend.get('improvement', 0),
                    'consistency_score': cls._calculate_consistency_score(user_results)
                },
                'performance_trend': performance_trend,
                'subject_performance': subject_performance,
                'time_performance': time_performance,
                'improvement_areas': improvement_areas,
                'success_metrics': success_metrics,
                'generated_at': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, analytics, timeout=cls.CACHE_TIMEOUT_SHORT)
            return analytics

        except Exception as e:
            logger.error(f"User analytics error: {e}")
            return {'error': str(e), 'user_id': anonymous_user.id}

    @classmethod
    def get_content_analytics(cls, period: str = 'month') -> Dict[str, Any]:
        """
        İçerik analitikleri (sorular, konular, zorluk seviyeleri)
        """
        try:
            cache_key = f"content_analytics_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            # Soru analizleri
            question_stats = cls._analyze_questions()

            # Konu analizi
            topic_analysis = cls._analyze_topics()

            # Zorluk dağılımı
            difficulty_distribution = cls._get_difficulty_distribution()

            # Popüler içerikler
            popular_content = cls._get_popular_content()

            analytics = {
                'period': period,
                'questions': question_stats,
                'topics': topic_analysis,
                'difficulty_distribution': difficulty_distribution,
                'popular_content': popular_content,
                'generated_at': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, analytics, timeout=cls.CACHE_TIMEOUT_LONG)
            return analytics

        except Exception as e:
            logger.error(f"Content analytics error: {e}")
            return {'error': str(e)}

    @classmethod
    def get_engagement_analytics(cls, period: str = 'week') -> Dict[str, Any]:
        """
        Kullanıcı etkileşim analitikleri
        """
        try:
            cache_key = f"engagement_analytics_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            days = cls.PERIODS.get(period, 7)
            start_date = timezone.now().date() - timedelta(days=days)

            # Kullanıcı etkinliği
            user_activity = cls._analyze_user_activity(start_date)

            # Oturum analizi
            session_analysis = cls._analyze_sessions(start_date)

            # Retention analizi
            retention_analysis = cls._analyze_retention(start_date)

            # Stickiness metrikleri
            stickiness_metrics = cls._calculate_stickiness_metrics(start_date)

            analytics = {
                'period': period,
                'user_activity': user_activity,
                'session_analysis': session_analysis,
                'retention_analysis': retention_analysis,
                'stickiness_metrics': stickiness_metrics,
                'generated_at': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, analytics, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return analytics

        except Exception as e:
            logger.error(f"Engagement analytics error: {e}")
            return {'error': str(e)}

    @classmethod
    def get_conversion_funnel(cls, period: str = 'month') -> Dict[str, Any]:
        """
        Dönüşüm hunisi analizi
        """
        try:
            cache_key = f"conversion_funnel_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            days = cls.PERIODS.get(period, 30)
            start_date = timezone.now().date() - timedelta(days=days)

            # Huni aşamaları
            funnel_stages = {
                'visitors': cls._get_visitor_count(start_date),
                'test_creators': cls._get_test_creators(start_date),
                'test_starters': cls._get_test_starters(start_date),
                'test_completers': cls._get_test_completers(start_date),
                'repeat_users': cls._get_repeat_users(start_date)
            }

            # Dönüşüm oranları
            conversion_rates = cls._calculate_conversion_rates(funnel_stages)

            # Huni analizi
            funnel_analysis = cls._analyze_funnel(funnel_stages, start_date)

            analytics = {
                'period': period,
                'funnel_stages': funnel_stages,
                'conversion_rates': conversion_rates,
                'funnel_analysis': funnel_analysis,
                'generated_at': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, analytics, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return analytics

        except Exception as e:
            logger.error(f"Conversion funnel error: {e}")
            return {'error': str(e)}

    @classmethod
    def generate_report(cls, report_type: str, period: str = 'month', format: str = 'json') -> Dict[str, Any]:
        """
        Otomatik rapor oluştur
        """
        try:
            report_generators = {
                'dashboard': cls._generate_dashboard_report,
                'user_performance': cls._generate_user_performance_report,
                'content_analysis': cls._generate_content_report,
                'engagement': cls._generate_engagement_report,
                'conversion': cls._generate_conversion_report
            }

            if report_type not in report_generators:
                return {'error': f'Geçersiz rapor tipi: {report_type}'}

            report = report_generators[report_type](period, format)

            return {
                'report_type': report_type,
                'period': period,
                'format': format,
                'data': report,
                'generated_at': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return {'error': str(e), 'report_type': report_type}

    # ==================== PRIVATE METHODS ====================

    @classmethod
    def _get_daily_trends(cls, start_date) -> List[Dict]:
        """
        Günlük trend verileri
        """
        try:
            trends = []
            current_date = start_date
            end_date = timezone.now().date()

            while current_date <= end_date:
                day_data = TempExamResult.objects.filter(
                    created_at__date=current_date
                ).aggregate(
                    total_tests=Count('id'),
                    avg_score=Avg('percentage'),
                    high_performers=Count('id', filter=Q(percentage__gte=80))
                )

                trends.append({
                    'date': current_date.isoformat(),
                    'total_tests': day_data['total_tests'],
                    'average_score': round(day_data['avg_score'] or 0, 1),
                    'high_performers': day_data['high_performers'],
                    'high_performance_rate': round((day_data['high_performers'] / day_data['total_tests'] * 100) if day_data['total_tests'] > 0 else 0, 1)
                })

                current_date += timedelta(days=1)

            return trends

        except Exception as e:
            logger.error(f"Daily trends error: {e}")
            return []

    @classmethod
    def _get_subject_performance(cls, start_date) -> Dict[str, Any]:
        """
        Konu bazında performans analizi
        """
        try:
            # Test başına konu performansı
            subject_data = TempExamResult.objects.filter(
                created_at__date__gte=start_date
            ).values(
                'session__subject'
            ).annotate(
                test_count=Count('id'),
                avg_score=Avg('percentage'),
                total_correct=Sum('correct_answers'),
                total_questions=Sum('total_questions')
            ).order_by('avg_score')

            # Konu isimleri ve istatistikler
            subjects = Subject.objects.all()
            performance = {}

            for data in subject_data:
                subject_code = data['session__subject']
                try:
                    subject = subjects.get(code=subject_code)
                    subject_name = subject.name
                except Subject.DoesNotExist:
                    subject_name = subject_code

                performance[subject_name] = {
                    'test_count': data['test_count'],
                    'average_score': round(data['avg_score'] or 0, 1),
                    'total_correct': data['total_correct'] or 0,
                    'total_questions': data['total_questions'] or 0,
                    'success_rate': round(((data['total_correct'] or 0) / (data['total_questions'] or 1)) * 100, 1)
                }

            return {
                'subjects': performance,
                'best_performing': max(performance.items(), key=lambda x: x[1]['average_score']) if performance else None,
                'worst_performing': min(performance.items(), key=lambda x: x[1]['average_score']) if performance else None
            }

        except Exception as e:
            logger.error(f"Subject performance error: {e}")
            return {}

    @classmethod
    def _get_demographics(cls, start_date) -> Dict[str, Any]:
        """
        Demografik analizler
        """
        try:
            # Zaman bazında kullanıcı dağılımı
            users_by_signup = AnonymousUser.objects.filter(
                created_at__date__gte=start_date
            ).annotate(
                hour=Extract('hour', 'created_at'),
                day_of_week=Extract('week_day', 'created_at')
            ).values('hour', 'day_of_week').annotate(count=Count('id'))

            # Saat bazında dağılım
            hourly_dist = defaultdict(int)
            for item in users_by_signup:
                if item['hour']:
                    hourly_dist[item['hour']] += item['count']

            # Gün bazında dağılım
            daily_dist = defaultdict(int)
            day_names = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
            for item in users_by_signup:
                if item['day_of_week'] is not None and 0 <= item['day_of_week'] < 7:
                    day_name = day_names[item['day_of_week']]
                    daily_dist[day_name] += item['count']

            return {
                'hourly_distribution': dict(hourly_dist),
                'daily_distribution': dict(daily_dist),
                'peak_hour': max(hourly_dist.items(), key=lambda x: x[1])[0] if hourly_dist else None,
                'peak_day': max(daily_dist.items(), key=lambda x: x[1])[0] if daily_dist else None
            }

        except Exception as e:
            logger.error(f"Demographics error: {e}")
            return {}

    @classmethod
    def _calculate_performance_trend(cls, results) -> Dict[str, Any]:
        """
        Performans trend'i hesapla
        """
        try:
            if results.count() < 2:
                return {'trend': 'insufficient_data', 'improvement': 0}

            scores = [result.percentage for result in results]

            # İlk ve son yarımların ortalaması
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            improvement = second_avg - first_avg

            # Trend belirle
            if improvement > 10:
                trend = 'strong_improving'
            elif improvement > 5:
                trend = 'improving'
            elif improvement > -5:
                trend = 'stable'
            elif improvement > -10:
                trend = 'declining'
            else:
                trend = 'strong_declining'

            return {
                'trend': trend,
                'improvement': round(improvement, 1),
                'first_half_average': round(first_avg, 1),
                'second_half_average': round(second_avg, 1)
            }

        except Exception as e:
            logger.error(f"Performance trend calculation error: {e}")
            return {'trend': 'error', 'improvement': 0}

    @classmethod
    def _get_user_subject_performance(cls, user_results) -> Dict[str, Any]:
        """
        Kullanıcının konu bazında performansı
        """
        try:
            subject_performance = defaultdict(list)

            for result in user_results:
                if result.session:
                    subject = result.session.subject
                    subject_performance[subject].append(result.percentage)

            # Her konu için istatistikleri hesapla
            performance = {}
            for subject, scores in subject_performance.items():
                if scores:
                    performance[subject] = {
                        'test_count': len(scores),
                        'average_score': round(sum(scores) / len(scores), 1),
                        'highest_score': max(scores),
                        'lowest_score': min(scores),
                        'score_trend': cls._calculate_simple_trend(scores)
                    }

            return performance

        except Exception as e:
            logger.error(f"User subject performance error: {e}")
            return {}

    @classmethod
    def _get_user_time_performance(cls, user_results) -> Dict[str, Any]:
        """
        Kullanıcının zaman bazında performansı
        """
        try:
            if user_results.count() < 2:
                return {'avg_time_per_question': 0, 'time_trend': 'insufficient_data'}

            total_time = sum(
                result.time_taken.total_seconds() for result in user_results
                if result.time_taken
            )
            total_questions = sum(
                result.total_questions for result in user_results
            )

            avg_time_per_question = total_time / total_questions if total_questions > 0 else 0

            return {
                'avg_time_per_question': round(avg_time_per_question, 1),
                'avg_time_per_question_formatted': f"{int(avg_time_per_question)}s",
                'total_time_spent': round(total_time / 3600, 1),  # saat
                'total_questions_answered': total_questions
            }

        except Exception as e:
            logger.error(f"User time performance error: {e}")
            return {'avg_time_per_question': 0, 'time_trend': 'error'}

    @classmethod
    def _identify_improvement_areas(cls, user_results) -> List[Dict]:
        """
        İyileşme alanlarını belirle
        """
        try:
            if not user_results.exists():
                return []

            subject_performance = cls._get_user_subject_performance(user_results)
            improvement_areas = []

            for subject, data in subject_performance.items():
                if data['average_score'] < 60:  # %60 altı
                    improvement_areas.append({
                        'subject': subject,
                        'current_average': data['average_score'],
                        'recommendation': f'{subject} konusunu daha fazla çalışın',
                        'priority': 'high' if data['average_score'] < 40 else 'medium'
                    })

            # Genel skor düşükse
            overall_avg = user_results.aggregate(Avg('percentage'))['percentage'] or 0
            if overall_avg < 70 and len(improvement_areas) == 0:
                improvement_areas.append({
                    'subject': 'Genel Performans',
                    'current_average': overall_avg,
                    'recommendation': 'Daha düzenli pratik yapın ve zaman yönetimini iyileştirin',
                    'priority': 'high' if overall_avg < 50 else 'medium'
                })

            return sorted(improvement_areas, key=lambda x: x['current_average'])

        except Exception as e:
            logger.error(f"Improvement areas error: {e}")
            return []

    @classmethod
    def _calculate_success_metrics(cls, user_results) -> Dict[str, Any]:
        """
        Başarı metriklerini hesapla
        """
        try:
            total_tests = user_results.count()
            if total_tests == 0:
                return {}

            # Başarı ve başarısız test sayıları
            successful_tests = user_results.filter(percentage >= 70).count()
            excellent_tests = user_results.filter(percentage >= 90).count()

            return {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'excellent_tests': excellent_tests,
                'success_rate': round((successful_tests / total_tests) * 100, 1),
                'excellence_rate': round((excellent_tests / total_tests) * 100, 1),
                'consistency_score': cls._calculate_consistency_score(user_results)
            }

        except Exception as e:
            logger.error(f"Success metrics calculation error: {e}")
            return {}

    @classmethod
    def _calculate_consistency_score(cls, user_results) -> float:
        """
        Tutarlılık skorunu hesapla (0-100)
        """
        try:
            if user_results.count() < 3:
                return 50.0

            scores = [result.percentage for result in user_results.order_by('created_at')]

            # Standart sapmayı hesapla
            if len(scores) < 2:
                return 50.0

            avg_score = sum(scores) / len(scores)
            variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)

            # Varyans düşükse tutarlılık yüksek (100 - varyans/25)
            consistency = max(0, min(100, 100 - (variance / 25)))

            return round(consistency, 1)

        except Exception as e:
            logger.error(f"Consistency score calculation error: {e}")
            return 50.0

    @classmethod
    def _calculate_simple_trend(cls, scores) -> str:
        """
        Basit trend analizi
        """
        try:
            if len(scores) < 2:
                return 'stable'

            first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2) if scores[:len(scores)//2] else 0
            second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2) if len(scores) > len(scores)//2 else 0

            if second_half_avg > first_half_avg + 10:
                return 'improving'
            elif second_half_avg < first_half_avg - 10:
                return 'declining'
            else:
                return 'stable'

        except Exception:
            return 'stable'

    @classmethod
    def _get_empty_analytics(cls, period: str) -> Dict[str, Any]:
        """
        Boş analitik verisi döndür
        """
        return {
            'period': period,
            'error': 'Insufficient data for analysis',
            'overview': {
                'total_sessions': 0,
                'completed_sessions': 0,
                'completion_rate': 0,
                'total_users': 0,
                'active_users': 0,
                'user_retention': 0
            },
            'performance': {
                'average_score': 0,
                'total_tests_completed': 0,
                'high_performers': 0,
                'high_performance_rate': 0
            },
            'generated_at': timezone.now().isoformat()
        }

    # Diğer private metodlar buraya eklenebilir...
    @classmethod
    def _analyze_questions(cls):
        """Soru analizi"""
        try:
            total_questions = Question.objects.count()
            by_difficulty = Question.objects.values('difficulty').annotate(count=Count('id'))

            return {
                'total_count': total_questions,
                'by_difficulty': list(by_difficulty),
                'avg_difficulty': Question.objects.aggregate(avg=Avg('difficulty'))['avg'] or 0
            }
        except Exception as e:
            logger.error(f"Question analysis error: {e}")
            return {}

    @classmethod
    def _analyze_topics(cls):
        """Konu analizi"""
        try:
            return {
                'total_topics': Topic.objects.count(),
                'questions_per_topic': Topic.objects.annotate(question_count=Count('question')).values_list('question_count', flat=True),
                'topics_with_questions': Topic.objects.annotate(question_count=Count('question')).filter(question_count__gt=0).count()
            }
        except Exception as e:
            logger.error(f"Topic analysis error: {e}")
            return {}

    @classmethod
    def _get_difficulty_distribution(cls):
        """Zorluk dağılımı"""
        try:
            return list(Question.objects.values('difficulty').annotate(count=Count('id')).order_by('difficulty'))
        except Exception as e:
            logger.error(f"Difficulty distribution error: {e}")
            return []

    @classmethod
    def _get_popular_content(cls):
        """Popüler içerikler"""
        try:
            return {
                'popular_topics': Topic.objects.annotate(question_count=Count('question'))
                    .filter(question_count__gt=10)
                    .order_by('-question_count')[:10]
                    .values_list('name', 'question_count'),
                'high_scoring_questions': Question.objects.filter(difficulty__gte=4).count(),
                'recent_questions': Question.objects.order_by('-created_at')[:10].values_list('id', flat=True)
            }
        except Exception as e:
            logger.error(f"Popular content error: {e}")
            return {}

    @classmethod
    def _analyze_user_activity(cls, start_date):
        """Kullanıcı etkinliği analizi"""
        try:
            return {
                'new_users': AnonymousUser.objects.filter(created_at__date__gte=start_date).count(),
                'active_users': AnonymousUser.objects.filter(last_seen__date__gte=start_date).count(),
                'users_with_tests': 0,  # TODO: Fix when anonymous_user field is added to TempExamSession
                'average_tests_per_user': TempExamSession.objects.filter(created_at__date__gte=start_date).count() / max(1, AnonymousUser.objects.filter(last_seen__date__gte=start_date).count())
            }
        except Exception as e:
            logger.error(f"User activity analysis error: {e}")
            return {}

    @classmethod
    def _analyze_sessions(cls, start_date):
        """Oturum analizi"""
        try:
            return {
                'total_sessions': TempExamSession.objects.filter(created_at__date__gte=start_date).count(),
                'completed_sessions': TempExamSession.objects.filter(created_at__date__gte=start_date, status='completed').count(),
                'abandoned_sessions': TempExamSession.objects.filter(created_at__date__gte=start_date, status='abandoned').count(),
                'expired_sessions': TempExamSession.objects.filter(created_at__date__gte=start_date, status='expired').count(),
                'average_session_duration': 'N/A'  # Gerekli veri olmadan hesaplanamaz
            }
        except Exception as e:
            logger.error(f"Session analysis error: {e}")
            return {}

    @classmethod
    def _analyze_retention(cls, start_date):
        """Retention analizi"""
        try:
            return {
                'day_1_retention': cls._calculate_retention_by_days(start_date, 1),
                'day_7_retention': cls._calculate_retention_by_days(start_date, 7),
                'day_30_retention': cls._calculate_retention_by_days(start_date, 30)
            }
        except Exception as e:
            logger.error(f"Retention analysis error: {e}")
            return {}

    @classmethod
    def _calculate_retention_by_days(cls, start_date, days):
        """Belirli gün sayısına göre retention hesapla"""
        try:
            cohort_users = AnonymousUser.objects.filter(created_at_date=start_date)
            if not cohort_users.exists():
                return 0

            retained_users = cohort_users.filter(
                last_seen__date__gte=start_date + timedelta(days=days)
            ).count()

            return round((retained_users / cohort_users.count()) * 100, 1)
        except Exception as e:
            logger.error(f"Retention calculation error: {e}")
            return 0

    @classmethod
    def _calculate_stickiness_metrics(cls, start_date):
        """Yapışkanlık metrikleri"""
        try:
            return {
                'average_session_completion_rate': 85.5,  # Örnek değer
                'return_user_rate': 42.3,  # Örnek değer
                'stickiness_index': 78.9  # Örnek değer
            }
        except Exception as e:
            logger.error(f"Stickiness metrics error: {e}")
            return {}

    @classmethod
    def _get_visitor_count(cls, start_date):
        """Ziyaretçi sayısı"""
        try:
            # Browser ID tabanlı benzersiz kullanıcı sayısı
            # TODO: Fix when anonymous_user field is added to TempExamSession
            return 0
        except Exception as e:
            logger.error(f"Visitor count error: {e}")
            return 0

    @classmethod
    def _get_test_creators(cls, start_date):
        """Test oluşturanlar"""
        try:
            # TODO: Fix when anonymous_user field is added to TempExamSession
            return 0
        except Exception as e:
            logger.error(f"Test creators error: {e}")
            return 0

    @classmethod
    def _get_test_starters(cls, start_date):
        """Test başlatanlar"""
        try:
            # Bu bilgi mevcut veri modelinde doğrudan bulunmuyor
            return TempExamSession.objects.filter(created_at__date__gte=start_date, status='started').count()
        except Exception as e:
            logger.error(f"Test starters error: {e}")
            return 0

    @classmethod
    def _get_test_completers(cls, start_date):
        """Test bitirenler"""
        try:
            return TempExamSession.objects.filter(created_at__date__gte=start_date, status='completed').count()
        except Exception as e:
            logger.error(f"Test completers error: {e}")
            return 0

    @classmethod
    def _get_repeat_users(cls, start_date):
        """Tekrar eden kullanıcılar"""
        try:
            users_with_multiple_tests = TempExamSession.objects.filter(
                created_at__date__gte=start_date
            ).values('anonymous_user').annotate(session_count=Count('id')).filter(session_count__gt=1).count()

            total_users = TempExamSession.objects.filter(
                created_at__date__gte=start_date
            ).values('anonymous_user').distinct().count()

            return round((users_with_multiple_tests / total_users) * 100, 1) if total_users > 0 else 0
        except Exception as e:
            logger.error(f"Repeat users error: {e}")
            return 0

    @classmethod
    def _calculate_conversion_rates(cls, stages):
        """Dönüşüm oranlarını hesapla"""
        try:
            return {
                'visitor_to_creator': round((stages['test_creators'] / stages['visitors']) * 100, 1) if stages['visitors'] > 0 else 0,
                'creator_to_starter': round((stages['test_starters'] / stages['test_creators']) * 100, 1) if stages['test_creators'] > 0 else 0,
                'starter_to_completer': round((stages['test_completers'] / stages['test_starters']) * 100, 1) if stages['test_starters'] > 0 else 0,
                'overall_conversion': round((stages['test_completers'] / stages['visitors']) * 100, 1) if stages['visitors'] > 0 else 0
            }
        except Exception as e:
            logger.error(f"Conversion rates calculation error: {e}")
            return {}

    @classmethod
    def _analyze_funnel(cls, stages, start_date):
        """Dönüşüm hunisi analizi"""
        try:
            return {
                'largest_drop': 'creator_to_starter',  # Bu değer dinamik hesaplanmalı
                'drop_percentage': 25.5,  # Örnek değer
                'bottleneck_stage': 'test_creation'
            }
        except Exception as e:
            logger.error(f"Funnel analysis error: {e}")
            return {}

    @classmethod
    def _generate_dashboard_report(cls, period, format):
        """Dashboard raporu"""
        return cls.get_dashboard_analytics(period)

    @classmethod
    def _generate_user_performance_report(cls, period, format):
        """Kullanıcı performans raporu"""
        return {'message': 'User performance report (placeholder)'}

    @classmethod
    def _generate_content_report(cls, period, format):
        """İçerik raporu"""
        return cls.get_content_analytics(period)

    @classmethod
    def _generate_engagement_report(cls, period, format):
        """Etkileşim raporu"""
        return cls.get_engagement_analytics(period)

    @classmethod
    def _generate_conversion_report(cls, period, format):
        """Dönüşüm raporu"""
        return cls.get_conversion_funnel(period)