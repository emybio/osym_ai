import json
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock

from quiz.models import Question, Subject, Difficulty, Topic


class QuestionGenerationIntegrationTest(APITestCase):
    """Integration tests for question generation workflow"""

    def setUp(self):
        self.topic = Topic.objects.create(name="Algebra")
        self.generate_url = reverse('generate-question')
        self.valid_payload = {
            "subject": Subject.MATEMATIK,
            "topic": "Algebra",
            "difficulty": Difficulty.MEDIUM,
            "provider": "openai"
        }

    @patch('quiz.services.ai_service.OpenAI')
    def test_complete_question_generation_flow(self, mock_openai):
        """Test the complete flow from API request to database storage"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "stem": "What is the derivative of x^2?",
            "choices": {
                "A": "x",
                "B": "2x",
                "C": "x^2",
                "D": "2x^2"
            },
            "answer": "B",
            "rubric": "The derivative of x^n is n*x^(n-1)"
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Make API request
        response = self.client.post(self.generate_url, self.valid_payload, format='json')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['stem'], "What is the derivative of x^2?")
        self.assertEqual(response.data['choices'], ["x", "2x", "x^2", "2x^2"])
        self.assertEqual(response.data['answer'], "B")
        self.assertEqual(response.data['source'], "openai")

        # Verify database storage
        question = Question.objects.get(id=response.data['id'])
        self.assertEqual(question.stem, "What is the derivative of x^2?")
        self.assertEqual(question.subject, Subject.MATEMATIK)
        self.assertEqual(question.difficulty, Difficulty.MEDIUM)

    @patch('quiz.services.ai_service.OpenAI')
    def test_question_explanation_flow(self, mock_openai):
        """Test the complete flow for question explanation"""
        # Create a question first
        question = Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Test question",
            choices=["A", "B", "C", "D"],
            answer="B",
            source="openai"
        )

        # Mock OpenAI explanation response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Step 1: Analyze the question\nStep 2: Find the solution"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Request explanation
        explain_url = reverse('explain-question', kwargs={'pk': question.id})
        response = self.client.post(explain_url, {"provider": "openai"}, format='json')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['explanation'], "Step 1: Analyze the question\nStep 2: Find the solution")

    def test_question_generation_with_invalid_data(self):
        """Test question generation with invalid request data"""
        invalid_payload = {
            "subject": "INVALID_SUBJECT",
            "topic": "",
            "difficulty": "INVALID_DIFFICULTY",
            "provider": "invalid_provider"
        }

        response = self.client.post(self.generate_url, invalid_payload, format='json')

        # Should handle errors gracefully
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])

    def test_explanation_for_nonexistent_question(self):
        """Test explanation request for non-existent question"""
        explain_url = reverse('explain-question', kwargs={'pk': 99999})
        response = self.client.post(explain_url, {"provider": "openai"}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuestionStatsIntegrationTest(APITestCase):
    """Integration tests for question statistics"""

    def setUp(self):
        self.topic = Topic.objects.create(name="Statistics")
        self.stats_url = reverse('question-stats')

        # Create test questions with different properties
        Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.EASY,
            stem="Easy math question",
            choices=["A", "B"],
            answer="A",
            source="openai"
        )
        Question.objects.create(
            subject=Subject.FIZIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Medium physics question",
            choices=["A", "B", "C"],
            answer="B",
            source="zai"
        )
        Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.HARD,
            stem="Hard math question",
            choices=["A", "B", "C", "D", "E"],
            answer="C",
            source="openai"
        )

    def test_question_statistics_endpoint(self):
        """Test the question statistics endpoint"""
        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stats = response.json()

        self.assertEqual(stats['total_questions'], 3)
        self.assertIn('by_subject', stats)
        self.assertIn('by_difficulty', stats)
        self.assertIn('by_source', stats)

        # Verify subject stats
        self.assertEqual(stats['by_subject']['Matematik'], 2)
        self.assertEqual(stats['by_subject']['Fizik'], 1)

        # Verify source stats
        self.assertEqual(stats['by_source']['openai'], 2)
        self.assertEqual(stats['by_source']['zai'], 1)


class CleanupIntegrationTest(TransactionTestCase):
    """Integration tests for cleanup functionality"""

    def setUp(self):
        from django.utils import timezone
        from datetime import timedelta

        self.topic = Topic.objects.create(name="Cleanup Test")
        self.cleanup_url = reverse('cleanup-questions')

        # Create old and new questions
        old_date = timezone.now() - timedelta(days=35)
        new_date = timezone.now() - timedelta(days=5)

        # Old question (should be deleted)
        self.old_question = Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=self.topic,
            difficulty=Difficulty.MEDIUM,
            stem="Old question",
            choices=["A", "B"],
            answer="A",
            source="openai",
            created_at=old_date
        )

        # New question (should remain)
        self.new_question = Question.objects.create(
            subject=Subject.FIZIK,
            topic=self.topic,
            difficulty=Difficulty.EASY,
            stem="New question",
            choices=["A", "B"],
            answer="B",
            source="zai",
            created_at=new_date
        )

        # Create admin user for testing
        from django.contrib.auth.models import User
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

    def test_cleanup_endpoint_as_admin(self):
        """Test cleanup endpoint with admin user"""
        self.client.force_authenticate(user=self.admin_user)

        # Initial count
        initial_count = Question.objects.count()
        self.assertEqual(initial_count, 2)

        # Run cleanup
        response = self.client.delete(f"{self.cleanup_url}?days_old=30")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('deleted_count', response.json())

        # Verify cleanup
        final_count = Question.objects.count()
        self.assertEqual(final_count, 1)
        self.assertTrue(Question.objects.filter(id=self.new_question.id).exists())
        self.assertFalse(Question.objects.filter(id=self.old_question.id).exists())

    def test_cleanup_endpoint_as_non_admin(self):
        """Test cleanup endpoint with non-admin user (should be forbidden)"""
        from django.contrib.auth.models import User
        regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=regular_user)

        response = self.client.delete(f"{self.cleanup_url}?days_old=30")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # No questions should be deleted
        self.assertEqual(Question.objects.count(), 2)

    def test_cleanup_endpoint_unauthenticated(self):
        """Test cleanup endpoint without authentication"""
        response = self.client.delete(f"{self.cleanup_url}?days_old=30")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # No questions should be deleted
        self.assertEqual(Question.objects.count(), 2)


class ErrorHandlingIntegrationTest(APITestCase):
    """Integration tests for error handling"""

    def setUp(self):
        self.generate_url = reverse('generate-question')

    @patch('quiz.services.ai_service.OpenAI')
    def test_openai_api_error_handling(self, mock_openai):
        """Test handling of OpenAI API errors"""
        # Mock OpenAI to raise an exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client

        payload = {
            "subject": Subject.MATEMATIK,
            "topic": "Test",
            "difficulty": Difficulty.MEDIUM,
            "provider": "openai"
        }

        response = self.client.post(self.generate_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('error', response.json())

    @patch('quiz.services.ai_service.ZaiClient')
    def test_zai_fallback_mechanism(self, mock_zai_client):
        """Test fallback from Z.ai to OpenAI"""
        from unittest.mock import MagicMock

        # Mock Z.ai to fail
        zai_instance = MagicMock()
        zai_instance.chat.completions.create.side_effect = Exception("Z.ai Error")
        mock_zai_client.return_value = zai_instance

        # Mock OpenAI to succeed
        with patch('quiz.services.ai_service.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "stem": "Fallback question",
                "choices": ["A", "B"],
                "answer": "A"
            })
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            payload = {
                "subject": Subject.MATEMATIK,
                "topic": "Test",
                "difficulty": Difficulty.MEDIUM,
                "provider": "zai"
            }

            response = self.client.post(self.generate_url, payload, format='json')

            # Should succeed with fallback
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.json()['source'], 'openai')  # Should be from fallback

    def test_database_constraint_handling(self):
        """Test handling of database constraint violations"""
        # Create a question first
        topic = Topic.objects.create(name="Test Topic")
        question = Question.objects.create(
            subject=Subject.MATEMATIK,
            topic=topic,
            difficulty=Difficulty.MEDIUM,
            stem="Test question",
            choices=["A", "B"],
            answer="A",
            source="openai"
        )

        # Mock AI service to return invalid data that would violate constraints
        with patch('quiz.services.question_service.ai_service') as mock_ai:
            mock_ai.generate_question.return_value = {
                "stem": "",  # Empty stem should violate constraints
                "choices": [],  # Empty choices should violate constraints
                "answer": "",
                "rubric": "",
                "source": "openai"
            }

            payload = {
                "subject": Subject.MATEMATIK,
                "topic": "Test Topic",
                "difficulty": Difficulty.MEDIUM,
                "provider": "openai"
            }

            response = self.client.post(self.generate_url, payload, format='json')

            # Should handle the error gracefully
            self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_502_BAD_GATEWAY])