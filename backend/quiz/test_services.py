import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError

from quiz.services.ai_service import AIService, AIProviderError
from quiz.services.question_service import QuestionService
from quiz.models import Question, Subject, Difficulty, Topic
from quiz.serializers import QuestionSerializer


class AIServiceTest(TestCase):
    """Test cases for AIService"""

    def setUp(self):
        self.ai_service = AIService()

    @patch('quiz.services.ai_service.OpenAI')
    @patch('quiz.services.ai_service.settings')
    def test_init_openai_client(self, mock_settings, mock_openai):
        """Test OpenAI client initialization"""
        mock_settings.OPENAI_API_KEY = 'test-key'
        mock_openai.return_value = Mock()

        service = AIService()

        self.assertIsNotNone(service.openai_client)
        mock_openai.assert_called_once_with(api_key='test-key')

    @patch('quiz.services.ai_service.settings')
    def test_init_openai_client_no_key(self, mock_settings):
        """Test OpenAI client initialization without API key"""
        mock_settings.OPENAI_API_KEY = None

        service = AIService()

        self.assertIsNone(service.openai_client)

    def test_format_choices_list(self):
        """Test choice formatting from list"""
        choices = ["A", "B", "C", "D"]
        result = self.ai_service._format_choices(choices)
        self.assertEqual(result, choices)

    def test_format_choices_dict(self):
        """Test choice formatting from dictionary"""
        choices = {"A": "Choice A", "B": "Choice B", "C": "Choice C"}
        result = self.ai_service._format_choices(choices)
        self.assertEqual(result, ["Choice A", "Choice B", "Choice C"])

    def test_format_choices_empty(self):
        """Test choice formatting with empty input"""
        result = self.ai_service._format_choices(None)
        self.assertEqual(result, [])

    @patch.object(AIService, '_get_ai_response')
    def test_generate_question_success(self, mock_get_response):
        """Test successful question generation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "stem": "Test question",
            "choices": {"A": "Option A", "B": "Option B"},
            "answer": "A",
            "rubric": "Test rubric"
        })
        mock_get_response.return_value = mock_response

        result = self.ai_service.generate_question("MAT", "Algebra", "M", "openai")

        self.assertEqual(result["stem"], "Test question")
        self.assertEqual(result["choices"], ["Option A", "Option B"])
        self.assertEqual(result["answer"], "A")
        self.assertEqual(result["source"], "openai")

    @patch.object(AIService, '_get_ai_response')
    def test_generate_question_invalid_json(self, mock_get_response):
        """Test question generation with invalid JSON response"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json"
        mock_get_response.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            self.ai_service.generate_question("MAT", "Algebra", "M", "openai")

    @patch.object(AIService, '_get_ai_response')
    def test_explain_question_success(self, mock_get_response):
        """Test successful question explanation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Step by step explanation"
        mock_get_response.return_value = mock_response

        result = self.ai_service.explain_question("Test question", ["A", "B"], "openai")

        self.assertEqual(result, "Step by step explanation")

    def test_get_ai_response_unsupported_provider(self):
        """Test AI response with unsupported provider"""
        with self.assertRaises(ValueError):
            self.ai_service._get_ai_response("unsupported", [])

    @patch.object(AIService, '_get_openai_response')
    @patch.object(AIService, '_get_zai_response')
    def test_fallback_mechanism(self, mock_zai, mock_openai):
        """Test fallback from Z.ai to OpenAI"""
        mock_zai.side_effect = AIProviderError("Z.ai error", provider="zai")
        mock_openai.return_value = Mock()

        # Create a new service with both clients mocked
        service = AIService()
        service.openai_client = Mock()
        service.zai_client = Mock()

        with patch.object(service, '_get_zai_response', mock_zai):
            with patch.object(service, '_get_openai_response', mock_openai):
                result = service._get_ai_response("zai", [], json_mode=True)

        mock_zai.assert_called_once()
        mock_openai.assert_called_once()


class QuestionServiceTest(TestCase):
    """Test cases for QuestionService"""

    def setUp(self):
        self.topic = Topic.objects.create(name="Test Topic")

    @patch('quiz.services.question_service.ai_service')
    def test_generate_question_success(self, mock_ai_service):
        """Test successful question generation and creation"""
        mock_ai_service.generate_question.return_value = {
            "stem": "Test question",
            "choices": ["A", "B", "C", "D"],
            "answer": "A",
            "rubric": "Test rubric",
            "source": "openai"
        }

        data = {
            "subject": Subject.MATEMATIK,
            "topic": "Test Topic",
            "difficulty": Difficulty.MEDIUM,
            "provider": "openai"
        }

        question, error = QuestionService.generate_question(data)

        self.assertIsNone(error)
        self.assertIsNotNone(question)
        self.assertEqual(question.stem, "Test question")
        self.assertEqual(question.subject, Subject.MATEMATIK)
        self.assertEqual(question.source, "openai")

    @patch('quiz.services.question_service.ai_service')
    def test_generate_question_ai_error(self, mock_ai_service):
        """Test question generation with AI service error"""
        mock_ai_service.generate_question.side_effect = AIProviderError("AI Error")

        data = {
            "subject": Subject.MATEMATIK,
            "topic": "Test Topic",
            "difficulty": Difficulty.MEDIUM,
            "provider": "openai"
        }

        question, error = QuestionService.generate_question(data)

        self.assertIsNone(question)
        self.assertIsNotNone(error)
        self.assertIn("AI sağlayıcı hatası", error)

    def test_explain_question_success(self):
        """Test successful question explanation"""
        question = Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Test question",
            choices=["A", "B", "C", "D"],
            answer="A",
            source="openai"
        )

        with patch('quiz.services.question_service.ai_service') as mock_ai:
            mock_ai.explain_question.return_value = "Explanation text"

            result, error = QuestionService.explain_question(question.id, "openai")

            self.assertIsNone(error)
            self.assertEqual(result, "Explanation text")

    def test_explain_question_not_found(self):
        """Test explanation for non-existent question"""
        result, error = QuestionService.explain_question(99999, "openai")

        self.assertIsNone(result)
        self.assertEqual(error, "Soru bulunamadı")

    def test_get_question_stats(self):
        """Test getting question statistics"""
        # Create test questions
        Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Question 1",
            choices=["A", "B"],
            answer="A",
            source="openai"
        )
        Question.objects.create(
            subject=Subject.FIZIK,
            topic=self.topic,
            difficulty=Difficulty.EASY,
            stem="Question 2",
            choices=["A", "B"],
            answer="B",
            source="zai"
        )

        stats = QuestionService.get_question_stats()

        self.assertEqual(stats["total_questions"], 2)
        self.assertIn("Matematik", stats["by_subject"])
        self.assertIn("Fizik", stats["by_subject"])
        self.assertIn("openai", stats["by_source"])
        self.assertIn("zai", stats["by_source"])

    def test_delete_old_questions(self):
        """Test deletion of old questions"""
        from django.utils import timezone
        from datetime import timedelta

        # Create old question
        old_date = timezone.now() - timedelta(days=35)
        old_question = Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Old question",
            choices=["A", "B"],
            answer="A",
            source="openai",
            created_at=old_date
        )
        old_question.created_at = old_date
        old_question.save()

        # Create recent question
        Question.objects.create(
            subject=Subject.FIZIK,
            topic=self.topic,
            difficulty=Difficulty.EASY,
            stem="Recent question",
            choices=["A", "B"],
            answer="B",
            source="zai"
        )

        deleted_count = QuestionService.delete_old_questions(30)

        self.assertEqual(deleted_count, 1)
        self.assertEqual(Question.objects.count(), 1)
        self.assertTrue(Question.objects.filter(subject=Subject.FIZIK).exists())


class QuestionSerializerTest(TestCase):
    """Test cases for QuestionSerializer"""

    def setUp(self):
        self.topic = Topic.objects.create(name="Test Topic")
        self.valid_data = {
            "subject": Subject.MATEMATIK,
            "topic": self.topic,
            "difficulty": Difficulty.MEDIUM,
            "stem": "What is 2+2?",
            "choices": ["3", "4", "5", "6"],
            "answer": "B",
            "source": "openai"
        }

    def test_valid_question_serialization(self):
        """Test serialization of valid question data"""
        question = Question.objects.create(**self.valid_data)
        serializer = QuestionSerializer(question)

        self.assertIn('id', serializer.data)
        self.assertIn('choices_display', serializer.data)
        self.assertEqual(serializer.data['stem'], "What is 2+2?")

    def test_validate_stem_success(self):
        """Test successful stem validation"""
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_validate_stem_too_short(self):
        """Test stem validation with too short text"""
        self.valid_data['stem'] = "Short"
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('stem', serializer.errors)

    def test_validate_choices_success(self):
        """Test successful choices validation"""
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_validate_choices_too_few(self):
        """Test choices validation with too few choices"""
        self.valid_data['choices'] = ["A"]
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('choices', serializer.errors)

    def test_validate_choices_duplicates(self):
        """Test choices validation with duplicate choices"""
        self.valid_data['choices'] = ["Same", "Same", "Different"]
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('choices', serializer.errors)

    def test_validate_answer_success(self):
        """Test successful answer validation"""
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_validate_answer_invalid(self):
        """Test answer validation with invalid answer"""
        self.valid_data['answer'] = "X"
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('answer', serializer.errors)

    def test_cross_field_validation(self):
        """Test cross-field validation between choices and answer"""
        self.valid_data['choices'] = ["A", "B"]  # Only 2 choices
        self.valid_data['answer'] = "D"  # Invalid choice index
        serializer = QuestionSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)