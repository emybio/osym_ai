from .models import StudentResult, Topic
from django.db.models import Q
import random


def compute_topic_performance(student_id: str):
    """
    Her topic için öğrenci başarı oranını hesaplar.
    Dönen dict: {topic_id: accuracy}
    """
    results = StudentResult.objects.filter(student_id=student_id).select_related("question__topic")
    stats = {}
    counts = {}

    for r in results:
        t = r.question.topic_id
        stats.setdefault(t, 0)
        counts.setdefault(t, 0)
        stats[t] += 1 if r.is_correct else 0
        counts[t] += 1

    performance = {}
    for t, s in stats.items():
        performance[t] = s / counts[t] if counts[t] > 0 else 0.0
    return performance


def pick_topics_for_exam(student_id: str, phase: str, count: int = 160):
    """
    TYT/AYT sınavı için hangi konulardan soru üretileceğini belirler.
    phase: "TYT" veya "AYT"
    AYT için: %80 AYT konuları, %20 TYT konuları.
    TYT için: sadece TYT.
    Zayıf konulara öncelik verilir.
    """
    performance = compute_topic_performance(student_id)

    if phase == "TYT":
        pool = Topic.objects.filter(phase="TYT")
    else:
        ayt_topics = list(Topic.objects.filter(phase="AYT"))
        tyt_topics = list(Topic.objects.filter(phase="TYT"))
        # %80 AYT, %20 TYT
        ayt_count = int(count * 0.8)
        tyt_count = count - ayt_count
        # Zayıf konulara öncelik: performansı düşük olanları öne çek
        weak_ayt = sorted(ayt_topics, key=lambda t: performance.get(t.id, 1.0))[:ayt_count]
        weak_tyt = sorted(tyt_topics, key=lambda t: performance.get(t.id, 1.0))[:tyt_count]
        return weak_ayt + weak_tyt

    # TYT için zayıf konuları öne çek
    topics = list(pool)
    topics_sorted = sorted(topics, key=lambda t: performance.get(t.id, 1.0))
    if len(topics_sorted) >= count:
        return topics_sorted[:count]
    else:
        return topics_sorted


def generate_exam_questions(student_id: str, phase: str, count: int = 160):
    """
    Belirlenen konular üzerinden AI ile soru üretimini tetikler.
    """
    from .ai_generator import generate_question_for_topic

    topics = pick_topics_for_exam(student_id, phase, count)
    questions = []
    # Basit: her topic için 1 soru (gerekiyorsa aynı konudan birden fazla çağrı yapılabilir)
    for topic in topics:
        q = generate_question_for_topic(topic)
        if q:
            questions.append(q)
        if len(questions) >= count:
            break

    return questions