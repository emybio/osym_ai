#!/usr/bin/env python
"""
Question Quality Analyzer
JSON dosyasındaki soruları analiz eder ve kalite sorunlarını tespit eder
"""

import json
import re
from collections import defaultdict

def load_questions(filename):
    """JSON dosyasından soruları yükle"""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # Fix Turkish character encoding issues
        content = content.replace('�', 'Ö').replace('SYM', 'ÖSYM')
        data = json.loads(content)

    questions = []
    for item in data:
        if item.get('model') == 'quiz.question':
            questions.append(item)

    return questions

def analyze_question_quality(question):
    """Tek bir sorunun kalitesini analiz et"""
    fields = question.get('fields', {})
    question_text = fields.get('question_text', '')
    subject_id = fields.get('subject', 0)

    issues = []

    # 1. Generic içerik kontrolü
    generic_patterns = [
        r'temel soru',
        r'örnek soru',
        r'.*dersi.*\d+\. soru',
        r'hangi.*doğrudur',
        r'hangi.*yanlıştır',
        r'test sorusu',
        r'aynı.*şekilde.*sıralanmıştır'
    ]

    for pattern in generic_patterns:
        if re.search(pattern, question_text, re.IGNORECASE):
            issues.append(f"Generic content: {pattern}")
            break

    # 2. Subject relevance kontrolü (subject ID'ye göre)
    subject_content_issues = {
        1: ["Türkçe"],  # Türkçe
        2: ["Matematik", "denklem", "fonksiyon", "türev", "integral"],  # Matematik
        3: ["Fizik", "kuvvet", "enerji", "hız"],  # Fizik
        4: ["Kimya", "atom", "molekül", "reaksiyon"],  # Kimya
        5: ["Biyoloji", "hücre", "fotosentez", "DNA"],  # Biyoloji
        6: ["Tarih"],  # Tarih
        7: ["Coğrafya"],  # Coğrafya
        8: ["Felsefe"],  # Felsefe
        9: ["Din"],  # Din
    }

    # Subject ID'den ilgili ders adını ve anahtar kelimeleri al
    subject_keywords = subject_content_issues.get(subject_id, [])
    if subject_keywords:
        subject_name = subject_keywords[0]
        # Eğer soru metninde dersle ilgili kelimeler yoksa issue ekle
        has_relevant_content = any(keyword.lower() in question_text.lower() for keyword in subject_keywords[1:])
        if not has_relevant_content and len(subject_keywords) > 1:
            issues.append(f"No {subject_name} content found")

    # 3. Short question kontrolü
    if len(question_text.strip()) < 20:
        issues.append("Question too short")

    # 4. Question mark kontrolü
    if '?' not in question_text:
        issues.append("Missing question mark")

    # 5. Character encoding issues
    if '�' in question_text:
        issues.append("Encoding issues")

    return issues

def get_subject_name(subject_id):
    """Subject ID'den ders adını al"""
    subject_map = {
        1: "Türkçe",
        2: "Matematik",
        3: "Fizik",
        4: "Kimya",
        5: "Biyoloji",
        6: "Tarih",
        7: "Coğrafya",
        8: "Felsefe",
        9: "Din Kültürü"
    }
    return subject_map.get(subject_id, f"Unknown({subject_id})")

def analyze_all_questions(questions):
    """Tüm soruları analiz et"""
    print(f"Toplam {len(questions)} soru analiz ediliyor...\n")

    # Subject bazında sorunları grupla
    subject_issues = defaultdict(list)
    total_issues = 0

    for i, question in enumerate(questions):
        question_id = question.get('pk', f'Q{i}')
        fields = question.get('fields', {})
        subject_id = fields.get('subject', 0)
        subject_name = get_subject_name(subject_id)
        question_text = fields.get('question_text', '')[:50] + "..." if len(fields.get('question_text', '')) > 50 else fields.get('question_text', '')

        issues = analyze_question_quality(question)

        if issues:
            total_issues += len(issues)
            subject_issues[subject_name].append({
                'id': question_id,
                'text': question_text,
                'issues': issues
            })

    # Rapor oluştur
    print("=== SORU KALİTE ANALİZ RAPORU ===\n")
    print(f"Toplam sorunlu soru: {total_issues}")
    print(f"Analiz edilen toplam soru: {len(questions)}")
    print(f"Soranın sorunlu olma oranı: {(total_issues/len(questions)*100):.1f}%\n")

    for subject, problems in subject_issues.items():
        print(f"=== {subject} DERSİ ===")
        print(f"Sorunlu soru sayısı: {len(problems)}")

        for problem in problems[:5]:  # İlk 5 problemi göster
            print(f"  {problem['id']}: {problem['text']}")
            for issue in problem['issues']:
                print(f"    - {issue}")

        if len(problems) > 5:
            print(f"  ... ve {len(problems)-5} sorunlu soru daha")
        print()

    return subject_issues

def generate_fixes(subject_issues):
    """Sorunları düzeltmek için öneriler oluştur"""
    print("=== DÜZELTME ÖNERİLERİ ===\n")

    fix_count = 0
    for subject, problems in subject_issues.items():
        print(f"{subject} için {len(problems)} soru düzeltilecek:")

        for problem in problems:
            # Generic content sorunu için düzeltme
            if any("Generic content" in issue for issue in problem['issues']):
                fix_count += 1
                print(f"  {problem['id']}: Generic içerik -> {subject} spesifik soru")

            # Subject relevance sorunu için düzeltme
            if any("content found" in issue for issue in problem['issues']):
                fix_count += 1
                print(f"  {problem['id']}: İçerik eksik -> {subject} konulu soru")

        print()

    print(f"Toplam düzeltilecek soru: {fix_count}")
    return fix_count

if __name__ == "__main__":
    # Soruları yükle ve analiz et
    questions = load_questions('questions_original.json')
    subject_issues = analyze_all_questions(questions)
    fix_count = generate_fixes(subject_issues)

    print(f"\nJSON dosyası oluşturuldu: {len(questions)} soru analiz edildi")
    print(f"Düzeltilecek toplam soru: {fix_count}")