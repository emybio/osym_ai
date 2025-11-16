#!/usr/bin/env python
"""
Batch Question Quality Analyzer
50'şer soruluk setlerde kalite sorunlarını tespit eder
"""

import json
import re
from quiz.models import Question, Choice

def analyze_question_quality(question):
    """Soru kalitesini analiz et - soru-cevap uyumu kontrolü"""
    issues = []

    question_text = question.question_text.lower()
    subject_name = question.subject.name.lower()

    # 1. Subject relevance kontrolü
    subject_keywords = {
        'türkçe': ['cümle', 'anlam', 'yazım', 'noktalama', 'sözcük', 'edat', 'bağlaç'],
        'matematik': ['denklem', 'fonksiyon', 'türev', 'integral', 'sayı', 'x', 'kaçtır'],
        'fizik': ['kuvvet', 'enerji', 'hız', 'ivme', 'volt', 'joule', 'newton'],
        'kimya': ['atom', 'molekül', 'reaksiyon', 'asit', 'baz', 'ph', 'element'],
        'biyoloji': ['hücre', 'fotosentez', 'dna', 'protein', 'organ', 'eniz'],
        'tarih': ['yıl', 'sultan', 'devlet', 'savaş', 'antlaşma', 'padisah'],
        'coğrafya': ['dağ', 'nehir', 'kıta', 'ülke', 'bölge', 'iklim'],
        'felsefe': ['felsefe', 'varlık', 'bilgi', 'mantık', 'ethik', 'akıl'],
        'din kültürü': ['islam', 'kuran', 'namaz', 'oruç', 'peygamber', 'din']
    }

    keywords = subject_keywords.get(subject_name, [])
    has_relevant = any(keyword in question_text for keyword in keywords)

    if not has_relevant and keywords:
        issues.append(f"No {subject_name} content found")

    # 2. Question-Cevap uyumu kontrolü
    choices = list(Choice.objects.filter(question=question))
    if len(choices) != 5:
        issues.append(f"Wrong number of choices: {len(choices)} (should be 5)")

    # 3. Generic content kontrolü
    generic_patterns = [
        r'temel soru',
        r'örnek soru',
        r'.*dersi.*\d+\. soru',
        r'hangi.*doğrudur',
        r'hangi.*yanlıştır'
    ]

    for pattern in generic_patterns:
        if re.search(pattern, question.question_text, re.IGNORECASE):
            issues.append(f"Generic content: {pattern}")
            break

    # 4. Question mark kontrolü
    if '?' not in question.question_text:
        issues.append("Missing question mark")

    return issues

def analyze_question_set(start_id, end_id):
    """Belirli aralıktaki soruları analiz et"""
    problematic_questions = []

    questions = Question.objects.all().order_by('id')[start_id-1:end_id]

    print(f"SET {start_id}-{end_id} ANALİZİ:")
    print(f"Toplam soru: {len(questions)}")

    for i, question in enumerate(questions):
        issues = analyze_question_quality(question)

        if issues:
            problematic_questions.append({
                'id': question.id,
                'subject': question.subject.name,
                'question': question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                'issues': issues,
                'choices_count': len(Choice.objects.filter(question=question))
            })

    print(f"🔍 Sorunlu soru: {len(problematic_questions)}")

    return problematic_questions

def export_problematic_questions(problematic_questions, filename):
    """Sorunlu soruları JSON olarak export et"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(problematic_questions, f, ensure_ascii=False, indent=2)

    print(f"📁 {len(problematic_questions)} sorunlu soru {filename} dosyasına export edildi")

if __name__ == "__main__":
    # Set 1: Sorular 1-50
    problematic = analyze_question_set(1, 50)

    if problematic:
        export_problematic_questions(problematic, 'set1_problematic_questions.json')

        print("\n📋 SORUNLU SORULAR:")
        for i, q in enumerate(problematic, 1):
            print(f"\n{i}. {q['id']} ({q['subject']})")
            print(f"   Sorun: {', '.join(q['issues'])}")
            print(f"   Soru: {q['question']}")
    else:
        print("\n✅ Set 1'de sorunlu soru bulunamadı!")