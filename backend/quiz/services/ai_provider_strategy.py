import random
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .ai_providers.base import AIProviderBase, QuestionType

logger = logging.getLogger(__name__)


@dataclass
class SubjectStrategy:
    text_ratio: float
    simple_visual_ratio: float
    complex_visual_ratio: float
    text_provider: str
    simple_visual_provider: str
    complex_visual_provider: str


class AIProviderStrategy:
    
    SUBJECT_STRATEGIES = {
        'matematik': SubjectStrategy(
            text_ratio=0.60,
            simple_visual_ratio=0.25,
            complex_visual_ratio=0.15,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'geometri': SubjectStrategy(
            text_ratio=0.30,
            simple_visual_ratio=0.40,
            complex_visual_ratio=0.30,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'fizik': SubjectStrategy(
            text_ratio=0.50,
            simple_visual_ratio=0.30,
            complex_visual_ratio=0.20,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'kimya': SubjectStrategy(
            text_ratio=0.70,
            simple_visual_ratio=0.20,
            complex_visual_ratio=0.10,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'biyoloji': SubjectStrategy(
            text_ratio=0.65,
            simple_visual_ratio=0.25,
            complex_visual_ratio=0.10,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'turkce': SubjectStrategy(
            text_ratio=0.90,
            simple_visual_ratio=0.08,
            complex_visual_ratio=0.02,
            text_provider='openai',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'tarih': SubjectStrategy(
            text_ratio=0.85,
            simple_visual_ratio=0.12,
            complex_visual_ratio=0.03,
            text_provider='openai',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
        'cografya': SubjectStrategy(
            text_ratio=0.65,
            simple_visual_ratio=0.25,
            complex_visual_ratio=0.10,
            text_provider='deepseek',
            simple_visual_provider='claude',
            complex_visual_provider='openai'
        ),
    }
    
    QUESTION_TYPE_MAPPING = {
        'parabola': QuestionType.COMPLEX_VISUAL,
        'geometry': QuestionType.SIMPLE_VISUAL,
        'function_graph': QuestionType.COMPLEX_VISUAL,
        'text': QuestionType.TEXT_ONLY,
        'general': QuestionType.TEXT_ONLY,
    }
    
    def __init__(self, providers: Dict[str, AIProviderBase]):
        self.providers = providers
        self._validate_providers()
    
    def _validate_providers(self):
        required_providers = {'openai', 'claude', 'deepseek'}
        available_providers = set(self.providers.keys())
        
        missing = required_providers - available_providers
        if missing:
            logger.warning(f"Missing providers: {missing}. Some strategies may not work.")
    
    def select_provider(
        self,
        subject: str,
        question_type: Optional[str] = None,
        force_provider: Optional[str] = None
    ) -> AIProviderBase:
        
        if force_provider:
            if force_provider in self.providers:
                logger.info(f"Using forced provider: {force_provider}")
                return self.providers[force_provider]
            else:
                logger.warning(f"Forced provider '{force_provider}' not available, using strategy")
        
        subject_lower = subject.lower()
        strategy = self.SUBJECT_STRATEGIES.get(subject_lower)
        
        if not strategy:
            logger.warning(f"No strategy for subject '{subject}', using default")
            strategy = self.SUBJECT_STRATEGIES['matematik']
        
        if question_type:
            q_type = self.QUESTION_TYPE_MAPPING.get(question_type.lower(), QuestionType.TEXT_ONLY)
        else:
            q_type = self._determine_question_type_by_ratio(strategy)
        
        provider_name = self._get_provider_for_question_type(strategy, q_type)
        
        provider = self.providers.get(provider_name)
        
        if not provider or not provider.can_handle(q_type):
            logger.warning(f"Provider '{provider_name}' cannot handle {q_type}, finding fallback")
            provider = self._find_fallback_provider(q_type)
        
        logger.info(f"Selected provider: {provider.name} for {subject}/{q_type.value}")
        return provider
    
    def _determine_question_type_by_ratio(self, strategy: SubjectStrategy) -> QuestionType:
        rand = random.random()
        
        if rand < strategy.text_ratio:
            return QuestionType.TEXT_ONLY
        elif rand < strategy.text_ratio + strategy.simple_visual_ratio:
            return QuestionType.SIMPLE_VISUAL
        else:
            return QuestionType.COMPLEX_VISUAL
    
    def _get_provider_for_question_type(
        self,
        strategy: SubjectStrategy,
        question_type: QuestionType
    ) -> str:
        if question_type == QuestionType.TEXT_ONLY:
            return strategy.text_provider
        elif question_type in [QuestionType.SIMPLE_VISUAL, QuestionType.GEOMETRY]:
            return strategy.simple_visual_provider
        else:
            return strategy.complex_visual_provider
    
    def _find_fallback_provider(self, question_type: QuestionType) -> AIProviderBase:
        for provider in self.providers.values():
            if provider.can_handle(question_type):
                logger.info(f"Found fallback provider: {provider.name}")
                return provider
        
        logger.error(f"No provider can handle {question_type}, using first available")
        return list(self.providers.values())[0]
    
    def get_cost_estimate(self, subject: str, num_questions: int = 1000) -> Dict:
        subject_lower = subject.lower()
        strategy = self.SUBJECT_STRATEGIES.get(subject_lower, self.SUBJECT_STRATEGIES['matematik'])
        
        text_count = int(num_questions * strategy.text_ratio)
        simple_visual_count = int(num_questions * strategy.simple_visual_ratio)
        complex_visual_count = int(num_questions * strategy.complex_visual_ratio)
        
        text_provider = self.providers.get(strategy.text_provider)
        simple_provider = self.providers.get(strategy.simple_visual_provider)
        complex_provider = self.providers.get(strategy.complex_visual_provider)
        
        text_cost = text_count * text_provider.cost.avg_question_cost if text_provider else 0
        simple_cost = simple_visual_count * simple_provider.cost.avg_question_cost if simple_provider else 0
        complex_cost = complex_visual_count * complex_provider.cost.avg_question_cost if complex_provider else 0
        
        total_cost = text_cost + simple_cost + complex_cost
        
        return {
            'subject': subject,
            'total_questions': num_questions,
            'breakdown': {
                'text_only': {
                    'count': text_count,
                    'provider': strategy.text_provider,
                    'cost': f"${text_cost:.4f}"
                },
                'simple_visual': {
                    'count': simple_visual_count,
                    'provider': strategy.simple_visual_provider,
                    'cost': f"${simple_cost:.4f}"
                },
                'complex_visual': {
                    'count': complex_visual_count,
                    'provider': strategy.complex_visual_provider,
                    'cost': f"${complex_cost:.4f}"
                }
            },
            'total_cost': f"${total_cost:.4f}",
            'cost_per_question': f"${total_cost / num_questions:.6f}"
        }
    
    def get_all_metrics(self) -> List[Dict]:
        return [provider.get_metrics() for provider in self.providers.values()]
