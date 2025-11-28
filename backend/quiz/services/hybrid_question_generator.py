import logging
from typing import Dict, Optional
from django.conf import settings

from .ai_providers import OpenAIProvider, ClaudeProvider, DeepSeekProvider
from .ai_providers.base import QuestionType
from .ai_provider_strategy import AIProviderStrategy
from .question_validation_system import QuestionValidationSystem, ValidationStatus

logger = logging.getLogger(__name__)


class HybridQuestionGenerator:

    def __init__(self, max_validation_attempts: int = 3):
        self.providers = self._initialize_providers()
        self.strategy = AIProviderStrategy(self.providers)
        self.validator = QuestionValidationSystem()
        self.max_validation_attempts = max_validation_attempts

    def _initialize_providers(self) -> Dict:
        providers = {}

        # AbacusAI ortak API anahtarı ile provider'ları başlat
        api_key = getattr(settings, 'ABACUSAI_API_KEY', None)
        if api_key and api_key != 'xxx' and api_key.startswith('s2_'):
            try:
                # OpenAI (GPT)
                providers['openai'] = OpenAIProvider(
                    api_key=api_key,
                    model="gpt-4o-mini"
                )
                logger.info("OpenAI provider initialized via AbacusAI")

                # Claude
                providers['claude'] = ClaudeProvider(
                    api_key=api_key,
                    model="claude-opus-4-5-20251101"
                )
                logger.info("Claude provider initialized via AbacusAI")

                # DeepSeek
                providers['deepseek'] = DeepSeekProvider(
                    api_key=api_key,
                    model="deepseek-chat"
                )
                logger.info("DeepSeek provider initialized via AbacusAI")

            except Exception as e:
                logger.error(f"Failed to initialize providers via AbacusAI: {e}")
        else:
            logger.error("AbacusAI API key not properly configured")
            logger.error(f"ABACUSAI_API_KEY value: {api_key}")
            if not api_key:
                logger.error("ABACUSAI_API_KEY not found in settings")
            elif not api_key.startswith('s2_'):
                logger.error("ABACUSAI_API_KEY must start with 's2_'")

        if not providers:
            logger.error("No AI providers initialized!")
            raise RuntimeError("At least one AI provider must be configured")

        logger.info(f"Initialized providers: {list(providers.keys())}")
        return providers
    
    def generate_validated_question(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        question_type: Optional[str] = None,
        force_provider: Optional[str] = None,
        system_prompt: str = None,
        user_prompt: str = None
    ) -> Dict:
        
        for attempt in range(1, self.max_validation_attempts + 1):
            try:
                logger.info(f"Generation attempt {attempt}/{self.max_validation_attempts}")
                
                provider = self.strategy.select_provider(
                    subject=subject,
                    question_type=question_type,
                    force_provider=force_provider
                )
                
                if not system_prompt or not user_prompt:
                    system_prompt, user_prompt = self._get_default_prompts(
                        subject, topic, difficulty, question_type
                    )
                
                q_type = self._determine_question_type(question_type, provider)
                
                question_data = provider.generate_question(
                    subject=subject,
                    topic=topic,
                    difficulty=difficulty,
                    question_type=q_type,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    json_mode=True
                )
                
                validation_result = self.validator.validate_question(
                    question_data=question_data,
                    question_type=question_type or 'general'
                )
                
                if validation_result.is_valid():
                    logger.info(f"Question validated successfully on attempt {attempt}")
                    question_data['validation'] = {
                        'status': 'passed',
                        'score': validation_result.score,
                        'attempt': attempt
                    }
                    return question_data
                else:
                    logger.warning(
                        f"Validation failed on attempt {attempt}: "
                        f"Score {validation_result.score}/100, "
                        f"Errors: {len(validation_result.errors)}"
                    )
                    
                    if attempt < self.max_validation_attempts:
                        feedback = self._generate_feedback(validation_result)
                        user_prompt += f"\n\nÖNCEKİ HATA: {feedback}\nLütfen bu hataları düzelterek yeni bir soru üret."
                    else:
                        logger.error(f"Max validation attempts reached. Returning last question with warnings.")
                        question_data['validation'] = {
                            'status': 'failed',
                            'score': validation_result.score,
                            'errors': [str(e) for e in validation_result.errors],
                            'warnings': [str(w) for w in validation_result.warnings],
                            'attempt': attempt
                        }
                        return question_data
            
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {e}")
                if attempt == self.max_validation_attempts:
                    raise
        
        raise RuntimeError("Failed to generate valid question after all attempts")
    
    def _determine_question_type(self, question_type: Optional[str], provider) -> QuestionType:
        if not question_type:
            return QuestionType.TEXT_ONLY
        
        type_map = {
            'parabola': QuestionType.PARABOLA,
            'geometry': QuestionType.GEOMETRY,
            'function_graph': QuestionType.FUNCTION_GRAPH,
            'text': QuestionType.TEXT_ONLY,
            'general': QuestionType.TEXT_ONLY,
        }
        
        return type_map.get(question_type.lower(), QuestionType.TEXT_ONLY)
    
    def _get_default_prompts(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        question_type: Optional[str]
    ) -> tuple:
        try:
            from ..prompts import SYSTEM_PROMPT, generate_user_prompt
            system = SYSTEM_PROMPT
            user = generate_user_prompt(subject, topic, difficulty)
        except ImportError:
            system = "Sen TYT sınavları için soru üreten bir yapay zekasın."
            user = f"Konu: {subject} - {topic}\nZorluk: {difficulty}\n\nLütfen 5 şıklı bir soru üret."
        
        if question_type and question_type != 'text':
            user += f"\n\nSoru tipi: {question_type}. Lütfen uygun SVG görseli de üret."
        
        return system, user
    
    def _generate_feedback(self, validation_result) -> str:
        feedback_parts = []
        
        for error in validation_result.errors[:3]:
            feedback_parts.append(f"- {error}")
        
        return " ".join(feedback_parts)
    
    def get_cost_estimate(self, subject: str, num_questions: int = 1000) -> Dict:
        return self.strategy.get_cost_estimate(subject, num_questions)
    
    def get_provider_metrics(self) -> list:
        return self.strategy.get_all_metrics()
    
    def test_all_providers(self) -> Dict:
        results = {}
        for name, provider in self.providers.items():
            try:
                success = provider.test_connection()
                results[name] = {
                    'status': 'connected' if success else 'failed',
                    'model': provider.model
                }
            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e)
                }
        return results
