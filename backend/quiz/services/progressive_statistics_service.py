import logging
from typing import Dict, List, Tuple, Optional, Any
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Avg, Max, Min, Count, Q, F, StdDev, Variance
from django.core.cache import cache

from quiz.models import AnonymousUser, AnonymousStats, TempExamSession, TempExamResult, Question

logger = logging.getLogger(__name__)


class ProgressiveStatisticsService:
    """Gelişmiş İstatistik Takip Servisi"""

    # Cache süreleri
    CACHE_TIMEOUT_SHORT = 300    # 5 dakika
    CACHE_TIMEOUT_MEDIUM = 1800  # 30 dakika
    CACHE_TIMEOUT_LONG = 3600    # 1 saat

    # İstatistik periyotları
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'
    PERIOD_ALL_TIME = 'all_time'

    @classmethod
    def update_user_statistics(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> None:
        """
        Kullanıcı istatistiklerini güncelle
        """
        try:
            # Mevcut istatistikleri getir veya oluştur
            stats, created = AnonymousStats.objects.get_or_create(
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

            # Test sonucuna göre istatistikleri güncelle
            stats.total_tests_taken += 1
            stats.total_correct_answers += exam_result.correct_answers
            stats.total_wrong_answers += exam_result.wrong_answers
            stats.total_time_spent += exam_result.time_taken or timedelta(0)
            stats.last_test_date = exam_result.created_at

            # Skor hesapla
            total_answers = exam_result.correct_answers + exam_result.wrong_answers
            current_score = (exam_result.correct_answers / total_answers * 100) if total_answers > 0 else 0

            # En yüksek skoru güncelle
            if current_score > stats.highest_score:
                stats.highest_score = current_score

            # Ortalama skoru güncelle
            if stats.total_tests_taken > 0:
                total_correct = stats.total_correct_answers
                total_answered = stats.total_correct_answers + stats.total_wrong_answers
                stats.average_score = (total_correct / total_answered * 100) if total_answered > 0 else 0

            # Streak hesapla
            cls._update_streak(stats, current_score >= 70.0)  # 70% üzeri başarılı sayılır

            # Konu bazında performansı güncelle
            cls._update_topic_performance(anonymous_user, exam_result)

            # Zamana bağlı performansı güncelle
            cls._update_time_performance(anonymous_user, exam_result)

            stats.save()
            logger.info(f"İstatistikler güncellendi: User={anonymous_user.id}, Score={current_score:.1f}%")

        except Exception as e:
            logger.error(f"İstatistik güncelleme hatası: {e}")

    @classmethod
    def _update_streak(cls, stats: AnonymousStats, is_successful: bool) -> None:
        """
        Streak (seri) takibi
        """
        if is_successful:
            stats.current_streak += 1
            if stats.current_streak > stats.best_streak:
                stats.best_streak = stats.current_streak
        else:
            stats.current_streak = 0

    @classmethod
    def _update_topic_performance(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> None:
        """
        Konu bazında performans takibi
        """
        try:
            # Testin konularını al
            session = exam_result.session
            if not session:
                return

            # Her bir soru için konu performansını güncelle
            questions = session.questions.all()
            correct_answers = set(exam_result.correct_answers_list or [])

            for question in questions:
                topic = question.topic
                if not topic:
                    continue

                is_correct = question.id in correct_answers

                # Konu performansını güncelle (Cache'de tut)
                cache_key = f"topic_perf_{anonymous_user.id}_{topic.id}"
                topic_data = cache.get(cache_key, {
                    'total_attempts': 0,
                    'correct_attempts': 0,
                    'accuracy_rate': 0.0
                })

                topic_data['total_attempts'] += 1
                if is_correct:
                    topic_data['correct_attempts'] += 1

                topic_data['accuracy_rate'] = (
                    topic_data['correct_attempts'] / topic_data['total_attempts'] * 100
                )

                cache.set(cache_key, topic_data, timeout=cls.CACHE_TIMEOUT_LONG)

        except Exception as e:
            logger.error(f"Konu performans güncelleme hatası: {e}")

    @classmethod
    def _update_time_performance(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> None:
        """
        Zamana bağlı performans takibi
        """
        try:
            # Günlük performans cache'i
            today = exam_result.created_at.date()
            cache_key = f"daily_perf_{anonymous_user.id}_{today}"

            daily_data = cache.get(cache_key, {
                'tests_taken': 0,
                'total_score': 0.0,
                'total_time': timedelta(0),
                'average_score': 0.0
            })

            # Güncel verileri ekle
            daily_data['tests_taken'] += 1

            total_answers = exam_result.correct_answers + exam_result.wrong_answers
            score = (exam_result.correct_answers / total_answers * 100) if total_answers > 0 else 0
            daily_data['total_score'] += score
            daily_data['total_time'] += exam_result.time_taken or timedelta(0)

            # Ortalamaları hesapla
            daily_data['average_score'] = daily_data['total_score'] / daily_data['tests_taken']

            # Cache'e kaydet (1 gün sakla)
            cache.set(cache_key, daily_data, timeout=86400)

        except Exception as e:
            logger.error(f"Zamana bağlı performans güncelleme hatası: {e}")

    @classmethod
    def get_user_performance_overview(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Kullanıcı performans özetini al
        """
        try:
            cache_key = f"perf_overview_{anonymous_user.id}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            stats = anonymous_user.stats
            if not stats:
                return cls._get_empty_performance_overview()

            # Son 7 günün performansı
            week_ago = timezone.now() - timedelta(days=7)
            recent_sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                created_at__gte=week_ago,
                status='completed'
            ).select_related('result')

            # Haftalık istatistikler
            week_stats = cls._calculate_period_statistics(recent_sessions)

            # Gelişim trendi
            improvement_trend = cls._calculate_improvement_trend(anonymous_user)

            # Güçlü ve zayıf konular
            strong_topics, weak_topics = cls._get_topic_strengths(anonymous_user)

            # Performans tahmini
            performance_prediction = cls._predict_performance(anonymous_user)

            overview = {
                'basic_stats': {
                    'total_tests': stats.total_tests_taken,
                    'average_score': round(stats.average_score, 1),
                    'highest_score': round(stats.highest_score, 1),
                    'current_streak': stats.current_streak,
                    'best_streak': stats.best_streak,
                    'total_time_hours': stats.total_time_spent.total_seconds() / 3600,
                },
                'weekly_performance': week_stats,
                'improvement_trend': improvement_trend,
                'topic_analysis': {
                    'strong_topics': strong_topics,
                    'weak_topics': weak_topics
                },
                'performance_prediction': performance_prediction,
                'last_updated': timezone.now().isoformat()
            }

            # Cache'e kaydet
            cache.set(cache_key, overview, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return overview

        except Exception as e:
            logger.error(f"Performans özeti alma hatası: {e}")
            return cls._get_empty_performance_overview()

    @classmethod
    def get_detailed_progress_chart(cls, anonymous_user: AnonymousUser, period: str = 'weekly') -> List[Dict]:
        """
        Detaylı ilerleme grafiği verileri
        """
        try:
            cache_key = f"progress_chart_{anonymous_user.id}_{period}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            # Tarih aralığını belirle
            if period == cls.PERIOD_DAILY:
                start_date = timezone.now() - timedelta(days=30)
                date_format = '%Y-%m-%d'
            elif period == cls.PERIOD_WEEKLY:
                start_date = timezone.now() - timedelta(weeks=12)
                date_format = '%Y-W%U'
            elif period == cls.PERIOD_MONTHLY:
                start_date = timezone.now() - timedelta(days=365)
                date_format = '%Y-%m'
            else:  # all_time
                start_date = None
                date_format = '%Y-%m'

            # Verileri al
            sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                status='completed'
            ).select_related('result')

            if start_date:
                sessions = sessions.filter(created_at__gte=start_date)

            # Tarihe göre grupla
            progress_data = {}
            for session in sessions:
                date_key = session.created_at.strftime(date_format)

                if date_key not in progress_data:
                    progress_data[date_key] = {
                        'date': date_key,
                        'test_count': 0,
                        'total_score': 0.0,
                        'total_time': timedelta(0),
                        'correct_answers': 0,
                        'wrong_answers': 0,
                        'average_score': 0.0
                    }

                result = session.result
                if result:
                    progress_data[date_key]['test_count'] += 1

                    total_answers = result.correct_answers + result.wrong_answers
                    score = (result.correct_answers / total_answers * 100) if total_answers > 0 else 0
                    progress_data[date_key]['total_score'] += score
                    progress_data[date_key]['total_time'] += result.time_taken or timedelta(0)
                    progress_data[date_key]['correct_answers'] += result.correct_answers
                    progress_data[date_key]['wrong_answers'] += result.wrong_answers

            # Ortalamaları hesapla
            for data in progress_data.values():
                if data['test_count'] > 0:
                    data['average_score'] = round(data['total_score'] / data['test_count'], 1)
                    data['total_time_minutes'] = data['total_time'].total_seconds() / 60
                    data['accuracy_rate'] = (
                        data['correct_answers'] / (data['correct_answers'] + data['wrong_answers']) * 100
                        if (data['correct_answers'] + data['wrong_answers']) > 0 else 0
                    )

            # Sırala ve listeye çevir
            chart_data = sorted(progress_data.values(), key=lambda x: x['date'])

            # Cache'e kaydet
            cache.set(cache_key, chart_data, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return chart_data

        except Exception as e:
            logger.error(f"İlerleme grafiği verileri hatası: {e}")
            return []

    @classmethod
    def get_topic_wise_analysis(cls, anonymous_user: AnonymousUser) -> Dict[str, List[Dict]]:
        """
        Konu bazında detaylı analiz
        """
        try:
            cache_key = f"topic_analysis_{anonymous_user.id}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            # Kullanıcının çözdüğü tüm soruları al
            user_sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                status='completed'
            ).prefetch_related('questions__result', 'result')

            topic_performance = {}

            for session in user_sessions:
                result = session.result
                if not result:
                    continue

                correct_answers = set(result.correct_answers_list or [])
                questions = session.questions.all()

                for question in questions:
                    topic = question.topic
                    if not topic:
                        continue

                    topic_name = topic.name
                    if topic_name not in topic_performance:
                        topic_performance[topic_name] = {
                            'topic': topic_name,
                            'total_questions': 0,
                            'correct_answers': 0,
                            'wrong_answers': 0,
                            'accuracy_rate': 0.0,
                            'latest_performance': []
                        }

                    topic_performance[topic_name]['total_questions'] += 1

                    if question.id in correct_answers:
                        topic_performance[topic_name]['correct_answers'] += 1
                    else:
                        topic_performance[topic_name]['wrong_answers'] += 1

                    # Son performans kaydı
                    topic_performance[topic_name]['latest_performance'].append({
                        'date': session.created_at.isoformat(),
                        'correct': question.id in correct_answers
                    })

            # Doğruluk oranlarını hesapla
            for topic_data in topic_performance.values():
                if topic_data['total_questions'] > 0:
                    topic_data['accuracy_rate'] = round(
                        topic_data['correct_answers'] / topic_data['total_questions'] * 100, 1
                    )

            # Konuları sınıflandır
            strong_topics = []
            moderate_topics = []
            weak_topics = []

            for topic_data in topic_performance.values():
                accuracy = topic_data['accuracy_rate']
                if accuracy >= 80:
                    strong_topics.append(topic_data)
                elif accuracy >= 60:
                    moderate_topics.append(topic_data)
                else:
                    weak_topics.append(topic_data)

            # Sırala
            strong_topics.sort(key=lambda x: x['accuracy_rate'], reverse=True)
            weak_topics.sort(key=lambda x: x['accuracy_rate'])

            analysis = {
                'strong_topics': strong_topics,
                'moderate_topics': moderate_topics,
                'weak_topics': weak_topics,
                'total_topics': len(topic_performance)
            }

            # Cache'e kaydet
            cache.set(cache_key, analysis, timeout=cls.CACHE_TIMEOUT_LONG)
            return analysis

        except Exception as e:
            logger.error(f"Konu analizi hatası: {e}")
            return {'strong_topics': [], 'moderate_topics': [], 'weak_topics': [], 'total_topics': 0}

    @classmethod
    def get_learning_recommendations(cls, anonymous_user: AnonymousUser) -> List[Dict[str, Any]]:
        """
        Kişiselleştirilmiş öğrenme önerileri
        """
        try:
            cache_key = f"recommendations_{anonymous_user.id}"
            cached_data = cache.get(cache_key)

            if cached_data:
                return cached_data

            recommendations = []

            # Performans verilerini al
            performance = cls.get_user_performance_overview(anonymous_user)
            topic_analysis = cls.get_topic_wise_analysis(anonymous_user)

            # Zayıf konular için öneriler
            for weak_topic in topic_analysis['weak_topics'][:3]:
                recommendations.append({
                    'type': 'topic_improvement',
                    'priority': 'high',
                    'title': f"{weak_topic['topic']} konusunu çalış",
                    'description': f"Bu konuda {weak_topic['accuracy_rate']} oranında başarılısın. Daha fazla pratik yapmalısın.",
                    'action_text': 'Konuyu çalış',
                    'action_url': f'/questions?topic={weak_topic["topic"]}',
                    'topic': weak_topic['topic']
                })

            # Günlük test hedefi
            if performance['basic_stats']['total_tests'] < 5:
                recommendations.append({
                    'type': 'daily_goal',
                    'priority': 'medium',
                    'title': 'Günlük test hedefini tamamla',
                    'description': 'Her gün en az 1 test çözerek alışkanlık kazan.',
                    'action_text': 'Test başlat',
                    'action_url': '/quick-test'
                })

            # Streak motivasyonu
            if performance['basic_stats']['current_streak'] > 0:
                recommendations.append({
                    'type': 'streak_motivation',
                    'priority': 'low',
                    'title': f"{performance['basic_stats']['current_streak']} günlük serin var!",
                    'description': 'Harika gidiyorsun! Serini kaybetmemek için devam et.',
                    'action_text': 'Test çöz',
                    'action_url': '/quick-test'
                })

            # Zaman yönetimi
            avg_time_per_question = cls._calculate_average_time_per_question(anonymous_user)
            if avg_time_per_question > 90:  # 90 saniyeden fazla
                recommendations.append({
                    'type': 'time_management',
                    'priority': 'medium',
                    'title': 'Zaman yönetimini iyileştir',
                    'description': f"Ortalama {avg_time_per_question:.0f} saniyede bir soru çözüyorsun. Daha hızlı olmaya çalış.",
                    'action_text': 'Zamanlı test',
                    'action_url': '/quick-test?timer=strict'
                })

            # Cache'e kaydet
            cache.set(cache_key, recommendations, timeout=cls.CACHE_TIMEOUT_SHORT)
            return recommendations

        except Exception as e:
            logger.error(f"Öğrenme önerileri hatası: {e}")
            return []

    @classmethod
    def _calculate_period_statistics(cls, sessions) -> Dict[str, Any]:
        """
        Belirli bir dönemdeki istatistikleri hesapla
        """
        total_tests = sessions.count()
        if total_tests == 0:
            return {
                'test_count': 0,
                'average_score': 0.0,
                'total_time': 0,
                'improvement': 0.0
            }

        total_score = 0.0
        total_time = timedelta(0)
        scores = []

        for session in sessions:
            result = session.result
            if result:
                total_answers = result.correct_answers + result.wrong_answers
                if total_answers > 0:
                    score = result.correct_answers / total_answers * 100
                    total_score += score
                    scores.append(score)
                    total_time += result.time_taken or timedelta(0)

        average_score = total_score / total_tests if total_tests > 0 else 0

        # İyileşme trendi
        improvement = 0.0
        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            improvement = second_avg - first_avg

        return {
            'test_count': total_tests,
            'average_score': round(average_score, 1),
            'total_time_minutes': total_time.total_seconds() / 60,
            'improvement': round(improvement, 1)
        }

    @classmethod
    def _calculate_improvement_trend(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        İyileşme trendini hesapla
        """
        try:
            # Son 30 testi al
            recent_sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                status='completed'
            ).select_related('result').order_by('-created_at')[:30]

            if len(recent_sessions) < 5:
                return {'trend': 'insufficient_data', 'percentage': 0.0}

            scores = []
            for session in recent_sessions:
                result = session.result
                if result:
                    total_answers = result.correct_answers + result.wrong_answers
                    if total_answers > 0:
                        score = result.correct_answers / total_answers * 100
                        scores.append(score)

            if len(scores) < 5:
                return {'trend': 'insufficient_data', 'percentage': 0.0}

            # İlk 10 ve son 10 testin ortalamasını karşılaştır
            recent_scores = scores[:10]
            older_scores = scores[-10:] if len(scores) >= 20 else scores[10:]

            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)

            improvement = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0

            if improvement > 5:
                trend = 'improving'
            elif improvement < -5:
                trend = 'declining'
            else:
                trend = 'stable'

            return {
                'trend': trend,
                'percentage': round(improvement, 1),
                'recent_average': round(recent_avg, 1),
                'older_average': round(older_avg, 1)
            }

        except Exception as e:
            logger.error(f"İyileşme trendi hesaplama hatası: {e}")
            return {'trend': 'error', 'percentage': 0.0}

    @classmethod
    def _get_topic_strengths(cls, anonymous_user: AnonymousUser) -> Tuple[List, List]:
        """
        Güçlü ve zayıf konuları belirle
        """
        try:
            # Cache'deki konu performans verilerini al
            strong_topics = []
            weak_topics = []

            # Tüm konu cache anahtarlarını bul
            for cache_key in cache.keys(f"topic_perf_{anonymous_user.id}_*"):
                topic_data = cache.get(cache_key)
                if topic_data:
                    # Topic ID'sini al
                    topic_id = cache_key.split('_')[-1]
                    try:
                        from quiz.models import Topic
                        topic = Topic.objects.get(id=topic_id)

                        topic_info = {
                            'topic': topic.name,
                            'accuracy_rate': round(topic_data['accuracy_rate'], 1),
                            'total_attempts': topic_data['total_attempts']
                        }

                        if topic_data['accuracy_rate'] >= 80:
                            strong_topics.append(topic_info)
                        elif topic_data['accuracy_rate'] < 60:
                            weak_topics.append(topic_info)

                    except Topic.DoesNotExist:
                        continue

            # Sırala
            strong_topics.sort(key=lambda x: x['accuracy_rate'], reverse=True)
            weak_topics.sort(key=lambda x: x['accuracy_rate'])

            return strong_topics[:5], weak_topics[:5]

        except Exception as e:
            logger.error(f"Konu güç analizi hatası: {e}")
            return [], []

    @classmethod
    def _predict_performance(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Gelecek performansını tahmin et
        """
        try:
            stats = anonymous_user.stats
            if not stats or stats.total_tests_taken < 3:
                return {'prediction': 'insufficient_data', 'confidence': 0.0}

            # Son performans trendini al
            trend_data = cls._calculate_improvement_trend(anonymous_user)

            # Basit lineer tahmin
            current_avg = stats.average_score
            trend_percentage = trend_data['percentage'] / 100

            # Bir sonraki test için tahmin
            predicted_score = current_avg * (1 + trend_percentage * 0.1)

            # Güven skoru
            confidence = min(stats.total_tests_taken / 10.0, 1.0)  # 10 testten sonra %100 güven

            return {
                'prediction': 'improving' if trend_percentage > 0.02 else 'stable' if trend_percentage > -0.02 else 'declining',
                'predicted_score': round(predicted_score, 1),
                'confidence': round(confidence, 2),
                'trend_strength': abs(trend_percentage)
            }

        except Exception as e:
            logger.error(f"Performans tahmini hatası: {e}")
            return {'prediction': 'error', 'confidence': 0.0}

    @classmethod
    def _calculate_average_time_per_question(cls, anonymous_user: AnonymousUser) -> float:
        """
        Soru başına ortalama süreyi hesapla
        """
        try:
            recent_sessions = TempExamSession.objects.filter(
                anonymous_user=anonymous_user,
                status='completed'
            ).select_related('result').order_by('-created_at')[:10]

            total_time = timedelta(0)
            total_questions = 0

            for session in recent_sessions:
                result = session.result
                if result and result.time_taken:
                    total_time += result.time_taken
                    total_questions += session.questions.count()

            if total_questions > 0:
                return total_time.total_seconds() / total_questions
            else:
                return 0.0

        except Exception as e:
            logger.error(f"Ortalama süre hesaplama hatası: {e}")
            return 0.0

    @classmethod
    def _get_empty_performance_overview(cls) -> Dict[str, Any]:
        """
        Boş performans özeti döndür
        """
        return {
            'basic_stats': {
                'total_tests': 0,
                'average_score': 0.0,
                'highest_score': 0.0,
                'current_streak': 0,
                'best_streak': 0,
                'total_time_hours': 0.0,
            },
            'weekly_performance': {
                'test_count': 0,
                'average_score': 0.0,
                'total_time_minutes': 0,
                'improvement': 0.0
            },
            'improvement_trend': {
                'trend': 'no_data',
                'percentage': 0.0
            },
            'topic_analysis': {
                'strong_topics': [],
                'weak_topics': []
            },
            'performance_prediction': {
                'prediction': 'no_data',
                'confidence': 0.0
            },
            'last_updated': timezone.now().isoformat()
        }

    @classmethod
    def clear_user_cache(cls, anonymous_user: AnonymousUser) -> None:
        """
        Kullanıcıya ait tüm istatistik cache'ini temizle
        """
        try:
            # Tüm cache anahtarlarını temizle
            cache_keys = [
                f"perf_overview_{anonymous_user.id}",
                f"progress_chart_{anonymous_user.id}_daily",
                f"progress_chart_{anonymous_user.id}_weekly",
                f"progress_chart_{anonymous_user.id}_monthly",
                f"topic_analysis_{anonymous_user.id}",
                f"recommendations_{anonymous_user.id}"
            ]

            for key in cache_keys:
                cache.delete(key)

            # Konu performans cache'lerini temizle
            topic_keys = cache.keys(f"topic_perf_{anonymous_user.id}_*")
            for key in topic_keys:
                cache.delete(key)

            # Günlük performans cache'lerini temizle
            daily_keys = cache.keys(f"daily_perf_{anonymous_user.id}_*")
            for key in daily_keys:
                cache.delete(key)

            logger.info(f"Kullanıcı cache temizlendi: {anonymous_user.id}")

        except Exception as e:
            logger.error(f"Cache temizleme hatası: {e}")

    @classmethod
    def export_user_statistics(cls, anonymous_user: AnonymousUser, format: str = 'json') -> Dict[str, Any]:
        """
        Kullanıcı istatistiklerini dışa aktar
        """
        try:
            # Tüm istatistik verilerini topla
            performance = cls.get_user_performance_overview(anonymous_user)
            progress_chart = cls.get_detailed_progress_chart(anonymous_user, 'all_time')
            topic_analysis = cls.get_topic_wise_analysis(anonymous_user)
            recommendations = cls.get_learning_recommendations(anonymous_user)

            export_data = {
                'user_id': anonymous_user.id,
                'export_date': timezone.now().isoformat(),
                'performance_overview': performance,
                'progress_chart': progress_chart,
                'topic_analysis': topic_analysis,
                'recommendations': recommendations,
                'export_format': format
            }

            return export_data

        except Exception as e:
            logger.error(f"İstatistik dışa aktarma hatası: {e}")
            return {}