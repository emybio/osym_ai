import random
from typing import List, Dict, Set
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
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
        from django.db.models import Count

        # Performance: User history'yi devre dışı bırak (hız için)
        user_question_history = set()
        # if user_identifier:
        #     user_question_history = self._get_user_question_history(user_identifier)

        # Her ders için gereken soru sayısını hesapla
        subject_requirements = self._calculate_subject_requirements(session)

        # Performance: Tüm konuları tek seferde al
        available_subjects = Subject.objects.filter(
            code__in=subject_requirements.keys()
        ).annotate(
            question_count=Count('question')
        ).filter(question_count__gt=0)

        # Mevcut olmayan konuları requirements'tan çıkar
        available_subject_codes = set(s.code for s in available_subjects)
        subject_requirements = {
            k: v for k, v in subject_requirements.items()
            if k in available_subject_codes
        }

        selected_questions = []
        remaining_needed = session.question_count

        for subject_code, required_count in subject_requirements.items():
            if remaining_needed <= 0:
                break

            # Mevcut konuları map'ten al (tekrar sorgu yapma)
            subject = next(s for s in available_subjects if s.code == subject_code)

            # Bu ders için gereken soru sayısını yeniden hesapla
            actual_needed = min(required_count, remaining_needed)

            # Bu ders için uygun soruları seç
            subject_questions = self._select_subject_questions(
                subject=subject,
                required_count=actual_needed,
                excluded_question_ids=user_question_history,
                session=session
            )

            selected_questions.extend(subject_questions)
            remaining_needed -= len(subject_questions)

        # Eğer hala eksik soru varsa, mevcut konulardan rastgele ekle
        if remaining_needed > 0:
            existing_questions = Question.objects.filter(
                subject__in=available_subjects
            ).exclude(id__in=selected_questions)

            additional_questions = list(existing_questions.order_by('?')[:remaining_needed])
            selected_questions.extend(additional_questions)

        # Seçilen soruları rastgele karıştır
        random.shuffle(selected_questions)

        # Kullanıcı geçmişine yeni soruları ekle
        if user_identifier and selected_questions:
            self._add_to_user_history(user_identifier, selected_questions)

        return selected_questions

    def _get_user_question_history(self, user_identifier) -> Set[int]:
        """
        HIZLI PERFORMANCE İÇİN BOŞ - TempExamSession sorgusu çok yavaşlıyordu
        """
        # User history'i devre dışı bırak - 25 saniyelik soruna neden oluyordu
        return set()

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
        Belirli bir ders için optimize edilmiş soru seçimi yapar
        """
        try:
            # Performance: Tek sorguda tüm soruları al
            all_questions = Question.objects.filter(subject=subject)

            # Excluded ID'ler varsa filtrele
            if excluded_question_ids:
                available_questions = all_questions.exclude(id__in=excluded_question_ids)
            else:
                available_questions = all_questions

            # Performans: Count yerine len() kullan
            available_questions_list = list(available_questions)
            available_count = len(available_questions_list)

            # Eğer yeterli sayıda yeni soru yoksa, eski soruları da dahil et
            if available_count < required_count and excluded_question_ids:
                additional_needed = required_count - available_count
                # Eski sorulardan rastgele seç
                old_questions = list(all_questions.filter(id__in=excluded_question_ids).order_by('?')[:additional_needed])

                # Yeni sorular + eski sorular
                selected_questions = available_questions_list + old_questions
            else:
                # Yeterli yeni soru varsa, sadece yeni sorulardan seç
                selected_questions = available_questions_list

            # Performans: Topic diversity'yi sadece çok fazla soru varsa yap
            if len(selected_questions) > required_count * 2:
                selected_questions = self._ensure_topic_diversity(selected_questions, subject, required_count)

            # Rastgele karıştır ve kes
            random.shuffle(selected_questions)
            return selected_questions[:required_count]

        except Exception as e:
            print(f"Error selecting questions for subject {subject.name}: {e}")
            return list(Question.objects.filter(subject=subject).order_by('?')[:required_count])

    def _ensure_topic_diversity(self, questions, subject, required_count):
        """
        Seçilen soruların konu çeşitliliğini sağlar
        """
        if not questions or len(questions) <= required_count:
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

        needed = min(required_count - len(diverse_questions), len(remaining_questions))
        diverse_questions.extend(remaining_questions[:needed])

        # Eğer hala eksik varsa, kullanılmayan sorulardan rastgele ekle
        while len(diverse_questions) < required_count and len(diverse_questions) < len(questions):
            unused_questions = [q for q in questions if q not in diverse_questions]
            if unused_questions:
                diverse_questions.append(random.choice(unused_questions))
            else:
                break

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


# Global instance with lazy initialization
_smart_selector = None

def get_smart_selector():
    """Get or create the smart selector instance"""
    global _smart_selector
    if _smart_selector is None:
        _smart_selector = SmartQuestionSelector()
    return _smart_selector

# Backward compatibility
class _SmartSelectorProxy:
    def __getattr__(self, name):
        selector = get_smart_selector()
        return getattr(selector, name)

smart_selector = _SmartSelectorProxy()