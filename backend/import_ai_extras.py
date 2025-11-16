#!/usr/bin/env python
"""
AI Standard Extras Importer
5-choice, measures, ve misconceptions verilerini veritabanına aktarır
"""

import json
from quiz.models import Question, Choice, Subskill, Measure, Misconception

def load_ai_extras(filename):
    """AI standard extras verilerini yükle"""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        content = content.replace('�', 'Ö').replace('SYM', 'ÖSYM')
        data = json.loads(content)

    return data

def import_choices_with_extras(ai_extras_data):
    """AI standard choices ve extras'ları import et"""
    imported_count = 0
    error_count = 0

    for question_id, extras in ai_extras_data.items():
        try:
            # Question'ı bul
            question = Question.objects.get(id=question_id)

            # Mevcut choices'ları temizle
            Choice.objects.filter(question=question).delete()
            Measure.objects.filter(question=question).delete()
            Misconception.objects.filter(question=question).delete()

            choices_data = extras.get('choices', {})
            measures_data = extras.get('measures', [])
            misconceptions_data = extras.get('misconceptions', {})

            # Yeni Choices'ları oluştur
            for label, text in choices_data.items():
                is_correct = (label == question.correct_answer)
                Choice.objects.create(
                    question=question,
                    label=label,
                    text=text,
                    is_correct=is_correct
                )

            # Measures'ları oluştur
            for measure_data in measures_data:
                subskill_name = measure_data.get('subskill', '')
                rule = measure_data.get('rule', '')
                weight = measure_data.get('weight', 1.0)

                # Subskill bul veya oluştur
                if question.topic:
                    subskill, created = Subskill.objects.get_or_create(
                        topic=question.topic,
                        name=subskill_name,
                        defaults={'description': rule}
                    )
                else:
                    continue

                Measure.objects.create(
                    question=question,
                    subskill=subskill,
                    rule=rule,
                    weight=weight
                )

            # Misconceptions'ları oluştur
            for choice_label, misconception_list in misconceptions_data.items():
                if not isinstance(misconception_list, list):
                    misconception_list = [misconception_list]

                for description in misconception_list:
                    Misconception.objects.create(
                        question=question,
                        choice_label=choice_label,
                        description=description
                    )

            imported_count += 1

        except Question.DoesNotExist:
            print(f"Question bulunamadı: {question_id}")
            error_count += 1
        except Exception as e:
            print(f"Hata - {question_id}: {str(e)}")
            error_count += 1

    return imported_count, error_count

def verify_import():
    """Import sonrası doğrulama"""
    print("\n=== IMPORT DOĞRULAMA ===")
    print(f"Toplam Question: {Question.objects.count()}")
    print(f"Toplam Choice: {Choice.objects.count()}")
    print(f"Ortalama choices per question: {Choice.objects.count() / Question.objects.count():.1f}")
    print(f"Toplam Measure: {Measure.objects.count()}")
    print(f"Toplam Misconception: {Misconception.objects.count()}")

    # 5-choice kontrolü
    questions_with_5_choices = 0
    for question in Question.objects.all():
        choice_count = Choice.objects.filter(question=question).count()
        if choice_count == 5:
            questions_with_5_choices += 1

    print(f"5 seçenekli sorular: {questions_with_5_choices}/{Question.objects.count()}")
    print(f"5-choice oranı: {(questions_with_5_choices/Question.objects.count()*100):.1f}%")

if __name__ == "__main__":
    print("AI Standard Extras Import başlatılıyor...")

    # AI extras verilerini yükle
    ai_extras = load_ai_extras('ai_standard_extras.json')
    print(f"Yüklenen question sayısı: {len(ai_extras)}")

    # Import et
    imported, errors = import_choices_with_extras(ai_extras)

    print(f"\n=== IMPORT SONUÇLARI ===")
    print(f"✅ Başarılı import: {imported}")
    print(f"❌ Hatalı import: {errors}")
    print(f"📊 Başarı oranı: {(imported/(imported+errors)*100):.1f}%")

    # Doğrulama
    verify_import()

    print(f"\n🎯 AI Standard extras import tamamlandı!")