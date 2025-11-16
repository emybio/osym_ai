from django.core.management.base import BaseCommand
import json
from quiz.models import Question, Choice

class Command(BaseCommand):
    help = 'Analyze questions in batches for quality issues'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, help='Start question number (1-500)')
        parser.add_argument('--end', type=int, help='End question number (1-500)')

    def handle(self, *args, **options):
        start = options.get('start', 1)
        end = options.get('end', 50)

        self.stdout.write(f"Analyzing questions {start}-{end}...")
        problematic = self.analyze_question_set(start, end)

        if problematic:
            filename = f'set_{start}_{end}_problematic.json'
            self.export_problematic_questions(problematic, filename)

            self.stdout.write(self.style.SUCCESS(f"Found {len(problematic)} problematic questions"))
            self.stdout.write(self.style.SUCCESS(f"Exported to {filename}"))

            # Show summary
            self.stdout.write("\n📋 PROBLEMATIC QUESTIONS:")
            for i, q in enumerate(problematic[:5], 1):  # Show first 5
                self.stdout.write(f"\n{i}. {q['id']} ({q['subject']})")
                self.stdout.write(f"   Issues: {', '.join(q['issues'])}")
                self.stdout.write(f"   Question: {q['question']}")
        else:
            self.stdout.write(self.style.SUCCESS("✅ No problematic questions found in this set!"))

    def analyze_question_quality(self, question):
        """Analyze question quality"""
        issues = []
        question_text = question.question_text.lower()
        subject_name = question.subject.name.lower()

        # Subject relevance
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

        # Question-Cevap uyumu
        choices_count = Choice.objects.filter(question=question).count()
        if choices_count != 5:
            issues.append(f"Wrong number of choices: {choices_count} (should be 5)")

        # Generic content
        if 'temel soru' in question_text or 'örnek soru' in question_text:
            issues.append("Generic content detected")

        # Question mark
        if '?' not in question.question_text:
            issues.append("Missing question mark")

        return issues

    def analyze_question_set(self, start_id, end_id):
        """Analyze specific range of questions"""
        problematic_questions = []

        questions = Question.objects.all().order_by('id')[start_id-1:end_id]

        for question in questions:
            issues = self.analyze_question_quality(question)

            if issues:
                problematic_questions.append({
                    'id': question.id,
                    'subject': question.subject.name,
                    'question': question.question_text[:100] + ("..." if len(question.question_text) > 100 else ""),
                    'issues': issues,
                    'choices_count': Choice.objects.filter(question=question).count()
                })

        return problematic_questions

    def export_problematic_questions(self, problematic_questions, filename):
        """Export problematic questions to JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(problematic_questions, f, ensure_ascii=False, indent=2)