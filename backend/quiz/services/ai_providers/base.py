from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    TEXT_ONLY = "text_only"
    SIMPLE_VISUAL = "simple_visual"
    COMPLEX_VISUAL = "complex_visual"
    PARABOLA = "parabola"
    GEOMETRY = "geometry"
    FUNCTION_GRAPH = "function_graph"


class AIProviderCapability(Enum):
    TEXT_GENERATION = "text_generation"
    VISUAL_GENERATION = "visual_generation"
    SVG_GENERATION = "svg_generation"
    TURKISH_LANGUAGE = "turkish_language"
    MATH_REASONING = "math_reasoning"
    JSON_MODE = "json_mode"


@dataclass
class ProviderCost:
    input_cost_per_1k: float
    output_cost_per_1k: float
    avg_question_cost: float


@dataclass
class ProviderMetrics:
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    total_cost: float = 0.0


class AIProviderBase(ABC):
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model
        self.metrics = ProviderMetrics()
        self._client = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[AIProviderCapability]:
        pass
    
    @property
    @abstractmethod
    def cost(self) -> ProviderCost:
        pass
    
    @property
    @abstractmethod
    def supported_question_types(self) -> List[QuestionType]:
        pass
    
    @abstractmethod
    def initialize_client(self):
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass
    
    def can_handle(self, question_type: QuestionType) -> bool:
        return question_type in self.supported_question_types
    
    def has_capability(self, capability: AIProviderCapability) -> bool:
        return capability in self.capabilities
    
    def update_metrics(self, success: bool, response_time: float, cost: float):
        self.metrics.total_requests += 1
        if not success:
            self.metrics.failed_requests += 1
        self.metrics.total_cost += cost
        
        if self.metrics.total_requests > 0:
            self.metrics.success_rate = (
                (self.metrics.total_requests - self.metrics.failed_requests) 
                / self.metrics.total_requests
            )
        
        if self.metrics.avg_response_time == 0:
            self.metrics.avg_response_time = response_time
        else:
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.total_requests - 1) + response_time)
                / self.metrics.total_requests
            )
    
    def get_metrics(self) -> Dict:
        return {
            'provider': self.name,
            'success_rate': f"{self.metrics.success_rate * 100:.2f}%",
            'avg_response_time': f"{self.metrics.avg_response_time:.2f}s",
            'total_requests': self.metrics.total_requests,
            'failed_requests': self.metrics.failed_requests,
            'total_cost': f"${self.metrics.total_cost:.4f}"
        }
