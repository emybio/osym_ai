import json
import os
from typing import Iterable, List
import logging

from django.conf import settings
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class AIProviderError(Exception):
    """Base exception for AI provider errors"""
    def __init__(self, message, provider=None, original_error=None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)

class AIService:
    """Service for managing AI providers and requests"""

    def __init__(self):
        self.openai_client = self._init_openai_client()
        self.zai_client = self._init_zai_client()
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.zai_model = os.getenv("ZAI_MODEL", "glm-4.5")

    def _init_openai_client(self):
        """Initialize OpenAI client if API key is available"""
        if settings.OPENAI_API_KEY:
            return OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.warning("OPENAI_API_KEY not configured")
        return None

    def _init_zai_client(self):
        """Initialize Z.ai client if API key is available"""
        try:
            if getattr(settings, "ZAI_API_KEY", None):
                from zai._client import ZaiClient
                return ZaiClient(api_key=settings.ZAI_API_KEY)
        except ImportError:
            logger.warning("Z.ai SDK not available")
        except Exception as e:
            logger.warning(f"Failed to initialize Z.ai client: {e}")
        return None

    def _format_choices(self, options) -> List[str]:
        """Format choices from various formats to list of strings"""
        if not options:
            return []
        if isinstance(options, list):
            return [opt for opt in options if opt]
        ordered = []
        for key in ["A", "B", "C", "D", "E"]:
            if options.get(key):
                ordered.append(options[key])
        return ordered

    def _get_ai_response(self, provider: str, messages: Iterable[dict], *, json_mode: bool = False):
        """Get response from AI provider with fallback mechanism"""
        try:
            if provider == "zai":
                return self._get_zai_response(messages, json_mode=json_mode)
            elif provider == "openai":
                return self._get_openai_response(messages, json_mode=json_mode)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except AIProviderError as e:
            if provider == "zai" and self.openai_client:
                logger.info(f"Falling back from Z.ai to OpenAI: {e}")
                try:
                    return self._get_openai_response(messages, json_mode=json_mode)
                except AIProviderError:
                    logger.warning("Both Z.ai and OpenAI failed, using mock mode")
                    return self._get_mock_response(messages, json_mode=json_mode)
            else:
                logger.warning(f"AI provider {provider} failed, using mock mode: {e}")
                return self._get_mock_response(messages, json_mode=json_mode)

    def _get_mock_response(self, messages: Iterable[dict], *, json_mode: bool = False):
        """Get mock response when all AI providers fail"""
        from .mock_service import get_mock_question, get_mock_explanation

        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        class MockChoice:
            def __init__(self, content):
                self.message = MockMessage(content)

        class MockMessage:
            def __init__(self, content):
                self.content = content

        if json_mode:
            mock_data = get_mock_question()
            content = json.dumps(mock_data)
        else:
            content = json.dumps(get_mock_explanation("Mock question", ["A", "B", "C", "D", "E"]))

        return MockResponse(content)

    def _get_zai_response(self, messages: Iterable[dict], *, json_mode: bool = False):
        """Get response from Z.ai API"""
        if not self.zai_client:
            raise AIProviderError("Z.ai client not initialized", provider="zai")

        try:
            response = self.zai_client.chat.completions.create(
                model=self.zai_model,
                messages=list(messages),
                response_format={"type": "json_object"} if json_mode else None,
                temperature=0.5,
                max_tokens=800,
            )
            return response
        except Exception as e:
            logger.error(f"Z.ai API error: {e}")
            raise AIProviderError(f"Z.ai API error: {str(e)}", provider="zai", original_error=e)

    def _get_openai_response(self, messages: Iterable[dict], *, json_mode: bool = False):
        """Get response from OpenAI API"""
        if not self.openai_client:
            raise AIProviderError("OpenAI client not initialized", provider="openai")

        try:
            kwargs = {
                "model": self.default_model,
                "messages": list(messages),
                "max_tokens": 800,
                "temperature": 0.5,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.openai_client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIProviderError(f"OpenAI API error: {str(e)}", provider="openai", original_error=e)

    def generate_question(self, subject: str, topic: str, difficulty: str, provider: str = "openai"):
        """Generate a question using specified AI provider"""
        try:
            from ..prompts import SYSTEM_PROMPT, USER_TEMPLATE
        except ImportError:
            # Fallback prompts if prompts.py is not available
            SYSTEM_PROMPT = "Sen TYT sınavları için soru üreten bir yapay zekasın."
            USER_TEMPLATE = "Subject: {subject}\nTopic: {topic}\nDifficulty: {difficulty}\nGenerate a multiple choice question."

        prompt = USER_TEMPLATE.format(subject=subject, topic=topic, difficulty=difficulty)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        completion = self._get_ai_response(provider, messages, json_mode=True)
        content = completion.choices[0].message.content
        payload = json.loads(content)

        return {
            "stem": payload.get("stem", ""),
            "choices": self._format_choices(payload.get("choices")),
            "answer": (payload.get("answer", "") or "A")[0],
            "rubric": payload.get("rubric", ""),
            "source": provider,
        }

    def explain_question(self, question_text: str, choices: List[str], provider: str = "openai"):
        """Generate explanation for a question"""
        user_message = f"Soruyu adım adım açıkla: {question_text}\nSeçenekler: {choices}"

        messages = [
            {"role": "system", "content": "Kısa, sade ve adım adım açıklama yap."},
            {"role": "user", "content": user_message},
        ]

        completion = self._get_ai_response(provider, messages)
        return completion.choices[0].message.content

# Singleton instance
ai_service = AIService()