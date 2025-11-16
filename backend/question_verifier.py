#!/usr/bin/env python
"""
Question Quality Verifier
Düzeltilmiş soruların kalitesini kontrol eder
"""

import json
import re

def load_questions(filename):
    """JSON dosyasından soruları yükle"""
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        content = content.replace('�', 'Ö').replace('SYM', 'ÖSYM')
        data = json.loads(content)

    questions = []
    for item in data:
        if item.get('model') == 'quiz.question':
            questions.append(item)

    return questions

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

def verify_question_quality(question):
    """Düzeltilmiş sorunun kalitesini kontrol et"""
    fields = question.get('fields', {})
    question_text = fields.get('question_text', '')
    subject_id = fields.get('subject', 0)

    quality_score = 100
    issues = []

    # 1. Generic content kontrolü (düşük puan olmamalı)
    generic_patterns = [
        r'temel soru',
        r'örnek soru',
        r'.*dersi.*\d+\. soru',
        r'Corafya dersi',
        r'Geometrik sekli'
    ]

    for pattern in generic_patterns:
        if re.search(pattern, question_text, re.IGNORECASE):
            quality_score -= 30
            issues.append(f"Generic content detected: {pattern}")

    # 2. Subject relevance kontrolü (yüksek puan)
    subject_keywords = {
        1: ["Türkçe", "cümle", "anlam", "yazım", "noktalama", "sözcük"],
        2: ["Matematik", "denklem", "fonksiyon", "türev", "integral", "x =", "kaçtır"],
        3: ["Fizik", "kuvvet", "enerji", "hız", "volt", "joule", "newton"],
        4: ["Kimya", "atom", "molekül", "reaksiyon", "pH", "asit", "baz"],
        5: ["Biyoloji", "hücre", "fotosentez", "DNA", "RNA", "protein"],
        6: ["Tarih", "yıl", "sultan", "devlet", "savaş", "antlaşma"],
        7: ["Coğrafya", "dağ", "nehir", "kıta", "ülke", "bölge"],
        8: ["Felsefe", "varlık", "bilgi", "etik", "mantık", "akıl"],
        9: ["Din", "islam", "kuran", "namaz", "oruç", "peygamber"]
    }

    if subject_id in subject_keywords:
        keywords = subject_keywords[subject_id]
        has_relevant = any(keyword.lower() in question_text.lower() for keyword in keywords)
        if has_relevant:
            quality_score += 10  # Subject relevance bonus
        else:
            quality_score -= 20
            issues.append("No subject-relevant content found")

    # 3. Question mark kontrolü
    if '?' not in question_text:
        quality_score -= 15
        issues.append("Missing question mark")

    # 4. Minimum length kontrolü
    if len(question_text.strip()) < 20:
        quality_score -= 25
        issues.append("Question too short")

    # 5. Character encoding
    if '�' in question_text:
        quality_score -= 10
        issues.append("Encoding issues")

    # 6. ÖSYM standard kontrolü
    if "ÖSYM standardı" in fields.get('explanation', ''):
        quality_score += 5

    return max(0, min(100, quality_score)), issues

def analyze_quality_distribution(questions):
    """Kalite dağılımını analiz et"""
    scores = []
    subject_scores = {}

    for question in questions:
        fields = question.get('fields', {})
        subject_id = fields.get('subject', 0)
        subject_name = get_subject_name(subject_id)

        score, issues = verify_question_quality(question)
        scores.append(score)

        if subject_name not in subject_scores:
            subject_scores[subject_name] = []
        subject_scores[subject_name].append(score)

    # İstatistikler
    avg_score = sum(scores) / len(scores)
    high_quality = len([s for s in scores if s >= 80])
    medium_quality = len([s for s in scores if 60 <= s < 80])
    low_quality = len([s for s in scores if s < 60])

    print(f"=== GENEL KALİTE RAPORU ===")
    print(f"Toplam soru: {len(questions)}")
    print(f"Ortalama kalite skoru: {avg_score:.1f}/100")
    print(f"Yüksek kalite (80+): {high_quality} ({high_quality/len(questions)*100:.1f}%)")
    print(f"Orta kalite (60-79): {medium_quality} ({medium_quality/len(questions)*100:.1f}%)")
    print(f"Düşük kalite (<60): {low_quality} ({low_quality/len(questions)*100:.1f}%)")
    print()

    # Subject bazında kalite
    print(f"=== DERS BAZINDA KALİTE ===")
    for subject_name, scores_list in subject_scores.items():
        avg = sum(scores_list) / len(scores_list)
        print(f"{subject_name:12}: {avg:.1f}/100 ({len(scores_list)} soru)")

    return avg_score, subject_scores

def show_best_questions(questions, count=5):
    """En iyi soruları göster"""
    scored_questions = []

    for question in questions:
        score, issues = verify_question_quality(question)
        scored_questions.append((question, score, issues))

    # En yüksek skorlu sorular
    best_questions = sorted(scored_questions, key=lambda x: x[1], reverse=True)[:count]

    print(f"\n=== EN İYİ {count} SORU ===")
    for i, (question, score, issues) in enumerate(best_questions, 1):
        fields = question.get('fields', {})
        subject_id = fields.get('subject', 0)
        subject_name = get_subject_name(subject_id)
        question_text = fields.get('question_text', '')

        print(f"\n{i}. {subject_name} (Skor: {score}/100)")
        print(f"   {question_text}")
        if issues:
            print(f"   Issues: {', '.join(issues)}")

def show_worst_questions(questions, count=5):
    """En kötü soruları göster"""
    scored_questions = []

    for question in questions:
        score, issues = verify_question_quality(question)
        scored_questions.append((question, score, issues))

    # En düşük skorlu sorular
    worst_questions = sorted(scored_questions, key=lambda x: x[1])[:count]

    print(f"\n=== EN DÜŞÜK {count} SORU ===")
    for i, (question, score, issues) in enumerate(worst_questions, 1):
        fields = question.get('fields', {})
        subject_id = fields.get('subject', 0)
        subject_name = get_subject_name(subject_id)
        question_text = fields.get('question_text', '')

        print(f"\n{i}. {subject_name} (Skor: {score}/100)")
        print(f"   {question_text}")
        print(f"   Issues: {', '.join(issues)}")

if __name__ == "__main__":
    questions = load_questions('questions_fixed.json')

    print(f"Düzeltilmiş {len(questions)} soru analiz ediliyor...\n")

    # Kalite analizi
    avg_score, subject_scores = analyze_quality_distribution(questions)

    # En iyi ve en kötü örnekler
    show_best_questions(questions, 5)
    show_worst_questions(questions, 5)

    print(f"\n=== ÖZET ===")
    print(f"Toplam soru kalitesi: {avg_score:.1f}/100")
    if avg_score >= 80:
        print("✅ MÜKEMMEL - Sorular yüksek kalitede")
    elif avg_score >= 70:
        print("✅ İYİ - Sorular genel olarak kaliteli")
    elif avg_score >= 60:
        print("⚠️ ORTA - Bazı iyileştirmeler yapılabilir")
    else:
        print("❌ DÜŞÜK - Ciddi iyileştirmeler gerekli")