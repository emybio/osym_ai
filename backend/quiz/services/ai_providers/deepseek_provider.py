import json
import time
from typing import Dict, List
from openai import OpenAI
import httpx
import logging

from .base import (
    AIProviderBase,
    AIProviderCapability,
    QuestionType,
    ProviderCost
)

logger = logging.getLogger(__name__)


class DeepSeekProvider(AIProviderBase):

    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = None):
        super().__init__(api_key, model)
        self.base_url = base_url or "https://routellm.abacus.ai/v1"
        self.initialize_client()
    
    @property
    def name(self) -> str:
        return "deepseek"
    
    @property
    def capabilities(self) -> List[AIProviderCapability]:
        return [
            AIProviderCapability.TEXT_GENERATION,
            AIProviderCapability.MATH_REASONING,
            AIProviderCapability.JSON_MODE,
        ]
    
    @property
    def cost(self) -> ProviderCost:
        return ProviderCost(0.00014, 0.00028, 0.0003)
    
    @property
    def supported_question_types(self) -> List[QuestionType]:
        return [
            QuestionType.TEXT_ONLY,
        ]
    
    def initialize_client(self):
        try:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=httpx.Client(verify=False)
            )
            logger.info(f"DeepSeek client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {e}")
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
            logger.error(f"DeepSeek connection test failed: {e}")
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
            if question_type != QuestionType.TEXT_ONLY:
                raise ValueError(f"DeepSeek only supports TEXT_ONLY questions, got {question_type}")
            
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
                "svg": None,
                "source": self.name,
                "model": self.model,
                "is_fallback": False
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(False, response_time, 0)
            logger.error(f"DeepSeek question generation failed: {e}")
            raise
