import json
import logging
import random
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter

from django.db import transaction
from django.db.models import Count, Q, F, Avg, Max, Min
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from ..models import (
    Question, Subject, Topic, TempExamSession,
    UserQuestionHistory, UserPerformanceMetrics
)

logger = logging.getLogger(__name__)


class OptimizedQuestionSelector:
    """
    Yüksek performanslı, Redis cache destekli akıllı soru seçim servisi

    Özellikler:
    - Redis cache ile hızlı erişim
    - Database query optimizasyonu
    - Performans metrikleri takibi
    - Konu ve zorluk dengesi
    - Öğrenvci bazında soru tekrarı önleme
    """

    def __init__(self, cache_timeout: int = 3600):
        """
        Initialize optimized question selector

        Args:
            cache_timeout (int): Cache timeout in seconds (default: 1 hour)
        """
        self.cache_timeout = cache_timeout

        # Redis cache keys
        self.CACHE_PREFIX = "question_selection"
        self.USER_HISTORY_KEY = f"{self.CACHE_PREFIX}:user_history"
        self.USER_STATS_KEY = f"{self.CACHE_PREFIX}:user_stats"
        self.AVAILABLE_QUESTIONS_KEY = f"{self.CACHE_PREFIX}:available_questions"
        self.PERFORMANCE_TRENDS_KEY = f"{self.CACHE_PREFIX}:performance_trends"

        # Question selection parameters
        self.MAX_RETRY_ATTEMPTS = 3
        self.DIVERSITY_THRESHOLD = 0.3  # Minimum topic diversity
        self.DIFFICULTY_ADAPTATION_FACTOR = 0.2

        # Performance thresholds
        self.PERFORMANCE_HISTORY_DAYS = 30
        self.MIN_QUESTIONS_FOR_STATS = 5

    def get_questions_for_user(self, session: TempExamSession, user_identifier: str) -> List[Question]:
        """
        Kullanıcı için optimize edilmiş soru seçimi yapar

        Args:
            session: TempExamSession nesnesi
            user_identifier: Kullanıcı kimliği (session_key, IP, user_id)

        Returns:
            List[Question]: Seçilen sorular
        """
        try:
            start_time = timezone.now()

            # 1. Kullanıcı geçmişini cache'den al
            user_history = self._get_user_history_optimized(user_identifier)
            user_stats = self._get_user_performance_stats(user_identifier)

            # 2. Ders bazında soru gereksinimlerini hesapla
            subject_requirements = self._calculate_adaptive_subject_requirements(
                session, user_stats
            )

            # 3. Seçim stratejisini belirle
            selection_strategy = self._determine_selection_strategy(user_stats, session)

            # 4. Soruları seç
            selected_questions = self._select_questions_with_strategy(
                subject_requirements, user_history, selection_strategy, session
            )

            # 5. Kalibrasyon ve optimizasyon
            selected_questions = self._apply_final_optimizations(
                selected_questions, user_stats, session
            )

            # 6. Cache'e yeni geçmişi kaydet
            self._cache_user_questions(user_identifier, selected_questions)

            # 7. Asenkron olarak database'e yaz
            self._async_save_user_history(user_identifier, selected_questions, session)

            processing_time = (timezone.now() - start_time).total_seconds()
            logger.info(f"Selected {len(selected_questions)} questions for {user_identifier} in {processing_time:.3f}s")

            return selected_questions

        except Exception as e:
            logger.error(f"Error in get_questions_for_user for {user_identifier}: {e}")
            # Fallback: Basit rastgele seçim
            return self._fallback_question_selection(session, user_identifier)

    def _get_user_history_optimized(self, user_identifier: str) -> Dict:
        """
        Redis cache üzerinden optimize edilmiş kullanıcı geçmişi

        Returns:
            Dict: {
                'seen_question_ids': Set[str],
                'subject_performance': Dict,
                'recent_topics': List,
                'difficulty_preferences': Dict,
                'last_seen': datetime
            }
        """
        cache_key = f"{self.USER_HISTORY_KEY}:{user_identifier}"

        # Cache'den kontrol et
        cached_history = cache.get(cache_key)
        if cached_history:
            return cached_history

        # Database'den al (optimizasyonlu query)
        cutoff_date = timezone.now() - timedelta(days=self.PERFORMANCE_HISTORY_DAYS)

        try:
            history_data = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date
            ).select_related('question', 'question__subject', 'question__topic').aggregate(
                total_questions=Count('id'),
                correct_answers=Count('id', filter=Q(is_correct=True)),
                avg_time=Avg('time_spent_seconds'),
                avg_difficulty=Avg('question__difficulty'),
                last_seen=Max('answered_at')
            )

            # Subject bazında performans
            subject_stats = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date
            ).values('question__subject__name', 'question__subject__code').annotate(
                subject_total=Count('id'),
                subject_correct=Count('id', filter=Q(is_correct=True)),
                avg_difficulty=Avg('question__difficulty')
            )

            # Konu geçmişi
            topic_history = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date,
                question__topic__isnull=False
            ).values_list('question__topic__name', flat=True).distinct()

            # Görülen soru ID'leri
            seen_question_ids = set(
                UserQuestionHistory.objects.filter(
                    user_identifier=user_identifier,
                    answered_at__gte=cutoff_date
                ).values_list('question_id', flat=True)
            )

            # Performans verilerini hesapla
            total_questions = history_data['total_questions'] or 0
            correct_answers = history_data['correct_answers'] or 0
            accuracy = correct_answers / total_questions if total_questions > 0 else 0.5

            result = {
                'seen_question_ids': seen_question_ids,
                'subject_performance': {
                    stat['question__subject__code']: {
                        'name': stat['question__subject__name'],
                        'accuracy': stat['subject_correct'] / max(stat['subject_total'], 1),
                        'total_questions': stat['subject_total'],
                        'avg_difficulty': stat['avg_difficulty'] or 3
                    }
                    for stat in subject_stats
                },
                'recent_topics': list(topic_history),
                'difficulty_preferences': self._calculate_difficulty_preferences(
                    history_data['avg_difficulty'] or 3, accuracy
                ),
                'overall_stats': {
                    'total_questions': total_questions,
                    'accuracy': accuracy,
                    'avg_time': history_data['avg_time'] or 60,
                    'avg_difficulty': history_data['avg_difficulty'] or 3,
                    'last_seen': history_data['last_seen']
                }
            }

            # Cache'e kaydet
            cache.set(cache_key, result, self.cache_timeout)

            return result

        except Exception as e:
            logger.error(f"Error getting user history for {user_identifier}: {e}")
            return self._get_empty_user_history()

    def _calculate_difficulty_preferences(self, avg_difficulty: float, accuracy: float) -> Dict:
        """
        Kullanıcı performansına göre zorluk tercihlerini hesapla
        """
        # Accuracy'e göre zorluk ayarı
        if accuracy > 0.8:
            # Başarılı kullanıcı - daha zor sorular
            preferred_difficulty = min(avg_difficulty + 0.5, 5)
        elif accuracy < 0.4:
            # Zayıf kullanıcı - daha kolay sorular
            preferred_difficulty = max(avg_difficulty - 0.5, 1)
        else:
            # Orta seviye - benzer zorluk
            preferred_difficulty = avg_difficulty

        # Zorluk dağılımı (normal distribution around preference)
        return {
            'preferred': preferred_difficulty,
            'min_difficulty': max(preferred_difficulty - 1, 1),
            'max_difficulty': min(preferred_difficulty + 1, 5),
            'distribution': {
                1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1
            }
        }

    def _calculate_adaptive_subject_requirements(self, session: TempExamSession, user_stats: Dict) -> Dict[str, int]:
        """
        Kullanıcı performansına göre adaptif ders bazında soru dağılımı
        """
        # Base distribution (TYT/AYT and branch specific)
        base_requirements = self._get_base_distribution(session.exam_type, session.branch, session.question_count)

        # Performansa göre adaptasyon
        subject_performance = user_stats.get('subject_performance', {})

        adapted_requirements = {}
        for subject_code, base_count in base_requirements.items():
            if subject_code in subject_performance:
                perf = subject_performance[subject_code]
                accuracy = perf['accuracy']

                # Başarısız olduğu derslerde daha fazla soru
                if accuracy < 0.5:
                    adapted_count = int(base_count * 1.3)
                elif accuracy > 0.8:
                    adapted_count = int(base_count * 0.9)
                else:
                    adapted_count = base_count

                adapted_requirements[subject_code] = adapted_count
            else:
                adapted_requirements[subject_code] = base_count

        # Toplam soru sayısını koru
        total_adapted = sum(adapted_requirements.values())
        if total_adapted != session.question_count:
            # Orantılı olarak ayarla
            ratio = session.question_count / total_adapted
            adapted_requirements = {
                code: int(count * ratio)
                for code, count in adapted_requirements.items()
            }

            # Kalan soruları ekle
            remaining = session.question_count - sum(adapted_requirements.values())
            if remaining > 0:
                # En çok ihtiyacı olan derse ekle
                weakest_subject = min(
                    subject_performance.items(),
                    key=lambda x: x[1]['accuracy']
                )[0] if subject_performance else list(adapted_requirements.keys())[0]
                adapted_requirements[weakest_subject] += remaining

        return adapted_requirements

    def _get_base_distribution(self, exam_type: str, branch: str, total_questions: int) -> Dict[str, int]:
        """
        Sınav tipi ve alana göre temel soru dağılımı
        """
        distributions = {
            "TYT": {
                "SAY": {"MAT": 14, "FIZ": 4, "KIM": 4, "BIO": 4, "TR": 14, "TAR": 3, "COG": 3},
                "EA":  {"MAT": 14, "FIZ": 4, "KIM": 4, "BIO": 4, "TR": 14, "TAR": 3, "COG": 3},
                "SOZ": {"MAT": 14, "FIZ": 2, "KIM": 2, "BIO": 3, "TR": 14, "TAR": 4, "COG": 3}
            },
            "AYT": {
                "SAY": {"MAT": 13, "FIZ": 7, "KIM": 7, "BIO": 6},
                "EA":  {"MAT": 8, "TR": 8, "TAR": 3, "COG": 3, "INK": 2, "FEL": 2},
                "SOZ": {"TR": 8, "TAR": 3, "COG": 2, "FEL": 4, "INK": 7}
            }
        }

        base_dist = distributions.get(exam_type, {}).get(branch, {})

        if not base_dist:
            return {"MAT": total_questions}

        # Scale to requested total
        base_total = sum(base_dist.values())
        if base_total == total_questions:
            return base_dist

        # Proportional scaling
        ratio = total_questions / base_total
        scaled_dist = {
            subject: max(1, int(count * ratio))
            for subject, count in base_dist.items()
        }

        # Adjust to match exactly total_questions
        scaled_total = sum(scaled_dist.values())
        if scaled_total != total_questions:
            diff = total_questions - scaled_total
            if diff > 0:
                # Add to subjects with highest counts
                sorted_subjects = sorted(scaled_dist.items(), key=lambda x: x[1], reverse=True)
                for i in range(diff):
                    if i < len(sorted_subjects):
                        subject = sorted_subjects[i][0]
                        scaled_dist[subject] += 1
            else:
                # Remove from subjects with lowest counts
                sorted_subjects = sorted(scaled_dist.items(), key=lambda x: x[1])
                for i in range(-diff):
                    if i < len(sorted_subjects) and scaled_dist[sorted_subjects[i][0]] > 1:
                        subject = sorted_subjects[i][0]
                        scaled_dist[subject] -= 1

        return scaled_dist

    def _determine_selection_strategy(self, user_stats: Dict, session: TempExamSession) -> Dict:
        """
        Kullanıcı profiline göre seçim stratejisi belirle
        """
        overall_stats = user_stats.get('overall_stats', {})
        total_questions = overall_stats.get('total_questions', 0)
        accuracy = overall_stats.get('accuracy', 0.5)

        strategy = {
            'type': 'balanced',
            'topic_diversity_weight': 0.3,
            'difficulty_variation': True,
            'prefer_new_topics': True,
            'avoid_recent_questions': True,
            'time_based_weighting': True
        }

        if total_questions < 5:
            # Yeni kullanıcı - temel sorular
            strategy.update({
                'type': 'beginner',
                'topic_diversity_weight': 0.5,
                'difficulty_variation': False,
                'prefer_new_topics': True,
                'avoid_recent_questions': False
            })
        elif accuracy > 0.8:
            # İleri seviye kullanıcı - challenging sorular
            strategy.update({
                'type': 'advanced',
                'topic_diversity_weight': 0.2,
                'difficulty_variation': True,
                'prefer_new_topics': False,
                'avoid_recent_questions': True
            })
        elif accuracy < 0.4:
            # Zayıf kullanıcı - destekleyici sorular
            strategy.update({
                'type': 'supportive',
                'topic_diversity_weight': 0.4,
                'difficulty_variation': False,
                'prefer_new_topics': True,
                'avoid_recent_questions': False
            })

        return strategy

    def _select_questions_with_strategy(
        self,
        subject_requirements: Dict[str, int],
        user_history: Dict,
        strategy: Dict,
        session: TempExamSession
    ) -> List[Question]:
        """
        Stratejiye göre soru seçimi
        """
        seen_questions = user_history.get('seen_question_ids', set())
        subject_performance = user_history.get('subject_performance', {})
        difficulty_prefs = user_history.get('difficulty_preferences', {})

        selected_questions = []

        for subject_code, required_count in subject_requirements.items():
            try:
                subject = Subject.objects.get(code=subject_code)

                # Bu ders için optimize edilmiş soru seçimi
                subject_questions = self._select_subject_questions_optimized(
                    subject=subject,
                    required_count=required_count,
                    excluded_question_ids=seen_questions,
                    subject_performance=subject_performance.get(subject_code, {}),
                    difficulty_preferences=difficulty_prefs,
                    strategy=strategy
                )

                selected_questions.extend(subject_questions)

            except Subject.DoesNotExist:
                logger.warning(f"Subject {subject_code} not found")
                continue

        return selected_questions

    def _select_subject_questions_optimized(
        self,
        subject: Subject,
        required_count: int,
        excluded_question_ids: Set[str],
        subject_performance: Dict,
        difficulty_preferences: Dict,
        strategy: Dict
    ) -> List[Question]:
        """
        Optimize edilmiş ders bazında soru seçimi
        """
        try:
            # Zorluk aralığını belirle
            min_diff = difficulty_preferences.get('min_difficulty', 1)
            max_diff = difficulty_preferences.get('max_difficulty', 5)

            # Ana query - optimize edilmiş
            available_query = Question.objects.filter(
                subject=subject,
                difficulty__gte=min_diff,
                difficulty__lte=max_diff,
                is_duplicate=False  # Kopya olmayan sorular
            )

            # Exclude seen questions
            if excluded_question_ids:
                available_query = available_query.exclude(id__in=excluded_question_ids)

            # Available count kontrol
            available_count = available_query.count()

            if available_count < required_count:
                # Yetersiz soru varsa kriterleri gevşet
                logger.warning(f"Insufficient questions for {subject.name}: {available_count}/{required_count}")

                # Kriterleri gevşet
                fallback_query = Question.objects.filter(
                    subject=subject,
                    is_duplicate=False
                )

                if excluded_question_ids:
                    fallback_query = fallback_query.exclude(id__in=excluded_question_ids)

                fallback_count = fallback_query.count()

                if fallback_count >= required_count:
                    selected_query = fallback_query
                else:
                    # Son çare: exclude kaldır
                    all_questions = Question.objects.filter(
                        subject=subject
                    ).order_by('?')[:required_count]
                    return list(all_questions)
            else:
                selected_query = available_query

            # Konu çeşitliliği uygulama
            if strategy.get('prefer_new_topics', True):
                selected_questions = self._apply_topic_diversity(
                    selected_query, required_count, strategy.get('topic_diversity_weight', 0.3)
                )
            else:
                selected_questions = list(selected_query.order_by('?')[:required_count])

            # Zorluk çeşitliliği
            if strategy.get('difficulty_variation', True) and len(selected_questions) > 1:
                selected_questions = self._ensure_difficulty_variation(selected_questions)

            return selected_questions[:required_count]

        except Exception as e:
            logger.error(f"Error selecting questions for subject {subject.name}: {e}")
            # Fallback: random selection
            return list(
                Question.objects.filter(
                    subject=subject
                ).exclude(id__in=excluded_question_ids).order_by('?')[:required_count]
            )

    def _apply_topic_diversity(self, queryset, required_count: int, diversity_weight: float) -> List[Question]:
        """
        Konu çeşitliliği sağla
        """
        try:
            # Konu dağılımını al
            topic_distribution = (
                queryset.values('topic__name')
                .annotate(count=Count('id'))
                .order_by('-count')
            )

            if len(topic_distribution) <= 1:
                # Tek konu varsa çeşitlilik sağlanamaz
                return list(queryset.order_by('?')[:required_count])

            # Çeşitlilik sayısını hesapla
            diversity_count = max(1, int(required_count * diversity_weight))

            # Her konudan en az bir soru seç
            diverse_questions = []
            topic_questions = {}

            # Soruları konuya göre grupla
            for question in queryset.all():
                topic_name = question.topic.name if question.topic else 'Genel'
                if topic_name not in topic_questions:
                    topic_questions[topic_name] = []
                topic_questions[topic_name].append(question)

            # Her konudan rastgele soru seç
            topics_used = 0
            for topic_name, questions in topic_questions.items():
                if topics_used >= diversity_count:
                    break
                if questions:
                    diverse_questions.append(random.choice(questions))
                    topics_used += 1

            # Kalan soruları rastgele seç
            remaining_needed = required_count - len(diverse_questions)
            if remaining_needed > 0:
                remaining_questions = [
                    q for q in queryset.all()
                    if q not in diverse_questions
                ]
                random.shuffle(remaining_questions)
                diverse_questions.extend(remaining_questions[:remaining_needed])

            return diverse_questions[:required_count]

        except Exception as e:
            logger.error(f"Error applying topic diversity: {e}")
            return list(queryset.order_by('?')[:required_count])

    def _ensure_difficulty_variation(self, questions: List[Question]) -> List[Question]:
        """
        Zorluk çeşitliliği sağla
        """
        if len(questions) <= 2:
            return questions

        # Zorluk dağılımını kontrol et
        difficulties = [q.difficulty for q in questions]
        unique_difficulties = set(difficulties)

        if len(unique_difficulties) >= 3:
            return questions  # Yeterli çeşitlilik var

        # Zorlukları dağıt
        sorted_questions = sorted(questions, key=lambda x: x.difficulty)

        # Basit dağılım: easy, medium, hard pattern
        result = []
        n = len(sorted_questions)

        for i in range(n):
            if i % 3 == 0 and i < n:
                result.append(sorted_questions[i])  # Easy
            elif i % 3 == 1 and i - 1 < n:
                result.append(sorted_questions[i - 1])  # Medium
            elif i - 2 < n:
                result.append(sorted_questions[i - 2])  # Hard

        return result

    def _apply_final_optimizations(
        self,
        questions: List[Question],
        user_stats: Dict,
        session: TempExamSession
    ) -> List[Question]:
        """
        Son optimizasyonları uygula
        """
        if len(questions) != session.question_count:
            # Soru sayısını ayarla
            if len(questions) > session.question_count:
                questions = questions[:session.question_count]
            else:
                # Eksik soruları tamamla
                existing_ids = {q.id for q in questions}
                additional_questions = Question.objects.exclude(
                    id__in=existing_ids
                ).order_by('?')[:session.question_count - len(questions)]
                questions.extend(additional_questions)

        # Random shuffle
        random.shuffle(questions)

        return questions

    def _cache_user_questions(self, user_identifier: str, questions: List[Question]):
        """
        Kullanıcı geçmişini cache'e kaydet
        """
        cache_key = f"{self.USER_HISTORY_KEY}:{user_identifier}"

        # Mevcut cache verisini al
        cached_history = cache.get(cache_key) or self._get_empty_user_history()

        # Yeni soru ID'lerini ekle
        new_question_ids = {q.id for q in questions}
        cached_history['seen_question_ids'].update(new_question_ids)

        # Cache'i güncelle
        cache.set(cache_key, cached_history, self.cache_timeout)

    def _async_save_user_history(
        self,
        user_identifier: str,
        questions: List[Question],
        session: TempExamSession
    ):
        """
        Asenkron olarak kullanıcı geçmişini database'e kaydet
        """
        try:
            from django.db import transaction

            # Bulk create için veri hazırla
            history_records = [
                UserQuestionHistory(
                    user_identifier=user_identifier,
                    question=question,
                    session=session
                )
                for question in questions
            ]

            # Asenkron create
            UserQuestionHistory.objects.bulk_create(
                history_records,
                ignore_conflicts=True,  # Duplicate key varsa ignore et
                batch_size=100
            )

            logger.info(f"Saved {len(history_records)} question history records for {user_identifier}")

        except Exception as e:
            logger.error(f"Error saving user history for {user_identifier}: {e}")

    def _get_empty_user_history(self) -> Dict:
        """
        Boş kullanıcı geçmiği template'i
        """
        return {
            'seen_question_ids': set(),
            'subject_performance': {},
            'recent_topics': [],
            'difficulty_preferences': {
                'preferred': 3,
                'min_difficulty': 1,
                'max_difficulty': 5,
                'distribution': {1: 0.2, 2: 0.2, 3: 0.4, 4: 0.1, 5: 0.1}
            },
            'overall_stats': {
                'total_questions': 0,
                'accuracy': 0.5,
                'avg_time': 60,
                'avg_difficulty': 3,
                'last_seen': None
            }
        }

    def _get_user_performance_stats(self, user_identifier: str) -> Dict:
        """
        Kullanıcı performans istatistiklerini cache'den al
        """
        cache_key = f"{self.USER_STATS_KEY}:{user_identifier}"
        return cache.get(cache_key) or {}

    def _fallback_question_selection(self, session: TempExamSession, user_identifier: str) -> List[Question]:
        """
        Fallback soru seçimi - basit rastgele seçim
        """
        logger.warning(f"Using fallback selection for {user_identifier}")

        try:
            # Mevcut geçmişi al
            history_cache_key = f"{self.USER_HISTORY_KEY}:{user_identifier}"
            cached_history = cache.get(history_cache_key) or self._get_empty_user_history()
            seen_ids = cached_history['seen_question_ids']

            # Rastgele sorular seç
            questions = Question.objects.exclude(
                id__in=seen_ids
            ).order_by('?')[:session.question_count]

            return list(questions)

        except Exception as e:
            logger.error(f"Fallback selection failed: {e}")
            # Son çare: herhangi bir soru
            return list(Question.objects.order_by('?')[:session.question_count])

    def update_user_performance(self, user_identifier: str, question_answers: List[Dict]):
        """
        Kullanıcı performansını güncelle

        Args:
            user_identifier: Kullanıcı kimliği
            question_answers: [
                {'question_id': 'Q123', 'answer_given': 'A', 'is_correct': True, 'time_spent': 45}
            ]
        """
        try:
            from django.db import transaction

            with transaction.atomic():
                for answer_data in question_answers:
                    # Update history record
                    UserQuestionHistory.objects.filter(
                        user_identifier=user_identifier,
                        question_id=answer_data['question_id']
                    ).update(
                        is_correct=answer_data['is_correct'],
                        answer_given=answer_data['answer_given'],
                        time_spent_seconds=answer_data.get('time_spent')
                    )

                # Update performance metrics
                self._update_performance_metrics(user_identifier)

                # Clear cache
                self.clear_user_cache(user_identifier)

            logger.info(f"Updated performance for {user_identifier}: {len(question_answers)} answers")

        except Exception as e:
            logger.error(f"Error updating user performance: {e}")

    def _update_performance_metrics(self, user_identifier: str):
        """
        Kullanıcı performans metriklerini güncelle
        """
        try:
            today = date.today()

            # Subject bazında günlük performans
            subject_metrics = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__date=today
            ).values(
                'question__subject'
            ).annotate(
                total_questions=Count('id'),
                correct_answers=Count('id', filter=Q(is_correct=True)),
                avg_time=Avg('time_spent_seconds')
            )

            for metric in subject_metrics:
                UserPerformanceMetrics.objects.update_or_create(
                    user_identifier=user_identifier,
                    subject_id=metric['question__subject'],
                    date=today,
                    defaults={
                        'total_questions': metric['total_questions'],
                        'correct_answers': metric['correct_answers'],
                        'average_time_seconds': metric['avg_time'] or 0
                    }
                )

        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")

    def clear_user_cache(self, user_identifier: str = None):
        """
        Kullanıcı cache'ini temizle
        """
        if user_identifier:
            # Specific user
            cache.delete(f"{self.USER_HISTORY_KEY}:{user_identifier}")
            cache.delete(f"{self.USER_STATS_KEY}:{user_identifier}")
        else:
            # All users - caution with this
            cache.delete_pattern(f"{self.USER_HISTORY_KEY}:*")
            cache.delete_pattern(f"{self.USER_STATS_KEY}:*")

    def get_user_question_analytics(self, user_identifier: str) -> Dict:
        """
        Kullanıcı için detaylı soru analitikleri
        """
        try:
            # Son 30 gün
            cutoff_date = timezone.now() - timedelta(days=30)

            analytics = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date
            ).select_related('question', 'question__subject', 'question__topic').aggregate(
                total_questions=Count('id'),
                correct_answers=Count('id', filter=Q(is_correct=True)),
                avg_time=Avg('time_spent_seconds'),
                unique_subjects=Count('question__subject', distinct=True),
                unique_topics=Count('question__topic', distinct=True),
                first_question=Min('answered_at'),
                last_question=Max('answered_at')
            )

            # Subject breakdown
            subject_breakdown = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date
            ).values(
                'question__subject__name'
            ).annotate(
                subject_total=Count('id'),
                subject_correct=Count('id', filter=Q(is_correct=True)),
                avg_difficulty=Avg('question__difficulty')
            ).order_by('-subject_total')

            # Topic performance
            topic_performance = UserQuestionHistory.objects.filter(
                user_identifier=user_identifier,
                answered_at__gte=cutoff_date,
                question__topic__isnull=False
            ).values(
                'question__topic__name'
            ).annotate(
                topic_total=Count('id'),
                topic_correct=Count('id', filter=Q(is_correct=True))
            ).order_by('-topic_total')

            return {
                'summary': {
                    'total_questions': analytics['total_questions'],
                    'accuracy': analytics['correct_answers'] / max(analytics['total_questions'], 1),
                    'avg_time_per_question': analytics['avg_time'] or 0,
                    'unique_subjects_covered': analytics['unique_subjects'],
                    'unique_topics_covered': analytics['unique_topics'],
                    'study_period_days': (analytics['last_question'] - analytics['first_question']).days if analytics['first_question'] and analytics['last_question'] else 0
                },
                'subject_breakdown': list(subject_breakdown),
                'topic_performance': list(topic_performance),
                'recommendations': self._generate_analytics_recommendations(analytics, subject_breakdown)
            }

        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}

    def _generate_analytics_recommendations(self, analytics: Dict, subject_breakdown) -> List[str]:
        """
        Analitik verilerine göre öneriler oluştur
        """
        recommendations = []

        total_questions = analytics['total_questions'] or 0
        correct_answers = analytics['correct_answers'] or 0
        accuracy = correct_answers / max(total_questions, 1)

        if total_questions < 10:
            recommendations.append("Daha fazla soru çözerek deneyiminizi artırın")

        if accuracy < 0.5:
            recommendations.append("Genel başarınızı artırmak için konu tekrarı yapın")
        elif accuracy > 0.9:
            recommendations.append("Harika performans! Daha zorlu sorularla kendinizi test edin")

        # Zayıf konuları tespit et
        if subject_breakdown:
            worst_subject = min(subject_breakdown, key=lambda x: x['subject_correct'] / max(x['subject_total'], 1))
            worst_accuracy = worst_subject['subject_correct'] / max(worst_subject['subject_total'], 1)

            if worst_accuracy < 0.4:
                recommendations.append(f"{worst_subject['question__subject__name']} dersine daha fazla çalışın")

        return recommendations


# Global instance
optimized_selector = OptimizedQuestionSelector()