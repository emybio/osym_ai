#!/usr/bin/env python3
"""
Veritabanı Temizleme Script'i
- Eksik soruları siler
- Tekrarlanan soruları kaldırır
- Şıkları düzeltir
- Otomatik eklenen şıkları temizler
"""

import os
import sys
import django
import json
import hashlib

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osym_ai.settings')
sys.path.append('/mnt/d/Projeler/osym_ai/backend')
django.setup()

from quiz.models import Question, Subject, Difficulty


def normalize_text(text):
    """Metni karşılaştırma için normalize et"""
    if not text:
        return ""
    # Boşlukları normalize et
    text = ' '.join(str(text).split())
    # Türkçe karakterleri normalize et
    text = text.replace('ı', 'i').replace('İ', 'I').replace('ğ', 'g').replace('Ğ', 'G')
    text = text.replace('ü', 'u').replace('Ü', 'U').replace('ş', 's').replace('Ş', 'S')
    text = text.replace('ö', 'o').replace('Ö', 'O').replace('ç', 'c').replace('Ç', 'C')
    return text.lower()


def calculate_question_hash(stem, choices):
    """Soru için hash hesapla (duplicate detection)"""
    content = normalize_text(stem)
    # İlk 3 seçeneği kullan (dinamik şıklar olabileceği için)
    for choice in choices[:3]:
        if 'hesaplanamayan' not in normalize_text(choice):
            content += normalize_text(choice)
    return hashlib.md5(content.encode()).hexdigest()


def clean_choices(choices):
    """Şıkları temizle"""
    if not isinstance(choices, list):
        return []

    # Otomatik eklenen şıkları kaldır
    cleaned = []
    for choice in choices:
        if choice and 'hesaplanamayan' not in normalize_text(choice) and 'calculated' not in normalize_text(choice):
            # Baştaki harf ve parantez kontrolü
            if len(choice) > 3 and choice[1] in [')', '.']:
                cleaned.append(choice.strip())
            elif len(choice) > 1:
                cleaned.append(choice.strip())

    # Eksik şıkları tamamla
    letters = ['A', 'B', 'C', 'D', 'E']
    if len(cleaned) < 5:
        for i in range(len(cleaned), 5):
            cleaned.append(letters[i] + ") Temizleme sırasında eklenen seçenek")

    # Fazla şıkları kes
    return cleaned[:5]


def is_valid_question(question):
    """Soru geçerli mi kontrol et"""
    stem = question.stem or ""
    if len(stem.strip()) < 20:
        return False, "Soru metni çok kısa"

    if "json parsing hatası" in stem.lower():
        return False, "JSON parsing hatası içeriyor"

    if "z.ai api'den gelen soru" in stem.lower():
        return False, "Hata mesajı içeriyor"

    return True, "Geçerli"


def main():
    print("🧹 Veritabanı Temizleme Başlatılıyor...")

    # Mevcut durumu analiz et
    questions = Question.objects.all()
    print(f"📊 Toplam {questions.count()} soru bulundu")

    # Geçersiz soruları sil
    invalid_count = 0
    for question in questions:
        is_valid, reason = is_valid_question(question)
        if not is_valid:
            print(f"❌ Siliniyor ID {question.id}: {reason}")
            question.delete()
            invalid_count += 1

    print(f"🗑️  {invalid_count} geçersiz soru silindi")

    # Kalan soruları analiz et
    remaining_questions = Question.objects.all()
    print(f"📋 Kalan soru sayısı: {remaining_questions.count()}")

    # Duplicate detection
    question_hashes = {}
    duplicates = []

    for question in remaining_questions:
        q_hash = calculate_question_hash(question.stem, question.choices)
        if q_hash in question_hashes:
            duplicates.append((question.id, question_hashes[q_hash]))
        else:
            question_hashes[q_hash] = question.id

    print(f"🔄 {len(duplicates)} tane tekrarlanan soru tespit edildi")

    # Duplicate'ları sil (daha yeni olanları sil)
    for dup_id, original_id in duplicates:
        dup_question = Question.objects.get(id=dup_id)
        original_question = Question.objects.get(id=original_id)

        if dup_question.created_at > original_question.created_at:
            print(f"🔄 Siliniyor (duplicate) ID {dup_id} -> Orijinal ID {original_id}")
            dup_question.delete()
        else:
            print(f"🔄 Siliniyor (duplicate) ID {original_id} -> Orijinal ID {dup_id}")
            original_question.delete()
            question_hashes[calculate_question_hash(dup_question.stem, dup_question.choices)] = dup_id

    # Şıkları temizle
    cleaned_questions = Question.objects.all()
    print(f"🔧 {cleaned_questions.count()} sorunun şıkları temizleniyor...")

    for question in cleaned_questions:
        original_choices = question.choices
        cleaned_choices = clean_choices(original_choices)

        if len(original_choices) != len(cleaned_choices):
            print(f"🔧 ID {question.id}: {len(original_choices)} -> {len(cleaned_choices)} şık")
            question.choices = cleaned_choices
            question.save()

    # Son durum
    final_questions = Question.objects.all()
    print(f"✅ Temizleme tamamlandı!")
    print(f"📊 Son durum:")
    print(f"   Toplam soru: {final_questions.count()}")

    subject_counts = {}
    for q in final_questions:
        subj = str(q.subject) if q.subject else 'Unknown'
        subject_counts[subj] = subject_counts.get(subj, 0) + 1

    for subj, count in sorted(subject_counts.items()):
        print(f"   {subj}: {count} soru")


if __name__ == "__main__":
    main()