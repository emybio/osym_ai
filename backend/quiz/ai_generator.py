import json
from openai import OpenAI
from django.conf import settings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from .models import Subject, Topic, Question, Choice, Measure, Misconception, Subskill

client = OpenAI(api_key=settings.OPENAI_API_KEY)


SYSTEM_PROMPT = """
Sen Türkiye'de YKS (TYT-AYT) düzeyinde soru hazırlayan, deneyimli bir öğretmensin.
Uzmanlık alanların: Türkçe, Matematik, Fizik, Kimya, Biyoloji, Geometri.

Kurallar:
1. Tüm metinler TÜRKÇE olacak.
2. HER zaman SADECE GEÇERLİ BİR JSON objesi döndür. JSON dışında tek bir karakter bile yazma.
3. JSON alanları:
   - id: string (ör: "TR-NOK-004" veya "AUTO")
   - lesson: string (ör: "Türkçe", "Matematik")
   - topic: string
   - question_text: string (soru cümlesi, tam ve anlamlı bitmeli)
   - choices: obje, 5 şık: {"A":"...", "B":"...", "C":"...", "D":"...", "E":"..."}
   - correct_answer: string ("A"..."E")
   - difficulty: string (ör: "Kolay", "Orta", "Zor")
   - cognitive: string (ör: "Bilgi", "Kavrama", "Analiz")
   - measures: liste, her eleman:
       { "subskill": "...", "rule": "...", "weight": 0.7 }
   - misconceptions: obje, her şık için liste:
       "A": ["..."], "B": ["..."], ...
   - explanation: string (adım adım çözüm/rubrik)

4. choices mutlaka 5 şıklı olacak ve yalnızca 1 tanesi doğru (correct_answer ile uyumlu) olacak.
5. Soru cümlesi eksik kalmayacak, soru işareti veya nokta ile son bulacak.
6. Açıklamada (explanation) cevabı doğrudan söyleme ("C şıkkı doğrudur" gibi) ZORUNLU DEĞİL.
7. Şıklar arasında birebir aynı metin bulunmamalı.
8. measures içindeki weight değerleri 0 ile 1 arasında olmalı ve toplamı yaklaşık 1 olmalı.
"""


def _load_context_from_pdf_and_past(subject_code: str, topic_name: str) -> str:
    """
    PDF müfredat + geçmiş sorular embedding indekslerinden bağlam çeker.
    """
    embeddings = OpenAIEmbeddings()

    try:
        pdf_db = Chroma(persist_directory="chroma_yks_pdf", embedding_function=embeddings)
        pdf_docs = pdf_db.similarity_search(f"{subject_code} {topic_name}", k=2)
    except Exception:
        pdf_docs = []

    try:
        past_db = Chroma(persist_directory="chroma_past", embedding_function=embeddings)
        past_docs = past_db.similarity_search(f"{subject_code} {topic_name}", k=3)
    except Exception:
        past_docs = []

    parts = []
    for d in pdf_docs:
        parts.append(d.page_content)
    for d in past_docs:
        parts.append(d.page_content)

    return "\n\n".join(parts[:5])


def generate_question_for_topic(topic: Topic, difficulty: int = 3):
    """
    Verilen Topic için bir adet soru üretir, validasyon yapar, Question ve ilişkili Choice/Measure/Misconception
    kayıtlarını veritabanına kaydeder. Hata durumunda None döner.
    """
    subject = topic.subject
    context = _load_context_from_pdf_and_past(subject.code, topic.name)

    user_prompt = f"""
Ders: {subject.name}
Ders Kodu: {subject.code}
Konu: {topic.name}
Sınav aşaması: {topic.phase}
Zorluk düzeyi: {difficulty}/5

Aşağıda MEB/ÖSYM müfredat ve geçmiş sorulardan ilgili parçalar yer alıyor:
{context}

Bu konuya uygun, YKS seviyesinde ÖZGÜN bir soru üret.
JSON dışında hiçbir şey yazma.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",   # veya kullandığın model
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None  # Gerekirse tekrar deneme mekanizması eklenebilir

    # Basit validasyonlar
    if "choices" not in data or "correct_answer" not in data:
        return None
    choices = data["choices"]
    if len(choices.keys()) != 5:
        return None
    if data["correct_answer"] not in choices.keys():
        return None

    # 1 doğru şık kontrolü: JSON'da ayrıca is_correct yok, correct_answer alanına güveniyoruz.
    # İstersek explanation içinde correct_answer ile tutarlılık kontrolü de yapabiliriz.

    # Question kaydı
    qid = data.get("id") or f"{subject.code}-{topic.id}-{Question.objects.count()+1:04d}"
    question = Question.objects.create(
        id=qid,
        subject=subject,
        topic=topic,
        question_text=data.get("question_text", ""),
        difficulty=difficulty,
        cognitive=data.get("cognitive", "Kavrama"),
        correct_answer=data["correct_answer"],
        explanation=data.get("explanation", ""),
    )

    # Choice kayıtları
    for label, text in choices.items():
        Choice.objects.create(
            question=question,
            label=label,
            text=text,
            is_correct=(label == data["correct_answer"]),
        )

    # Measures (subskill eşleştirme, isim bazlı)
    for m in data.get("measures", []):
        subskill_name = m.get("subskill")
        if not subskill_name:
            continue
        subskill_obj, _ = Subskill.objects.get_or_create(topic=topic, name=subskill_name)
        Measure.objects.create(
            question=question,
            subskill=subskill_obj,
            rule=m.get("rule", ""),
            weight=m.get("weight", 1.0),
        )

    # Misconceptions
    for label, descriptions in data.get("misconceptions", {}).items():
        if not isinstance(descriptions, list):
            descriptions = [descriptions]
        for desc in descriptions:
            Misconception.objects.create(
                question=question,
                choice_label=label,
                description=desc,
            )

    return question