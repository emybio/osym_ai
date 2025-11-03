from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Question, Attempt, Difficulty, Subject


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model with enhanced validation"""

    choices_display = serializers.SerializerMethodField()
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_display', 'topic', 'difficulty',
            'difficulty_display', 'stem', 'choices', 'choices_display',
            'answer', 'rubric', 'source', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_choices_display(self, obj):
        """Return formatted choices with letters"""
        if not obj.choices:
            return []
        return [f"{chr(65+i)}. {choice}" for i, choice in enumerate(obj.choices)]

    def validate_stem(self, value):
        """Validate question stem"""
        if not value or not value.strip():
            raise serializers.ValidationError("Soru metni boş olamaz.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Soru metni çok kısa.")
        if len(value) > 2000:
            raise serializers.ValidationError("Soru metni çok uzun (maks. 2000 karakter).")
        return value.strip()

    def validate_choices(self, value):
        """Validate answer choices"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Şıklar liste olmalıdır.")
        if len(value) < 2:
            raise serializers.ValidationError("En az 2 şık olmalıdır.")
        if len(value) > 5:
            raise serializers.ValidationError("En fazla 5 şık olabilir.")

        # Check for empty choices
        for i, choice in enumerate(value):
            if not choice or not choice.strip():
                raise serializers.ValidationError(f"Şık {i+1} boş olamaz.")

        # Check for duplicate choices
        cleaned_choices = [choice.strip().lower() for choice in value if choice.strip()]
        if len(cleaned_choices) != len(set(cleaned_choices)):
            raise serializers.ValidationError("Aynı şıktan birden fazla olamaz.")

        return [choice.strip() for choice in value]

    def validate_answer(self, value):
        """Validate answer letter"""
        if not value:
            raise serializers.ValidationError("Cevap belirtilmelidir.")

        answer_letter = value.upper()
        if answer_letter not in ['A', 'B', 'C', 'D', 'E']:
            raise serializers.ValidationError("Cevap A, B, C, D, veya E olmalıdır.")

        return answer_letter

    def validate_source(self, value):
        """Validate source field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Kaynak belirtilmelidir.")
        return value.strip()

    def validate(self, data):
        """Cross-field validation"""
        choices = data.get('choices', [])
        answer = data.get('answer', '')

        # Validate that answer letter corresponds to a valid choice
        if choices and answer:
            answer_index = ord(answer.upper()) - ord('A')
            if answer_index >= len(choices):
                raise serializers.ValidationError(f"Cevap şıkkı {answer} mevcut değil.")

        return data


class AttemptSerializer(serializers.ModelSerializer):
    """Serializer for Attempt model with enhanced validation"""

    question_info = QuestionSerializer(source='question', read_only=True)
    is_correct = serializers.BooleanField(read_only=True)

    class Meta:
        model = Attempt
        fields = [
            'id', 'question', 'question_info', 'selected_answer',
            'is_correct', 'response_time_ms', 'created_at'
        ]
        read_only_fields = ['id', 'is_correct', 'created_at']

    def validate_selected_answer(self, value):
        """Validate selected answer"""
        if not value or not value.strip():
            raise serializers.ValidationError("Seçilen cevap boş olamaz.")

        answer_letter = value.upper()
        if answer_letter not in ['A', 'B', 'C', 'D', 'E']:
            raise serializers.ValidationError("Seçilen cevap A, B, C, D, veya E olmalıdır.")

        return answer_letter

    def validate_response_time_ms(self, value):
        """Validate response time"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Cevaplama süresi negatif olamaz.")
        if value is not None and value > 3600000:  # 1 hour in milliseconds
            raise serializers.ValidationError("Cevaplama süresi çok uzun.")
        return value

    def validate(self, data):
        """Cross-field validation"""
        # Ensure the question exists and is accessible
        question = data.get('question')
        if question and not question.is_active:
            raise serializers.ValidationError("Bu soru artık aktif değil.")

        return data


class QuestionGenerationRequestSerializer(serializers.Serializer):
    """Serializer for question generation requests"""

    subject = serializers.ChoiceField(choices=Subject.choices, default=Subject.MATEMATIK)
    topic = serializers.CharField(max_length=100, default="Temel Kavramlar")
    difficulty = serializers.ChoiceField(choices=Difficulty.choices, default=Difficulty.MEDIUM)
    provider = serializers.ChoiceField(choices=['openai', 'zai'], default='openai')

    def validate_topic(self, value):
        """Validate topic name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Konu adı boş olamaz.")
        return value.strip()

    def validate_provider(self, value):
        """Validate AI provider"""
        allowed_providers = ['openai', 'zai']
        if value not in allowed_providers:
            raise serializers.ValidationError(f"Sağlayıcı şunlardan biri olmalı: {', '.join(allowed_providers)}")
        return value


class ExplanationRequestSerializer(serializers.Serializer):
    """Serializer for explanation requests"""

    provider = serializers.ChoiceField(choices=['openai', 'zai'], default='openai')

    def validate_provider(self, value):
        """Validate AI provider"""
        allowed_providers = ['openai', 'zai']
        if value not in allowed_providers:
            raise serializers.ValidationError(f"Sağlayıcı şunlardan biri olmalı: {', '.join(allowed_providers)}")
        return value