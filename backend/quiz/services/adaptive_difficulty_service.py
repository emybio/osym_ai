import logging
import random
from typing import Dict, List, Tuple, Optional, Any
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db.models import Avg, Count, Q, F, StdDev
from collections import defaultdict

from quiz.models import AnonymousUser, AnonymousStats, TempExamSession, TempExamResult, Question, Subject, Topic

logger = logging.getLogger(__name__)


class AdaptiveDifficultyService:
    """Adaptive Difficulty (Uyarlanabilir Zorluk) Servisi"""

    # Cache süreleri
    CACHE_TIMEOUT_SHORT = 300    # 5 dakika
    CACHE_TIMEOUT_MEDIUM = 1800  # 30 dakika
    CACHE_TIMEOUT_LONG = 3600    # 1 saat

    # Zorluk seviyeleri
    DIFFICULTY_LEVELS = {
        1: {'name': 'Çok Kolay', 'target_success_rate': 0.90, 'color': '#10b981'},
        2: {'name': 'Kolay', 'target_success_rate': 0.80, 'color': '#22c55e'},
        3: {'name': 'Orta', 'target_success_rate': 0.70, 'color': '#f59e0b'},
        4: {'name': 'Zor', 'target_success_rate': 0.60, 'color': '#f97316'},
        5: {'name': 'Çok Zor', 'target_success_rate': 0.50, 'color': '#ef4444'}
    }

    # Başarı oranlarına göre zorluk ayarları
    SUCCESS_RATE_ADJUSTMENTS = {
        (0.0, 0.4): -2,   # Çok düşük başarı: Zorluğu 2 seviye düşür
        (0.4, 0.55): -1,  # Düşük başarı: Zorluğu 1 seviye düşür
        (0.55, 0.75): 0,  # Optimal aralık: Zorluğu koru
        (0.75, 0.85): 1,  # Yüksek başarı: Zorluğu 1 seviye artır
        (0.85, 1.0): 2    # Çok yüksek başarı: Zorluğu 2 seviye artır
    }

    # Temel parametreler
    BASE_QUESTION_COUNT = 20
    MIN_DIFFICULTY = 1
    MAX_DIFFICULTY = 5
    OPTIMAL_SUCCESS_RATE = 0.70  # %70 hedef başarı oranı

    @classmethod
    def get_user_difficulty_profile(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Kullanıcının konu bazında zorluk profilini al
        """
        try:
            cache_key = f"difficulty_profile_{anonymous_user.id}"
            cached_profile = cache.get(cache_key)

            if cached_profile:
                return cached_profile

            # TODO: Fix when anonymous_user field is added to TempExamSession
            # Son 10 testi al
            # recent_sessions = TempExamSession.objects.filter(
            #     anonymous_user=anonymous_user,
            #     status='completed'
            # ).select_related('result').order_by('-created_at')[:10]
            recent_sessions = []  # Placeholder until anonymous_user field is added

            if len(recent_sessions) < 2:
                # Yeni kullanıcı için varsayılan profil
                return cls._get_default_difficulty_profile()

            # Konu bazında performans analizi
            subject_difficulties = {}
            topic_difficulties = {}

            for session in recent_sessions:
                result = session.result
                if not result:
                    continue

                # Her sorunun konu ve zorluk bilgisini analiz et
                questions = session.questions.all()
                correct_answers = set(result.correct_answers_list or [])

                for question in questions:
                    subject_code = question.subject
                    topic_name = question.topic
                    difficulty = int(question.difficulty) if question.difficulty else 3
                    is_correct = question.id in correct_answers

                    # Konu bazında takip
                    if subject_code not in subject_difficulties:
                        subject_difficulties[subject_code] = {
                            'total_questions': 0,
                            'correct_answers': 0,
                            'difficulty_attempts': defaultdict(int),
                            'difficulty_correct': defaultdict(int)
                        }

                    subject_difficulties[subject_code]['total_questions'] += 1
                    subject_difficulties[subject_code]['difficulty_attempts'][difficulty] += 1
                    if is_correct:
                        subject_difficulties[subject_code]['correct_answers'] += 1
                        subject_difficulties[subject_code]['difficulty_correct'][difficulty] += 1

                    # Konu bazında takip
                    if topic_name:
                        if topic_name not in topic_difficulties:
                            topic_difficulties[topic_name] = {
                                'total_questions': 0,
                                'correct_answers': 0,
                                'difficulty_attempts': defaultdict(int),
                                'difficulty_correct': defaultdict(int)
                            }

                        topic_difficulties[topic_name]['total_questions'] += 1
                        topic_difficulties[topic_name]['difficulty_attempts'][difficulty] += 1
                        if is_correct:
                            topic_difficulties[topic_name]['correct_answers'] += 1
                            topic_difficulties[topic_name]['difficulty_correct'][difficulty] += 1

            # Optimal zorluk seviyelerini hesapla
            profile = {
                'user_level': cls._calculate_user_level(anonymous_user),
                'subject_difficulties': {},
                'topic_difficulties': {},
                'global_difficulty': 3,
                'confidence_level': 0.5,
                'last_updated': timezone.now().isoformat()
            }

            # Konu bazında zorluk hesapla
            for subject_code, data in subject_difficulties.items():
                if data['total_questions'] >= 3:  # Yeterli veri varsa
                    optimal_difficulty = cls._calculate_optimal_difficulty(data)
                    profile['subject_difficulties'][subject_code] = {
                        'recommended_difficulty': optimal_difficulty,
                        'confidence': cls._calculate_confidence(data),
                        'performance_data': {
                            'total_questions': data['total_questions'],
                            'success_rate': data['correct_answers'] / data['total_questions']
                        }
                    }

            # Konu bazında zorluk hesapla
            for topic_name, data in topic_difficulties.items():
                if data['total_questions'] >= 3:  # Yeterli veri varsa
                    optimal_difficulty = cls._calculate_optimal_difficulty(data)
                    profile['topic_difficulties'][topic_name] = {
                        'recommended_difficulty': optimal_difficulty,
                        'confidence': cls._calculate_confidence(data),
                        'performance_data': {
                            'total_questions': data['total_questions'],
                            'success_rate': data['correct_answers'] / data['total_questions']
                        }
                    }

            # Genel zorluk seviyesini hesapla
            if profile['subject_difficulties']:
                difficulties = [d['recommended_difficulty'] for d in profile['subject_difficulties'].values()]
                profile['global_difficulty'] = round(sum(difficulties) / len(difficulties))

                # Güven seviyesini hesapla
                confidences = [d['confidence'] for d in profile['subject_difficulties'].values()]
                profile['confidence_level'] = sum(confidences) / len(confidences)

            # Cache'e kaydet
            cache.set(cache_key, profile, timeout=cls.CACHE_TIMEOUT_MEDIUM)
            return profile

        except Exception as e:
            logger.error(f"User difficulty profile calculation error: {e}")
            return cls._get_default_difficulty_profile()

    @classmethod
    def generate_adaptive_questions(cls, session: TempExamSession, anonymous_user: AnonymousUser) -> List:
        """
        Kullanıcı performansına göre uyarlanmış soru seti oluştur
        """
        try:
            # Kullanıcının zorluk profilini al
            difficulty_profile = cls.get_user_difficulty_profile(anonymous_user)

            # Mevcut question_distribution'ı al
            from .quick_test_service import generate_quick_test_questions
            original_questions = generate_quick_test_questions(session)

            if not original_questions:
                return []

            # Soruları adaptif şekilde güncelle
            adaptive_questions = cls._adapt_questions_difficulty(
                original_questions,
                session,
                difficulty_profile
            )

            logger.info(f"Generated {len(adaptive_questions)} adaptive questions for user {anonymous_user.id}")
            return adaptive_questions

        except Exception as e:
            logger.error(f"Adaptive question generation error: {e}")
            # Hata durumunda normal soru üretimine geri dön
            from .quick_test_service import generate_quick_test_questions
            return generate_quick_test_questions(session)

    @classmethod
    def _adapt_questions_difficulty(cls, original_questions: List, session: TempExamSession, difficulty_profile: Dict) -> List:
        """
        Orijinal soruların zorluk seviyelerini uyarla
        """
        try:
            # Mevcut soruları temizle (çünkü yenilerini oluşturacağız)
            from quiz.models import TempExamQuestion
            TempExamQuestion.objects.filter(session=session).delete()

            adapted_questions = []
            current_order = 1

            # Soruları konularına göre grupla
            questions_by_subject = {}
            for temp_question in original_questions:
                subject_name = temp_question.subject
                if subject_name not in questions_by_subject:
                    questions_by_subject[subject_name] = []
                questions_by_subject[subject_name].append(temp_question)

            # Her konu için adaptif soru seç
            for subject_name, subject_questions in questions_by_subject.items():
                # Konu kodunu bul
                try:
                    subject = Subject.objects.get(name=subject_name)
                    subject_code = subject.code
                except Subject.DoesNotExist:
                    # Eğer konu bulunamazsa orijinal soruları kullan
                    subject_code = None

                # Bu konu için önerilen zorluk seviyesi
                if subject_code and subject_code in difficulty_profile.get('subject_difficulties', {}):
                    recommended_difficulty = difficulty_profile['subject_difficulties'][subject_code]['recommended_difficulty']
                    confidence = difficulty_profile['subject_difficulties'][subject_code]['confidence']
                else:
                    # Genel zorluk seviyesini kullan
                    recommended_difficulty = difficulty_profile.get('global_difficulty', 3)
                    confidence = 0.5

                # Zorluk varyasyonu ekle (belirli bir seviyede rastgelelik)
                difficulty_range = cls._get_difficulty_range(recommended_difficulty, confidence)

                # Her soru için uygun zorlukta yeni soru seç
                for temp_question in subject_questions:
                    try:
                        # Konu ve zorluk aralığına göre soru ara
                        if subject_code:
                            questions = Question.objects.filter(
                                subject__code=subject_code,
                                difficulty__in=difficulty_range
                            ).exclude(
                                id__in=[q.question_text for q in adapted_questions]
                            ).order_by('?')[:1]
                        else:
                            # Konu bulunamazsa rastgele zorlukta soru seç
                            questions = Question.objects.filter(
                                difficulty__in=difficulty_range
                            ).order_by('?')[:1]

                        if questions.exists():
                            question = questions.first()
                        else:
                            # Uygun soru bulunamazsa en yakın zorlukta soru seç
                            questions = Question.objects.filter(
                                difficulty=max(cls.MIN_DIFFICULTY, min(difficulty_range))
                            ).order_by('?')[:1]
                            question = questions.first() if questions.exists() else None

                        if not question:
                            # Hiç soru bulunamazsa rastgele soru seç
                            questions = Question.objects.order_by('?')[:1]
                            question = questions.first() if questions.exists() else None

                        if question:
                            # Seçenekleri JSON formatına çevir
                            choices = {}
                            for choice in question.choices.all():
                                choices[choice.label] = choice.text

                            # Yeni TempExamQuestion oluştur
                            adapted_temp_question = TempExamQuestion.objects.create(
                                session=session,
                                question_text=question.question_text,
                                options=choices,
                                correct_option=question.correct_answer,
                                subject=question.subject.name,
                                topic=question.topic.name if question.topic else None,
                                difficulty=str(question.difficulty),
                                order=current_order,
                                # Adaptif bilgileri ekle
                                is_adaptive=True,
                                target_difficulty=recommended_difficulty,
                                difficulty_confidence=confidence
                            )
                            adapted_questions.append(adapted_temp_question)
                            current_order += 1

                    except Exception as e:
                        logger.error(f"Error adapting question {temp_question.id}: {e}")
                        # Hata durumunda orijinal soruyu kullan
                        temp_question.order = current_order
                        temp_question.is_adaptive = True
                        temp_question.save()
                        adapted_questions.append(temp_question)
                        current_order += 1

            return adapted_questions

        except Exception as e:
            logger.error(f"Questions difficulty adaptation error: {e}")
            return original_questions

    @classmethod
    def update_difficulty_profile(cls, anonymous_user: AnonymousUser, exam_result: TempExamResult) -> Dict[str, Any]:
        """
        Test sonucuna göre zorluk profilini güncelle
        """
        try:
            # Mevcut profili al
            current_profile = cls.get_user_difficulty_profile(anonymous_user)

            # Cache'i temizle (yeni hesaplama için)
            cache_key = f"difficulty_profile_{anonymous_user.id}"
            cache.delete(cache_key)

            # Güncellenmiş profili al
            updated_profile = cls.get_user_difficulty_profile(anonymous_user)

            # Değişiklikleri analiz et
            changes = cls._analyze_profile_changes(current_profile, updated_profile)

            logger.info(f"Difficulty profile updated for user {anonymous_user.id}: {changes}")
            return {
                'previous_profile': current_profile,
                'current_profile': updated_profile,
                'changes': changes,
                'updated_at': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Difficulty profile update error: {e}")
            return {'error': str(e)}

    @classmethod
    def get_difficulty_recommendations(cls, anonymous_user: AnonymousUser) -> List[Dict[str, Any]]:
        """
        Zorluk tabanlı öğrenme önerileri oluştur
        """
        try:
            profile = cls.get_user_difficulty_profile(anonymous_user)
            recommendations = []

            # Düşük performanslı konular için öneriler
            for subject_code, data in profile.get('subject_difficulties', {}).items():
                performance_data = data.get('performance_data', {})
                success_rate = performance_data.get('success_rate', 0)

                if success_rate < 0.5:  # %50 altında performans
                    recommendations.append({
                        'type': 'difficulty_adjustment',
                        'priority': 'high',
                        'title': f'{subject_code} konusunda zorluk düşürülmesi öneriliyor',
                        'description': f'Mevcut başarı oranınız %{success_rate*100:.1f}. Bu konuda daha kolay sorularla pratik yaparak temelinizi güçlendirebilirsiniz.',
                        'current_difficulty': data['recommended_difficulty'],
                        'suggested_difficulty': max(cls.MIN_DIFFICULTY, data['recommended_difficulty'] - 1),
                        'subject': subject_code
                    })
                elif success_rate > 0.85:  # %85 üstünde performans
                    recommendations.append({
                        'type': 'difficulty_increase',
                        'priority': 'medium',
                        'title': f'{subject_code} konusunda zorluk artırılabilir',
                        'description': f'Mevcut başarı oranınız %{success_rate*100:.1f}. Bu konuda kendinizi zorlayarak daha üst seviyelere çıkabilirsiniz.',
                        'current_difficulty': data['recommended_difficulty'],
                        'suggested_difficulty': min(cls.MAX_DIFFICULTY, data['recommended_difficulty'] + 1),
                        'subject': subject_code
                    })

            # Genel öneriler
            if profile.get('confidence_level', 0) < 0.3:
                recommendations.append({
                    'type': 'more_practice',
                    'priority': 'high',
                    'title': 'Daha fazla pratik yapmanız öneriliyor',
                    'description': 'Sistem henüz öğrenme seviyenizi tam olarak anlayamadı. Daha fazla test çözerek kişiselleştirilmiş öneriler alabilirsiniz.',
                    'action': 'practice_more'
                })

            # Kullanıcı seviyesine göre öneriler
            user_level = profile.get('user_level', 'beginner')
            if user_level == 'beginner':
                recommendations.append({
                    'type': 'foundation_building',
                    'priority': 'high',
                    'title': 'Temel konulara odaklanın',
                    'description': 'Başlangıç seviyesinde olduğunuz için temel konuları pekiştirmeniz öneriliyor. Kolay ve orta seviye sorularla başlayın.',
                    'action': 'focus_on_basics'
                })

            return recommendations

        except Exception as e:
            logger.error(f"Difficulty recommendations error: {e}")
            return []

    @classmethod
    def _calculate_optimal_difficulty(cls, performance_data: Dict) -> int:
        """
        Performans verilerine göre optimal zorluk seviyesi hesapla
        """
        try:
            total_questions = performance_data['total_questions']
            correct_answers = performance_data['correct_answers']
            success_rate = correct_answers / total_questions

            # Her zorluk seviyesindeki performansı analiz et
            difficulty_performance = {}
            for difficulty in range(1, 6):
                attempts = performance_data['difficulty_attempts'].get(difficulty, 0)
                correct = performance_data['difficulty_correct'].get(difficulty, 0)

                if attempts > 0:
                    difficulty_performance[difficulty] = correct / attempts
                else:
                    difficulty_performance[difficulty] = 0

            # En uygun zorluk seviyesini bul
            best_difficulty = 3  # Varsayılan
            best_score = float('inf')

            for difficulty in range(1, 6):
                if difficulty_performance[difficulty] > 0:
                    # Hedef başarı oranına ne kadar yakınsa o kadar iyi
                    deviation = abs(difficulty_performance[difficulty] - cls.OPTIMAL_SUCCESS_RATE)

                    # Deneme sayısını da dikkate al
                    attempts = performance_data['difficulty_attempts'].get(difficulty, 0)
                    confidence = min(attempts / 10, 1.0)  # Maksimum 1.0

                    # Düşük skor (daha iyi) + yüksek güven = daha iyi seçim
                    score = deviation * (2 - confidence)

                    if score < best_score:
                        best_score = score
                        best_difficulty = difficulty

            # Başarı oranına göre son ayar
            if success_rate > 0.8:
                best_difficulty = min(cls.MAX_DIFFICULTY, best_difficulty + 1)
            elif success_rate < 0.5:
                best_difficulty = max(cls.MIN_DIFFICULTY, best_difficulty - 1)

            return best_difficulty

        except Exception as e:
            logger.error(f"Optimal difficulty calculation error: {e}")
            return 3  # Varsayılan orta zorluk

    @classmethod
    def _calculate_confidence(cls, performance_data: Dict) -> float:
        """
        Performans verilerine göre güven seviyesini hesapla
        """
        try:
            total_questions = performance_data['total_questions']

            # Deneme sayısına göre güven seviyesi
            if total_questions < 3:
                return 0.1
            elif total_questions < 5:
                return 0.3
            elif total_questions < 10:
                return 0.5
            elif total_questions < 20:
                return 0.7
            else:
                return 0.9

        except Exception:
            return 0.5

    @classmethod
    def _get_difficulty_range(cls, target_difficulty: int, confidence: float) -> List[int]:
        """
        Hedef zorluk ve güven seviyesine göre zorluk aralığı oluştur
        """
        try:
            # Düşük güven seviyesinde daha geniş aralık
            if confidence < 0.3:
                spread = 2
            elif confidence < 0.7:
                spread = 1
            else:
                spread = 0

            min_diff = max(cls.MIN_DIFFICULTY, target_difficulty - spread)
            max_diff = min(cls.MAX_DIFFICULTY, target_difficulty + spread)

            return list(range(min_diff, max_diff + 1))

        except Exception:
            return [3]  # Varsayılan

    @classmethod
    def _calculate_user_level(cls, anonymous_user: AnonymousUser) -> str:
        """
        Kullanıcı seviyesini hesapla
        """
        try:
            stats = anonymous_user.stats
            if not stats:
                return 'beginner'

            # Test sayısına göre seviye belirle
            if stats.total_tests_taken < 5:
                return 'beginner'
            elif stats.total_tests_taken < 20:
                return 'intermediate'
            elif stats.total_tests_taken < 50:
                return 'advanced'
            else:
                return 'expert'

        except Exception:
            return 'beginner'

    @classmethod
    def _get_default_difficulty_profile(cls) -> Dict[str, Any]:
        """
        Yeni kullanıcı için varsayılan zorluk profili
        """
        return {
            'user_level': 'beginner',
            'subject_difficulties': {},
            'topic_difficulties': {},
            'global_difficulty': 3,  # Orta zorluk
            'confidence_level': 0.1,
            'last_updated': timezone.now().isoformat()
        }

    @classmethod
    def _analyze_profile_changes(cls, old_profile: Dict, new_profile: Dict) -> Dict[str, Any]:
        """
        Profil değişikliklerini analiz et
        """
        try:
            changes = {
                'difficulty_changes': {},
                'confidence_improvement': 0,
                'new_subjects_analyzed': [],
                'overall_trend': 'stable'
            }

            # Konu bazında değişiklikleri analiz et
            old_subjects = old_profile.get('subject_difficulties', {})
            new_subjects = new_profile.get('subject_difficulties', {})

            for subject_code, new_data in new_subjects.items():
                if subject_code in old_subjects:
                    old_difficulty = old_subjects[subject_code].get('recommended_difficulty', 3)
                    new_difficulty = new_data.get('recommended_difficulty', 3)

                    if old_difficulty != new_difficulty:
                        changes['difficulty_changes'][subject_code] = {
                            'from': old_difficulty,
                            'to': new_difficulty,
                            'trend': 'increased' if new_difficulty > old_difficulty else 'decreased'
                        }
                else:
                    changes['new_subjects_analyzed'].append(subject_code)

            # Güven seviyesi değişimi
            old_confidence = old_profile.get('confidence_level', 0)
            new_confidence = new_profile.get('confidence_level', 0)
            changes['confidence_improvement'] = new_confidence - old_confidence

            # Genel trend
            if changes['difficulty_changes']:
                increased_count = sum(1 for c in changes['difficulty_changes'].values() if c['trend'] == 'increased')
                decreased_count = sum(1 for c in changes['difficulty_changes'].values() if c['trend'] == 'decreased')

                if increased_count > decreased_count:
                    changes['overall_trend'] = 'improving'
                elif decreased_count > increased_count:
                    changes['overall_trend'] = 'declining'

            return changes

        except Exception as e:
            logger.error(f"Profile changes analysis error: {e}")
            return {'error': str(e)}