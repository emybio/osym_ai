import json
import time
from typing import Dict, List
from openai import OpenAI
import httpx
import os
import logging

from .base import (
    AIProviderBase,
    AIProviderCapability,
    QuestionType,
    ProviderCost
)

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProviderBase):

    def __init__(self, api_key: str, model: str = "claude-opus-4-5-20251101", base_url: str = None):
        super().__init__(api_key, model)
        self.base_url = base_url or "https://routellm.abacus.ai/v1"
        self.initialize_client()

    @property
    def name(self) -> str:
        return "claude"

    @property
    def capabilities(self) -> List[AIProviderCapability]:
        return [
            AIProviderCapability.TEXT_GENERATION,
            AIProviderCapability.VISUAL_GENERATION,
            AIProviderCapability.SVG_GENERATION,
            AIProviderCapability.TURKISH_LANGUAGE,
            AIProviderCapability.MATH_REASONING,
            AIProviderCapability.JSON_MODE,
        ]

    @property
    def cost(self) -> ProviderCost:
        costs = {
            "claude-3-5-sonnet-20241022": ProviderCost(0.003, 0.015, 0.012),
            "claude-3-opus-20240229": ProviderCost(0.015, 0.075, 0.050),
            "claude-3-sonnet-20240229": ProviderCost(0.003, 0.015, 0.012),
            "claude-3-haiku-20240307": ProviderCost(0.00025, 0.00125, 0.001),
        }
        return costs.get(self.model, ProviderCost(0.003, 0.015, 0.012))

    @property
    def supported_question_types(self) -> List[QuestionType]:
        return [
            QuestionType.TEXT_ONLY,
            QuestionType.SIMPLE_VISUAL,
            QuestionType.COMPLEX_VISUAL,
            QuestionType.PARABOLA,
            QuestionType.GEOMETRY,
            QuestionType.FUNCTION_GRAPH,
        ]

    def initialize_client(self):
        try:
            ignore_ssl = os.getenv('IGNORE_SSL', 'False').lower() in ('true', '1', 'yes')

            kwargs = {
                'api_key': self.api_key,
                'base_url': self.base_url,
            }

            if ignore_ssl:
                kwargs['http_client'] = httpx.Client(verify=False)

            self._client = OpenAI(**kwargs)
            logger.info(f"Claude client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
            raise

    def test_connection(self) -> bool:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            logger.info(f"Claude connection test successful for model: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            return False

    def generate_question(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        question_type: QuestionType = QuestionType.TEXT_ONLY,
        system_prompt: str = None,
        user_prompt: str = None,
        json_mode: bool = True
    ) -> Dict:
        start_time = time.time()
        self.metrics.total_requests += 1

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content

            if json_mode:
                result = json.loads(content)
            else:
                result = {"stem": content}

            response_time = time.time() - start_time
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.total_requests - 1) + response_time)
                / self.metrics.total_requests
            )

            self.metrics.total_cost += self.cost.avg_question_cost
            self.metrics.success_rate = (
                (self.metrics.total_requests - self.metrics.failed_requests)
                / self.metrics.total_requests
            )

            return {
                "stem": result.get("stem", ""),
                "choices": result.get("choices", []),
                "answer": result.get("answer", "A"),
                "rubric": result.get("rubric", ""),
                "svg": result.get("svg", None),
                "source": self.name,
                "model": self.model,
                "is_fallback": False
            }

        except Exception as e:
            self.metrics.failed_requests += 1
            logger.error(f"Claude question generation failed: {e}")
            raise
