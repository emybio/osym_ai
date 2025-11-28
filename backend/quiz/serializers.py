from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import (
    Question, Attempt, Subject, Topic, Subskill, Choice, StudentResult,
    PDFDocument, PDFProcessingLog, TempExamSession, TempExamQuestion,
    TempExamResult, ExamResult
)
from django.contrib.auth.models import User

class ChoiceSerializer(serializers.ModelSerializer):
    """Serializer for Choice model"""

    class Meta:
        model = Choice
        fields = ['label', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model with enhanced validation"""

    choices = ChoiceSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    subskills = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_name',
            'subskills', 'question_text', 'difficulty', 'cognitive',
            'correct_answer', 'explanation', 'choices', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_question_text(self, value):
        """Validate question text"""
        if not value or not value.strip():
            raise serializers.ValidationError("Soru metni boş olamaz.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Soru metni çok kısa.")
        if len(value) > 2000:
            raise serializers.ValidationError("Soru metni çok uzun (maks. 2000 karakter).")
        return value.strip()

    def validate_correct_answer(self, value):
        """Validate answer letter"""
        if not value:
            raise serializers.ValidationError("Cevap belirtilmelidir.")

        answer_letter = value.upper()
        if answer_letter not in ['A', 'B', 'C', 'D', 'E']:
            raise serializers.ValidationError("Cevap A, B, C, D, veya E olmalıdır.")

        return answer_letter

    def validate_difficulty(self, value):
        """Validate difficulty"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Zorluk seviyesi 1-5 arasında olmalıdır.")
        return value


class StudentResultSerializer(serializers.ModelSerializer):
    """Serializer for StudentResult model"""

    question_info = QuestionSerializer(source='question', read_only=True)
    is_correct = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentResult
        fields = [
            'id', 'student_id', 'question', 'question_info',
            'selected_answer', 'is_correct', 'measures_result', 'created_at'
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


class AttemptSerializer(serializers.ModelSerializer):
    """Serializer for Attempt model (legacy support)"""

    question_info = QuestionSerializer(source='question', read_only=True)
    is_correct = serializers.BooleanField(read_only=True)

    class Meta:
        model = Attempt
        fields = [
            'id', 'user', 'question', 'question_info', 'choice',
            'is_correct', 'created_at'
        ]
        read_only_fields = ['id', 'is_correct', 'created_at']

    def validate_choice(self, value):
        """Validate selected answer"""
        if not value or not value.strip():
            raise serializers.ValidationError("Seçilen cevap boş olamaz.")

        answer_letter = value.upper()
        if answer_letter not in ['A', 'B', 'C', 'D', 'E']:
            raise serializers.ValidationError("Seçilen cevap A, B, C, D, veya E olmalıdır.")

        return answer_letter


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""

    class Meta:
        model = Subject
        fields = ['id', 'code', 'name']


class TopicSerializer(serializers.ModelSerializer):
    """Serializer for Topic model"""

    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Topic
        fields = ['id', 'subject', 'subject_name', 'name', 'phase']


class SubskillSerializer(serializers.ModelSerializer):
    """Serializer for Subskill model"""

    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = Subskill
        fields = ['id', 'topic', 'topic_name', 'name', 'description']


class QuestionGenerationRequestSerializer(serializers.Serializer):
    """Serializer for question generation requests"""

    subject = serializers.CharField(max_length=50)
    topic = serializers.CharField(max_length=100)
    difficulty = serializers.IntegerField(min_value=1, max_value=5, default=3)
    count = serializers.IntegerField(min_value=1, max_value=50, default=1)

    def validate_topic(self, value):
        """Validate topic name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Konu adı boş olamaz.")
        return value.strip()

    def validate_subject(self, value):
        """Validate subject name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Ders adı boş olamaz.")
        return value.strip()


class ExplanationRequestSerializer(serializers.Serializer):
    """Serializer for explanation requests"""

    question_id = serializers.CharField(max_length=30)

    def validate_question_id(self, value):
        """Validate question ID"""
        if not value or not value.strip():
            raise serializers.ValidationError("Soru ID'si boş olamaz.")
        return value.strip()


class PDFDocumentSerializer(serializers.ModelSerializer):
    """Serializer for PDFDocument model"""

    subject_name = serializers.CharField(source='subject.name', read_only=True)
    file_size = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = PDFDocument
        fields = [
            'id', 'title', 'description', 'document_type', 'subject', 'subject_name',
            'exam_type', 'year', 'file', 'file_size', 'is_processed', 'processed_at',
            'processing_status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at', 'is_processed']

    def get_file_size(self, obj):
        """Return file size in MB"""
        if obj.file:
            return round(obj.file.size / (1024 * 1024), 2)
        return 0

    def get_processing_status(self, obj):
        """Get processing status from latest log"""
        latest_log = obj.processing_logs.first()
        if latest_log:
            return {
                'status': latest_log.status,
                'message': latest_log.message,
                'started_at': latest_log.started_at,
                'completed_at': latest_log.completed_at
            }
        return None

    def validate_document_type(self, value):
        """Validate document type"""
        if value not in ['CURRICULUM', 'PAST_EXAM']:
            raise serializers.ValidationError("Geçersiz doküman türü.")
        return value

    def validate_exam_type(self, value):
        """Validate exam type"""
        if value and value not in ['TYT', 'AYT', 'BOTH']:
            raise serializers.ValidationError("Geçersiz sınav türü.")
        return value


class PDFProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for PDFProcessingLog model"""

    pdf_title = serializers.CharField(source='pdf_document.title', read_only=True)

    class Meta:
        model = PDFProcessingLog
        fields = [
            'id', 'pdf_document', 'pdf_title', 'status', 'message',
            'error_details', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'pdf_document', 'started_at', 'completed_at']


# Hızlı Test Serializer'ları
class TempExamQuestionSerializer(serializers.ModelSerializer):
    """Hızlı test soruları için serializer"""

    class Meta:
        model = TempExamQuestion
        fields = [
            'id', 'question_text', 'options', 'subject', 'topic',
            'difficulty', 'order'
        ]
        read_only_fields = ['id']


class TempExamSessionSerializer(serializers.ModelSerializer):
    """Geçici sınav oturumu için serializer"""

    questions = TempExamQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TempExamSession
        fields = [
            'uuid', 'exam_type', 'branch', 'question_count',
            'duration_minutes', 'status', 'temp_data', 'created_at', 'questions'
        ]
        read_only_fields = ['uuid', 'created_at', 'status']


class TempExamSessionCreateSerializer(serializers.ModelSerializer):
    """Yeni hızlı test oturumu oluşturma serializer'ı"""

    class Meta:
        model = TempExamSession
        fields = [
            'exam_type', 'branch', 'question_count', 'duration_minutes'
        ]

    def validate_exam_type(self, value):
        if value not in ['TYT', 'AYT']:
            raise serializers.ValidationError("Geçersiz sınav türü.")
        return value

    def validate_branch(self, value):
        if value not in ['SAY', 'EA', 'SOZ']:
            raise serializers.ValidationError("Geçersiz branş.")
        return value

    def validate_question_count(self, value):
        if not 5 <= value <= 20:
            raise serializers.ValidationError("Soru sayısı 5-20 arasında olmalıdır.")
        return value

    def validate_duration_minutes(self, value):
        if not 5 <= value <= 30:
            raise serializers.ValidationError("Süre 5-30 dakika arasında olmalıdır.")
        return value


class TempExamAnswerSerializer(serializers.Serializer):
    """Hızlı test cevapları için serializer"""

    uuid = serializers.UUIDField()
    answers = serializers.DictField(
        child=serializers.CharField(max_length=1),
        help_text="Soru ID'leri ve seçilen cevaplar: {'1': 'A', '2': 'C', ...}"
    )

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Cevaplar boş olamaz.")

        for question_id, answer in value.items():
            if not answer or not answer.strip():
                raise serializers.ValidationError(f"Soru {question_id} için cevap boş olamaz.")

            answer_letter = answer.upper()
            if answer_letter not in ['A', 'B', 'C', 'D', 'E']:
                raise serializers.ValidationError(
                    f"Soru {question_id} için geçersiz cevap: {answer}"
                )

        return {k: v.upper() for k, v in value.items()}


class TempExamResultSerializer(serializers.ModelSerializer):
    """Hızlı test sonuçları için serializer"""

    session_info = TempExamSessionSerializer(source='session', read_only=True)

    class Meta:
        model = TempExamResult
        fields = [
            'uuid', 'session', 'session_info', 'total_questions',
            'correct_count', 'wrong_count', 'percentage',
            'subject_breakdown', 'created_at', 'merged'
        ]
        read_only_fields = ['uuid', 'created_at', 'merged']


class ExamResultSerializer(serializers.ModelSerializer):
    """Kalıcı sınav sonuçları için serializer"""

    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ExamResult
        fields = [
            'id', 'user', 'username', 'exam_type', 'branch',
            'total_questions', 'correct_count', 'wrong_count',
            'percentage', 'subject_breakdown', 'is_quick_test',
            'source_uuid', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'source_uuid']


class RegisterAndMergeSerializer(serializers.Serializer):
    """Kayıt ve merge işlemi için serializer"""

    temp_result_uuid = serializers.UUIDField()
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_temp_result_uuid(self, value):
        try:
            temp_result = TempExamResult.objects.get(uuid=value, merged=False)
            self.temp_result = temp_result
        except TempExamResult.DoesNotExist:
            raise serializers.ValidationError("Geçersiz veya daha önce kullanılmış test sonucu.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu kullanıcı adı zaten kullanılıyor.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu e-posta adresi zaten kullanılıyor.")
        return value