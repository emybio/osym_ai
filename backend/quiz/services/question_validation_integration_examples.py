"""
Soru Doğrulama Sistemi Entegrasyon Örneği

Bu dosya, soru oluşturma sürecine doğrulama sisteminin nasıl entegre edileceğini gösterir.
"""

from typing import Dict, Optional
import logging
from quiz.services.question_validation_system import (
    QuestionValidationSystem,
    ValidationStatus,
    generate_validation_report
)

logger = logging.getLogger(__name__)


class QuestionGeneratorWithValidation:
    """
    Doğrulama sistemi entegre edilmiş soru oluşturucu
    """
    
    def __init__(self, ai_service, max_attempts=3):
        self.ai_service = ai_service
        self.validator = QuestionValidationSystem()
        self.max_attempts = max_attempts
    
    def generate_validated_question(self, topic: str, difficulty: str, question_type: str = "general") -> Optional[Dict]:
        """
        Doğrulanmış soru oluşturur. Gerekirse birden fazla deneme yapar.
        
        Args:
            topic: Soru konusu
            difficulty: Zorluk seviyesi
            question_type: Soru tipi (parabola, geometry, function_graph, general)
            
        Returns:
            Doğrulanmış soru verisi veya None
        """
        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"Soru oluşturma denemesi {attempt}/{self.max_attempts}")
            
            # 1. AI ile soru oluştur
            question_data = self._generate_question_with_ai(topic, difficulty, question_type)
            
            if not question_data:
                logger.warning(f"AI soru oluşturamadı (deneme {attempt})")
                continue
            
            # 2. Doğrulama yap
            validation_result = self.validator.validate_question(question_data, question_type)
            
            # 3. Rapor oluştur ve logla
            report = generate_validation_report(validation_result)
            logger.info(f"Doğrulama Raporu (Deneme {attempt}):\n{report}")
            
            # 4. Sonuç kontrolü
            if validation_result.is_valid():
                logger.info(f"✓ Soru başarıyla doğrulandı (deneme {attempt})")
                question_data['validation_score'] = validation_result.score
                question_data['validation_attempt'] = attempt
                return question_data
            else:
                logger.warning(f"✗ Soru doğrulanamadı (deneme {attempt}, skor: {validation_result.score})")
                
                # Hataları analiz et ve AI'ya feedback ver
                if attempt < self.max_attempts:
                    feedback = self._generate_feedback_from_errors(validation_result)
                    logger.info(f"AI'ya feedback: {feedback}")
        
        logger.error(f"Soru {self.max_attempts} denemede oluşturulamadı")
        return None
    
    def _generate_question_with_ai(self, topic: str, difficulty: str, question_type: str) -> Optional[Dict]:
        """
        AI servisi ile soru oluşturur
        """
        try:
            # AI servisini çağır
            prompt = self._build_prompt(topic, difficulty, question_type)
            response = self.ai_service.generate(prompt)
            
            # Response'u parse et
            question_data = self._parse_ai_response(response)
            
            return question_data
        except Exception as e:
            logger.error(f"AI soru oluşturma hatası: {e}")
            return None
    
    def _build_prompt(self, topic: str, difficulty: str, question_type: str) -> str:
        """
        AI için prompt oluşturur
        """
        base_prompt = f"""
        Konu: {topic}
        Zorluk: {difficulty}
        Soru Tipi: {question_type}
        
        ÖSYM tarzında bir soru oluştur.
        """
        
        if question_type == "parabola":
            base_prompt += """
            
            ÖNEMLİ KURALLAR:
            1. Soru metninde fonksiyonu açıkça belirt: f(x) = ax² + bx + c
            2. SVG'de çizilen parabol bu fonksiyona TAM OLARAK uymalı
            3. Tepe noktası, kökler ve y-kesişimi doğru hesaplanmalı
            4. SVG koordinatları Kartezyen koordinat sistemine uygun olmalı
            """
        elif question_type == "geometry":
            base_prompt += """
            
            ÖNEMLİ KURALLAR:
            1. Açı değerlerini soru metninde açıkça belirt
            2. SVG'de açı işaretleri DOĞRU KONUMDA olmalı
            3. Açı işaretleri ilgili köşelerde gösterilmeli
            4. Verilen açı değerleri ile görsel tutarlı olmalı
            """
        
        return base_prompt
    
    def _parse_ai_response(self, response: str) -> Dict:
        """
        AI response'unu parse eder
        """
        # Bu fonksiyon AI servisinin response formatına göre özelleştirilmeli
        # Örnek implementasyon:
        import json
        try:
            return json.loads(response)
        except:
            return {}
    
    def _generate_feedback_from_errors(self, validation_result) -> str:
        """
        Doğrulama hatalarından AI için feedback oluşturur
        """
        feedback_parts = []
        
        for error in validation_result.errors:
            error_type = error['type']
            message = error['message']
            
            if 'parabola' in error_type.lower():
                feedback_parts.append(
                    f"Parabol hatası: {message}. "
                    "Fonksiyon tanımını ve SVG koordinatlarını kontrol et."
                )
            elif 'geometry' in error_type.lower():
                feedback_parts.append(
                    f"Geometri hatası: {message}. "
                    "Açı işaretlerinin konumunu ve değerlerini düzelt."
                )
            elif 'svg' in error_type.lower():
                feedback_parts.append(
                    f"SVG hatası: {message}. "
                    "SVG formatını ve elementleri kontrol et."
                )
            else:
                feedback_parts.append(f"Hata: {message}")
        
        return " ".join(feedback_parts)


# Kullanım Örneği 1: Basit Kullanım
def example_basic_usage():
    """Temel kullanım örneği"""
    from quiz.services.ai_service import AIService
    
    ai_service = AIService()
    generator = QuestionGeneratorWithValidation(ai_service)
    
    # Parabol sorusu oluştur
    question = generator.generate_validated_question(
        topic="Parabol",
        difficulty="orta",
        question_type="parabola"
    )
    
    if question:
        print("✓ Soru başarıyla oluşturuldu!")
        print(f"Doğrulama skoru: {question['validation_score']}")
        print(f"Deneme sayısı: {question['validation_attempt']}")
    else:
        print("✗ Soru oluşturulamadı")


# Kullanım Örneği 2: Batch İşleme
def example_batch_processing():
    """Toplu soru oluşturma örneği"""
    from quiz.services.ai_service import AIService
    
    ai_service = AIService()
    generator = QuestionGeneratorWithValidation(ai_service)
    
    topics = [
        ("Parabol", "kolay", "parabola"),
        ("Parabol", "orta", "parabola"),
        ("Üçgenler", "orta", "geometry"),
        ("Fonksiyonlar", "zor", "function_graph"),
    ]
    
    results = {
        'success': 0,
        'failed': 0,
        'total_attempts': 0
    }
    
    for topic, difficulty, question_type in topics:
        question = generator.generate_validated_question(topic, difficulty, question_type)
        
        if question:
            results['success'] += 1
            results['total_attempts'] += question['validation_attempt']
        else:
            results['failed'] += 1
            results['total_attempts'] += generator.max_attempts
    
    print(f"Başarılı: {results['success']}")
    print(f"Başarısız: {results['failed']}")
    print(f"Ortalama deneme: {results['total_attempts'] / len(topics):.1f}")


# Kullanım Örneği 3: Django View Entegrasyonu
def example_django_view_integration():
    """Django view'a entegrasyon örneği"""
    from django.http import JsonResponse
    from django.views import View
    from quiz.services.ai_service import AIService
    
    class GenerateQuestionView(View):
        def post(self, request):
            # Request'ten parametreleri al
            topic = request.POST.get('topic')
            difficulty = request.POST.get('difficulty')
            question_type = request.POST.get('question_type', 'general')
            
            # Soru oluştur
            ai_service = AIService()
            generator = QuestionGeneratorWithValidation(ai_service)
            
            question = generator.generate_validated_question(
                topic=topic,
                difficulty=difficulty,
                question_type=question_type
            )
            
            if question:
                # Veritabanına kaydet
                from quiz.models import Question
                db_question = Question.objects.create(
                    question_text=question['question_text'],
                    image_svg=question.get('image_svg'),
                    correct_answer=question['correct_answer'],
                    validation_score=question['validation_score']
                )
                
                # Seçenekleri kaydet
                for choice_data in question['choices']:
                    db_question.choices.create(
                        text=choice_data['text'],
                        is_correct=choice_data['is_correct']
                    )
                
                return JsonResponse({
                    'success': True,
                    'question_id': db_question.id,
                    'validation_score': question['validation_score'],
                    'attempts': question['validation_attempt']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Soru oluşturulamadı'
                }, status=400)


# Kullanım Örneği 4: Celery Task Entegrasyonu
def example_celery_task_integration():
    """Celery task'a entegrasyon örneği"""
    from celery import shared_task
    from quiz.services.ai_service import AIService
    
    @shared_task
    def generate_question_async(topic, difficulty, question_type='general'):
        """Asenkron soru oluşturma"""
        ai_service = AIService()
        generator = QuestionGeneratorWithValidation(ai_service)
        
        question = generator.generate_validated_question(
            topic=topic,
            difficulty=difficulty,
            question_type=question_type
        )
        
        if question:
            # Veritabanına kaydet
            from quiz.models import Question
            db_question = Question.objects.create(
                question_text=question['question_text'],
                image_svg=question.get('image_svg'),
                correct_answer=question['correct_answer'],
                validation_score=question['validation_score']
            )
            
            for choice_data in question['choices']:
                db_question.choices.create(
                    text=choice_data['text'],
                    is_correct=choice_data['is_correct']
                )
            
            return {
                'success': True,
                'question_id': db_question.id
            }
        else:
            return {
                'success': False,
                'error': 'Soru oluşturulamadı'
            }


# Kullanım Örneği 5: Manuel Doğrulama
def example_manual_validation():
    """Mevcut soruları manuel doğrulama"""
    from quiz.models import Question
    from quiz.services.question_validation_system import QuestionValidationSystem
    
    validator = QuestionValidationSystem()
    
    # Tüm soruları doğrula
    questions = Question.objects.filter(validation_score__isnull=True)
    
    for question in questions:
        question_data = {
            'question_text': question.question_text,
            'image_svg': question.image_svg,
            'choices': [
                {
                    'text': choice.text,
                    'is_correct': choice.is_correct
                }
                for choice in question.choices.all()
            ],
            'correct_answer': question.correct_answer
        }
        
        # Soru tipini belirle
        question_type = 'general'
        if 'parabol' in question.question_text.lower():
            question_type = 'parabola'
        elif any(word in question.question_text.lower() for word in ['açı', 'üçgen', 'dörtgen']):
            question_type = 'geometry'
        
        # Doğrula
        result = validator.validate_question(question_data, question_type)
        
        # Sonucu kaydet
        question.validation_score = result.score
        question.validation_status = result.status.value
        question.save()
        
        # Rapor oluştur
        if not result.is_valid():
            report = generate_validation_report(result)
            logger.warning(f"Soru {question.id} doğrulanamadı:\n{report}")


if __name__ == '__main__':
    # Örnekleri çalıştır
    print("Örnek 1: Basit Kullanım")
    example_basic_usage()
    
    print("\nÖrnek 2: Batch İşleme")
    example_batch_processing()
