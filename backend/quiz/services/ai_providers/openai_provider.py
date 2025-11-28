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


class OpenAIProvider(AIProviderBase):

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = None):
        super().__init__(api_key, model)
        self.base_url = base_url or "https://routellm.abacus.ai/v1"
        self.initialize_client()
    
    @property
    def name(self) -> str:
        return "openai"
    
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
            "gpt-4o": ProviderCost(0.0025, 0.010, 0.015),
            "gpt-4o-mini": ProviderCost(0.00015, 0.0006, 0.002),
            "gpt-4-turbo": ProviderCost(0.01, 0.03, 0.025),
        }
        return costs.get(self.model, ProviderCost(0.002, 0.006, 0.005))
    
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
            }
            
            if self.base_url:
                kwargs['base_url'] = self.base_url
            
            if ignore_ssl:
                kwargs['http_client'] = httpx.Client(verify=False)
            
            self._client = OpenAI(**kwargs)
            logger.info(f"OpenAI client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def test_connection(self) -> bool:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
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
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            result = json.loads(content)
            
            response_time = time.time() - start_time
            self.update_metrics(True, response_time, self.cost.avg_question_cost)
            
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
            response_time = time.time() - start_time
            self.update_metrics(False, response_time, 0)
            logger.error(f"OpenAI question generation failed: {e}")
            raise
