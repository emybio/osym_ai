import random
from typing import List, Dict
from django.db.models import Count, Q
from quiz.models import Question, Subject, TempExamSession


class SimpleQuestionSelector:
    """
    Basit ve hızlı soru seçici - optimizasyonları kaldırılmış
    """

    def __init__(self):
        pass

    def get_questions_for_user(self, session, user_identifier=None) -> List[Question]:
        """
        Basit soru seçimi - hızlı ve güvenilir
        """
        # Her ders için gereken soru sayısını hesapla
        subject_requirements = self._calculate_subject_requirements(session)

        selected_questions = []

        for subject_code, required_count in subject_requirements.items():
            if required_count == 0:
                continue

            try:
                subject = Subject.objects.get(code=subject_code)

                # Basit rastgele soru seçimi
                available_questions = list(Question.objects.filter(subject=subject))

                if len(available_questions) >= required_count:
                    questions = random.sample(available_questions, required_count)
                else:
                    # Mevcut tüm soruları al
                    questions = available_questions[:]
                    # Eksikse diğer konulardan tamamla
                    while len(questions) < required_count:
                        all_questions = list(Question.objects.all())
                        remaining = [q for q in all_questions if q not in questions]
                        if remaining:
                            questions.append(random.choice(remaining))
                        else:
                            break

                selected_questions.extend(questions)

            except Subject.DoesNotExist:
                continue

        # Tam olarak istenen sayıda soru döndür
        random.shuffle(selected_questions)
        return selected_questions[:session.question_count]

    def _calculate_subject_requirements(self, session) -> Dict[str, int]:
        """
        Basit dağılım hesapla
        """
        question_distribution = {
            "TYT": {
                "SAY": {"MAT": 6, "FIZ": 2, "KIM": 2, "BIO": 2, "TR": 6, "TAR": 1, "COG": 1},
                "EA":  {"MAT": 6, "FIZ": 2, "KIM": 2, "BIO": 2, "TR": 6, "TAR": 1, "COG": 1},
                "SOZ": {"MAT": 6, "FIZ": 1, "KIM": 1, "BIO": 1, "TR": 6, "TAR": 2, "COG": 1}
            },
            "AYT": {
                "SAY": {"MAT": 13, "FIZ": 7, "KIM": 6, "BIO": 4},
                "EA":  {"MAT": 13, "FIZ": 7, "KIM": 6, "BIO": 4},
                "SOZ": {"TR": 12, "TAR": 5, "COG": 5, "FIZ": 2, "KIM": 2, "BIO": 2}
            }
        }

        try:
            # Sadece mevcut olan konuları al
            available_subjects = Subject.objects.all()
            available_codes = set(s.code for s in available_subjects)

            if session.exam_type not in question_distribution:
                session.exam_type = "TYT"
            if session.branch not in question_distribution[session.exam_type]:
                session.branch = "SAY"

            distribution = question_distribution[session.exam_type][session.branch]

            # Mevcut olmayan konuları çıkar
            return {k: v for k, v in distribution.items() if k in available_codes}

        except Exception as e:
            print(f"Error calculating requirements: {e}")
            return {"TR": session.question_count}


# Global instance
simple_selector = SimpleQuestionSelector()