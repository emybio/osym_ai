from django.core.management.base import BaseCommand
import json
from quiz.models import Question, Choice, Subskill, Measure, Misconception


class Command(BaseCommand):
    help = 'Import AI standard choices, measures, and misconceptions'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='AI extras JSON file path')

    def handle(self, *args, **options):
        json_file = options['json_file']

        self.stdout.write("AI Standard Extras Import başlatılıyor...")

        # AI extras verilerini yükle
        try:
            with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                content = content.replace('�', 'Ö').replace('SYM', 'ÖSYM')
                ai_extras = json.loads(content)

            self.stdout.write(f"Yüklenen question sayısı: {len(ai_extras)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Dosya okuma hatası: {e}"))
            return

        # Import et
        imported, errors = self.import_choices_with_extras(ai_extras)

        self.stdout.write(self.style.SUCCESS(f"\n=== IMPORT SONUÇLARI ==="))
        self.stdout.write(self.style.SUCCESS(f"✅ Başarılı import: {imported}"))
        self.stdout.write(self.style.ERROR(f"❌ Hatalı import: {errors}"))
        success_rate = (imported/(imported+errors)*100) if (imported+errors) > 0 else 0
        self.stdout.write(self.style.SUCCESS(f"📊 Başarı oranı: {success_rate:.1f}%"))

        # Doğrulama
        self.verify_import()

        self.stdout.write(self.style.SUCCESS(f"\n🎯 AI Standard extras import tamamlandı!"))

    def import_choices_with_extras(self, ai_extras_data):
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

                if imported_count % 50 == 0:
                    self.stdout.write(f"{imported_count} soru işlendi...")

            except Question.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Question bulunamadı: {question_id}"))
                error_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Hata - {question_id}: {str(e)}"))
                error_count += 1

        return imported_count, error_count

    def verify_import(self):
        """Import sonrası doğrulama"""
        self.stdout.write(self.style.SUCCESS("\n=== IMPORT DOĞRULAMA ==="))
        self.stdout.write(f"Toplam Question: {Question.objects.count()}")
        self.stdout.write(f"Toplam Choice: {Choice.objects.count()}")

        if Question.objects.count() > 0:
            avg_choices = Choice.objects.count() / Question.objects.count()
            self.stdout.write(f"Ortalama choices per question: {avg_choices:.1f}")

        self.stdout.write(f"Toplam Measure: {Measure.objects.count()}")
        self.stdout.write(f"Toplam Misconception: {Misconception.objects.count()}")

        # 5-choice kontrolü
        questions_with_5_choices = 0
        for question in Question.objects.all():
            choice_count = Choice.objects.filter(question=question).count()
            if choice_count == 5:
                questions_with_5_choices += 1

        if Question.objects.count() > 0:
            five_choice_rate = (questions_with_5_choices/Question.objects.count()*100)
            self.stdout.write(f"5 seçenekli sorular: {questions_with_5_choices}/{Question.objects.count()}")
            self.stdout.write(f"5-choice oranı: {five_choice_rate:.1f}%")