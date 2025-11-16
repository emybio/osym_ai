import random
from typing import List, Dict, Set
from datetime import datetime, timedelta

from django.db.models import Count, Q
from quiz.models import Question, Subject, TempExamSession, TempExamQuestion


class SmartQuestionSelector:
    """
    Aynı kullanıcının farklı sorular görmesini sağlayan akıllı soru seçim servisi
    """

    def __init__(self):
        self.question_history_cache = {}  # Kullanıcı soru geçmişi için cache

    def get_questions_for_user(self, session, user_identifier=None) -> List[Question]:
        """
        Kullanıcı için akıllı soru seçimi yapar

        Args:
            session: TempExamSession nesnesi
            user_identifier: Kullanıcıyı tanımlayan unique ID (IP, session key, etc.)

        Returns:
            List[Question]: Seçilen sorular
        """
        # Kullanıcının daha önce çözdüğü soruları al
        user_question_history = self._get_user_question_history(user_identifier)

        # Her ders için gereken soru sayısını hesapla
        subject_requirements = self._calculate_subject_requirements(session)

        selected_questions = []

        for subject_code, required_count in subject_requirements.items():
            try:
                subject = Subject.objects.get(code=subject_code)

                # Bu ders için uygun soruları seç
                subject_questions = self._select_subject_questions(
                    subject=subject,
                    required_count=required_count,
                    excluded_question_ids=user_question_history,
                    session=session
                )

                selected_questions.extend(subject_questions)

            except Subject.DoesNotExist:
                continue

        # Seçilen soruları rastgele karıştır
        random.shuffle(selected_questions)

        # Kullanıcı geçmişine yeni soruları ekle
        if user_identifier:
            self._add_to_user_history(user_identifier, selected_questions)

        return selected_questions

    def _get_user_question_history(self, user_identifier) -> Set[int]:
        """
        Kullanıcının daha önce çözdüğü soru ID'lerini getirir
        """
        if not user_identifier:
            return set()

        # Cache'den kontrol et
        if user_identifier in self.question_history_cache:
            return self.question_history_cache[user_identifier]

        # Veritabanından kullanıcı geçmişini al
        # Son 30 gündeki soruları kontrol et (yenilik sağlamak için)
        thirty_days_ago = datetime.now() - timedelta(days=30)

        recent_question_ids = set()

        try:
            # TempExamQuestion üzerinden kullanıcı geçmişini trace et
            # user_identifier genellikle session_key veya IP address olur
            past_sessions = TempExamSession.objects.filter(
                Q(session_key=user_identifier) |
                Q(temp_data__ip_address=user_identifier)
            ).filter(
                created_at__gte=thirty_days_ago
            ).prefetch_related('questions')

            for session in past_sessions:
                for temp_question in session.questions.all():
                    # Asıl Question ID'sini bulmak için text match kullan
                    original_questions = Question.objects.filter(
                        question_text=temp_question.question_text
                    )
                    recent_question_ids.update(original_questions.values_list('id', flat=True))

        except Exception as e:
            # Hata durumunda boş geçmiş döndür
            print(f"Error getting user question history: {e}")

        # Cache'e ekle
        self.question_history_cache[user_identifier] = recent_question_ids

        return recent_question_ids

    def _calculate_subject_requirements(self, session) -> Dict[str, int]:
        """
        Sınav oturumu için ders bazında soru sayılarını hesaplar
        """
        question_distribution = {
            "TYT": {
                "SAY": {
                    "MAT": 0.33,  # 40/120
                    "FIZ": 0.10,  # 7/20 Fen Bilimleri
                    "KIM": 0.10,  # 7/20 Fen Bilimleri
                    "BIO": 0.10,  # 6/20 Fen Bilimleri
                    "TR": 0.33,   # 40/120
                    "TAR": 0.07,  # 5/20 Sosyal Bilimler
                    "COG": 0.07,  # 5/20 Sosyal Bilimler
                    "INK": 0.00   # Din Kültürü TYT'de yok
                },
                "EA": {
                    "MAT": 0.33,  # 40/120
                    "FIZ": 0.10,  # 7/20 Fen Bilimleri
                    "KIM": 0.10,  # 7/20 Fen Bilimleri
                    "BIO": 0.10,  # 6/20 Fen Bilimleri
                    "TR": 0.33,   # 40/120
                    "TAR": 0.07,  # 5/20 Sosyal Bilimler
                    "COG": 0.07,  # 5/20 Sosyal Bilimler
                    "INK": 0.00   # Din Kültürü TYT'de yok
                },
                "SOZ": {
                    "MAT": 0.33,  # 40/120
                    "FIZ": 0.05,  # 3/20 Fen Bilimleri
                    "KIM": 0.05,  # 4/20 Fen Bilimleri
                    "BIO": 0.08,  # 6/20 Fen Bilimleri
                    "TR": 0.33,   # 40/120
                    "TAR": 0.10,  # 5/20 Sosyal Bilimler
                    "COG": 0.06,  # 5/20 Sosyal Bilimler
                    "INK": 0.00   # Din Kültürü TYT'de yok
                }
            },
            "AYT": {
                "SAY": {
                    "MAT": 0.50,  # 40/80
                    "FIZ": 0.20,  # 14/40
                    "KIM": 0.20,  # 13/40
                    "BIO": 0.10,  # 13/40
                    "TR": 0.00,
                    "TAR": 0.00,
                    "COG": 0.00,
                    "INK": 0.00,
                    "FEL": 0.00,
                    "DIN": 0.00
                },
                "EA": {
                    "MAT": 0.29,  # 23/80
                    "TR": 0.29,  # 23/80 (Edebiyat)
                    "TAR": 0.13,  # 10/80
                    "COG": 0.13,  # 10/80
                    "INK": 0.08,  # 6/80
                    "FEL": 0.08,  # 6/80
                    "FIZ": 0.00,
                    "KIM": 0.00,
                    "BIO": 0.00
                },
                "SOZ": {
                    "TR": 0.30,  # 24/80 (Edebiyat)
                    "TAR": 0.13,  # 10/80
                    "COG": 0.10,  # 8/80
                    "FEL": 0.15,  # 12/80
                    "INK": 0.32,  # 26/80
                    "MAT": 0.00,
                    "FIZ": 0.00,
                    "KIM": 0.00,
                    "BIO": 0.00
                }
            }
        }

        exam_type = session.exam_type
        branch = session.branch

        distribution = question_distribution.get(exam_type, {}).get(branch, {})

        if not distribution:
            return {}

        subject_requirements = {}
        valid_subjects = {k: v for k, v in distribution.items() if v > 0}

        # İlk olarak tam sayıları hesapla
        exact_counts = {}
        total_floor = 0

        for subject_code, weight in valid_subjects.items():
            count = int(session.question_count * weight)  # floor
            exact_counts[subject_code] = count
            total_floor += count

        # Kalan soruları dağıt
        remaining = session.question_count - total_floor

        if remaining > 0:
            # En yüksek kesirli kısma sahip derslere kalanları ekle
            fractions = {}
            for subject_code, weight in valid_subjects.items():
                exact = session.question_count * weight
                fraction = exact - int(exact)
                fractions[subject_code] = fraction

            # Kesirli kısma göre sırala
            sorted_by_fraction = sorted(fractions.items(), key=lambda x: x[1], reverse=True)

            for i in range(remaining):
                if i < len(sorted_by_fraction):
                    subject_code = sorted_by_fraction[i][0]
                    exact_counts[subject_code] += 1
                else:
                    # Eğer tüm derslere eklendiyse, en yüksek ağırlıklıya devam et
                    subject_code = max(valid_subjects.keys(), key=lambda k: valid_subjects[k])
                    exact_counts[subject_code] += 1

        return exact_counts

    def _select_subject_questions(self, subject, required_count, excluded_question_ids, session):
        """
        Belirli bir ders için soru seçimi yapar
        """
        try:
            # Önce exclude edilen sorular hariç tüm soruları al
            available_questions = Question.objects.filter(
                subject=subject
            ).exclude(
                id__in=excluded_question_ids
            )

            available_count = available_questions.count()

            # Eğer yeterli sayıda yeni soru yoksa, eski soruları da dahil et
            if available_count < required_count:
                additional_needed = required_count - available_count
                # Eski sorulardan rastgele seç
                old_questions = Question.objects.filter(
                    subject=subject,
                    id__in=excluded_question_ids
                ).order_by('?')[:additional_needed]

                # Yeni sorular + eski sorular
                selected_questions = list(available_questions.order_by('?')[:available_count])
                selected_questions.extend(list(old_questions))

            else:
                # Yeterli yeni soru varsa, sadece yeni sorulardan seç
                selected_questions = list(available_questions.order_by('?')[:required_count])

            # Konu çeşitliliği sağla (eğer mümkünse)
            selected_questions = self._ensure_topic_diversity(selected_questions, subject, required_count)

            return selected_questions

        except Exception as e:
            print(f"Error selecting questions for subject {subject.name}: {e}")
            return Question.objects.filter(subject=subject).order_by('?')[:required_count]

    def _ensure_topic_diversity(self, questions, subject, required_count):
        """
        Seçilen soruların konu çeşitliliğini sağlar
        """
        if not questions:
            return questions

        # Konulara göre grupla
        topics = {}
        for question in questions:
            topic_name = question.topic.name if question.topic else "Genel"
            if topic_name not in topics:
                topics[topic_name] = []
            topics[topic_name].append(question)

        # Her konudan en az bir soru olacak şekilde dağıt
        diverse_questions = []
        topics_per_question = min(len(topics), required_count // 2)  # En az yarısı farklı konulardan

        # Her konudan rastgele bir soru seç
        topic_count = 0
        for topic_name, topic_questions in topics.items():
            if topic_count >= topics_per_question:
                break
            if topic_questions:
                diverse_questions.append(random.choice(topic_questions))
                topic_count += 1

        # Kalan soruları rastgele ekle
        remaining_questions = [q for q in questions if q not in diverse_questions]
        random.shuffle(remaining_questions)

        needed = required_count - len(diverse_questions)
        diverse_questions.extend(remaining_questions[:needed])

        return diverse_questions[:required_count]

    def _add_to_user_history(self, user_identifier, questions):
        """
        Kullanıcı geçmişine yeni soruları ekler
        """
        if not user_identifier or not questions:
            return

        if user_identifier not in self.question_history_cache:
            self.question_history_cache[user_identifier] = set()

        self.question_history_cache[user_identifier].update(q.id for q in questions)

    def clear_user_cache(self, user_identifier=None):
        """
        Kullanıcı cache'ini temizler
        """
        if user_identifier:
            self.question_history_cache.pop(user_identifier, None)
        else:
            self.question_history_cache.clear()

    def get_user_statistics(self, user_identifier) -> Dict:
        """
        Kullanıcının soru çözüm istatistiklerini getirir
        """
        if not user_identifier:
            return {}

        recent_questions = self._get_user_question_history(user_identifier)

        return {
            "total_questions_seen": len(recent_questions),
            "recent_question_count": len(recent_questions),
            "cache_hit": user_identifier in self.question_history_cache
        }


# Global instance
smart_selector = SmartQuestionSelector()