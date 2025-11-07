import json
import os
import re
import random
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
        self.zai_model = os.getenv("ZAI_MODEL", "glm-4-plus")

    def _init_openai_client(self):
        """Initialize OpenAI client if API key is available"""
        if settings.OPENAI_API_KEY:
            # Disable SSL verification for development environments
            import httpx
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=httpx.Client(verify=False) if os.getenv('IGNORE_SSL', 'False').lower() in ('true', '1', 'yes') else None
            )
            return client
        logger.warning("OPENAI_API_KEY not configured")
        return None

    def _init_zai_client(self):
        """Initialize Z.ai client if API key is available"""
        try:
            if getattr(settings, "ZAI_API_KEY", None):
                from zai._client import ZaiClient
                return ZaiClient(
                    api_key=settings.ZAI_API_KEY,
                    base_url="https://api.z.ai/api/anthropic/v1"
                )
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
            cleaned_choices = [opt for opt in options if opt]

            # Z.ai için: Eğer 5'ten fazla seçenek varsa veya tekrar varsa temizle
            if len(cleaned_choices) > 5:
                cleaned_choices = cleaned_choices[:5]

            # Eğer 5'ten az seçenek varsa eksikleri ekle
            while len(cleaned_choices) < 5:
                cleaned_choices.append(f"Seçenek {chr(65 + len(cleaned_choices))}")

            # Tekrar eden seçenekleri kaldır (sondakileri koru)
            unique_choices = []
            seen = set()
            for choice in reversed(cleaned_choices):
                if choice not in seen:
                    unique_choices.append(choice)
                    seen.add(choice)
            unique_choices.reverse()

            return unique_choices

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
            # Check if this is a balance issue
            error_msg = str(e).lower()
            is_balance_issue = any(keyword in error_msg for keyword in [
                "balance", "insufficient", "充值", "1113", "429", "no resource package"
            ])

            if provider == "zai" and self.openai_client:
                logger.info(f"Falling back from Z.ai to OpenAI: {e}")
                try:
                    return self._get_openai_response(messages, json_mode=json_mode)
                except Exception as fallback_error:
                    logger.error(f"Fallback to OpenAI also failed: {fallback_error}")
                    # Check if fallback also has balance issues
                    fallback_error_msg = str(fallback_error).lower()
                    is_fallback_balance_issue = any(keyword in fallback_error_msg for keyword in [
                        "balance", "insufficient", "quota", "limit", "429"
                    ])

                    if is_balance_issue and is_fallback_balance_issue:
                        raise AIProviderError(f"Balance issues with both providers: {e}", provider="both", original_error=e)
                    else:
                        raise AIProviderError(f"Both Z.ai and OpenAI failed: {e}", provider="both")
            else:
                if is_balance_issue:
                    raise AIProviderError(f"Balance issue with {provider}: {e}", provider=provider, original_error=e)
                else:
                    raise e

    def _get_zai_response(self, messages: Iterable[dict], *, json_mode: bool = False):
        """Get response from Z.ai API with system role workaround"""
        if not self.zai_client:
            raise AIProviderError("Z.ai client not initialized", provider="zai")

        try:
            # Z.ai API system role desteklemiyor, system prompt'u user message'ın başına ekle
            system_prompt = ""
            user_prompt = ""

            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_prompt = msg["content"]

            # System prompt'u user message'ın başına ekle
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
            else:
                full_prompt = user_prompt

            # Z.ai client ile doğrudan API call (system'siz)
            import requests
            import json as pyjson

            # Headers
            headers = {
                'Authorization': f'Bearer {getattr(settings, "ZAI_API_KEY", "")}',
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }

            # Data
            data = {
                'model': self.zai_model,
                'max_tokens': 800,
                'temperature': 0.5,
                'messages': [{'role': 'user', 'content': full_prompt}]
            }

            # API call
            response = requests.post(
                "https://api.z.ai/api/anthropic/v1/messages",
                headers=headers,
                json=data,
                timeout=30,
                verify=False  # SSL issues için
            )

            if response.status_code != 200:
                raise AIProviderError(f"Z.ai API error: {response.status_code} - {response.text}", provider="zai")

            # Response formatını Z.ai client response formatına dönüştür
            result = response.json()
            content = result.get('content', [{}])[0].get('text', '')

            # Mock response object oluştur
            class MockChoice:
                def __init__(self, content):
                    self.message = MockMessage(content)

            class MockMessage:
                def __init__(self, content):
                    self.content = content

            class MockResponse:
                def __init__(self, content):
                    self.choices = [MockChoice(content)]

            return MockResponse(content)

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
                "temperature": 0.5,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.openai_client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIProviderError(f"OpenAI API error: {str(e)}", provider="openai", original_error=e)

    def get_random_question(self, subject: str = None, difficulty: str = None):
        """Get a random question from database as fallback"""
        try:
            from ..models import Question

            queryset = Question.objects.all()

            if subject:
                # Map display names to model values
                subject_map = {
                    'Matematik': 'MAT',
                    'Fizik': 'FIZ',
                    'Kimya': 'KIM',
                    'Biyoloji': 'BIO',
                    'Geometri': 'GEO'
                }
                subject_value = subject_map.get(subject, subject)
                queryset = queryset.filter(subject=subject_value)

            if difficulty:
                # Map display names to model values
                difficulty_map = {
                    'Kolay': 'E',
                    'Orta': 'M',
                    'Zor': 'H'
                }
                difficulty_value = difficulty_map.get(difficulty, difficulty)
                queryset = queryset.filter(difficulty=difficulty_value)

            if queryset.exists():
                question = queryset.order_by('?').first()
                return {
                    "stem": question.stem,
                    "choices": question.choices,
                    "answer": question.answer,
                    "rubric": question.rubric,
                    "source": "database",
                    "is_fallback": True
                }
            else:
                # No matching questions, get any random question
                question = Question.objects.order_by('?').first()
                if question:
                    return {
                        "stem": question.stem,
                        "choices": question.choices,
                        "answer": question.answer,
                        "rubric": question.rubric,
                        "source": "database",
                        "is_fallback": True
                    }
                else:
                    raise Exception("No questions available in database")

        except Exception as e:
            logger.error(f"Failed to get random question: {e}")
            raise Exception(f"No fallback questions available: {e}")

    def generate_question(self, subject: str, topic: str, difficulty: str, provider: str = "openai"):
        """Generate a question using specified AI provider with fallback to database"""
        try:
            from ..prompts import SYSTEM_PROMPT, generate_user_prompt
        except ImportError:
            # Fallback prompts if prompts.py is not available
            SYSTEM_PROMPT = "Sen TYT sınavları için soru üreten bir yapay zekasın."
            generate_user_prompt = lambda s, t, d: f"Subject: {s}\nTopic: {t}\nDifficulty: {d}\nGenerate a multiple choice question."

        prompt = generate_user_prompt(subject, topic, difficulty)

        # Provider-specific optimizations
        if provider == "zai":
            # Z.ai için özel talimatlar
            zai_optimization = "\n\nZ.ai İÇİN KRİTİK KURALLAR (HİÇBİRİNİ ATLAMA):\n"
            zai_optimization += "=== ZORUNLU FORMAT ===\n"
            zai_optimization += "• KESİNLİKLE 5 şık üret: A, B, C, D, E (HİÇ 4 ŞIK YAPMA!)\n"
            zai_optimization += "• JSON choices dizisinde KESİNLİKLE 5 eleman olacak\n"
            zai_optimization += "• Şıklar: \"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\", \"E) ...\" formatında\n"
            zai_optimization += "• SADECE BİR doğru cevap (A, B, C, D veya E)\n"
            zai_optimization += "• Cevap şıkkındaki değer diğer şıklarda OLMAYACAK\n"
            zai_optimization += "• Matematiksel/kavramal DOĞRULUĞU KONTROL ET\n\n"
            zai_optimization += "=== ÖRNEK JSON ===\n"
            zai_optimization += "{\n"
            zai_optimization += "  \"stem\": \"...\",\n"
            zai_optimization += "  \"choices\": [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\", \"E) ...\"],\n"
            zai_optimization += "  \"answer\": \"C\",\n"
            zai_optimization += "  \"rubric\": \"...\"\n"
            zai_optimization += "}\n\n"
            zai_optimization += "UYARI: Eğer 4 şık üretirsen sistem reddedecek!\n"
            prompt += zai_optimization

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            completion = self._get_ai_response(provider, messages, json_mode=True)
            content = completion.choices[0].message.content

            # Provider ayırına göre JSON parsing
            if provider == "zai":
                payload = self._parse_zai_response(content)
            else:
                # OpenAI ve diğerleri için standart JSON parsing
                payload = self._parse_standard_response(content)

            choices = self._format_choices(payload.get("choices"))
            answer = (payload.get("answer", "") or "A")[0]

            # Z.ai için: Eğer 5 şık gelmediyse eksik şıkları ekle
            if provider == "zai" and len(choices) < 5:
                while len(choices) < 5:
                    new_letter = chr(65 + len(choices))  # A, B, C, D, E
                    choices.append(f"{new_letter}) Hesaplanamayan seçenek")
                    # Cevap yeni eklenen şıksa değiştirme
                    if answer == new_letter:
                        answer = "A"  # Varsayılan olarak A yap

            return {
                "stem": payload.get("stem", ""),
                "choices": choices,
                "answer": answer,
                "rubric": payload.get("rubric", ""),
                "source": provider,
                "is_fallback": False
            }

        except AIProviderError as e:
            # Check if this is specifically a balance issue
            error_msg = str(e).lower()
            is_balance_issue = any(keyword in error_msg for keyword in [
                "balance", "insufficient", "充值", "1113", "429", "no resource package",
                "quota", "limit"
            ])

            if is_balance_issue:
                logger.info(f"Balance issue detected, falling back to database: {e}")
                return self.get_random_question(subject, difficulty)
            else:
                # This is a technical error, not balance
                logger.error(f"Technical error in AI generation: {e}")
                raise e

        except Exception as e:
            # Any other unexpected error
            logger.error(f"Unexpected error in AI generation: {e}")
            # Try to fall back to database anyway
            try:
                return self.get_random_question(subject, difficulty)
            except:
                raise e

    def explain_question(self, question_text: str, choices: List[str], provider: str = "openai"):
        """Generate explanation for a question"""
        user_message = f"Soruyu adım adım açıkla: {question_text}\nSeçenekler: {choices}"

        messages = [
            {"role": "system", "content": "Kısa, sade ve adım adım açıklama yap."},
            {"role": "user", "content": user_message},
        ]

        completion = self._get_ai_response(provider, messages)
        return completion.choices[0].message.content

    def _parse_zai_response(self, content: str) -> dict:
        """Parse Z.ai API response with robust error handling and enhanced cleanup"""

        # Extract JSON from markdown or plain text
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.find('```', start)
            if end > start:
                json_str = content[start:end].strip()
            else:
                raise AIProviderError("Invalid JSON markdown block - unclosed", provider="zai")
        else:
            # Find JSON object in content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
            else:
                raise AIProviderError("No JSON found in Z.ai response", provider="zai")

        print(f"DEBUG: Raw JSON length: {len(json_str)}")
        print(f"DEBUG: JSON preview (first 100): {repr(json_str[:100])}")

        # Aggressive cleanup for Z.ai specific issues
        json_str = json_str.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        json_str = json_str.replace('\\n', ' ').replace('\\r', '').replace('\\t', ' ')
        json_str = ' '.join(json_str.split())  # Remove extra whitespace

        # Additional cleanup for JSON string literals with embedded newlines and quotes
        json_str = json_str.replace('" \\n', ' ').replace('" \\r', ' ').replace('" \\t', ' ')
        json_str = json_str.replace('\\\\"', '"').replace('\\\\"', '"').replace('\\/', ' ')

        # Fix common quote escaping issues
        json_str = json_str.replace('""', '" "').replace('" ', ' ')

        print(f"DEBUG: Cleaned JSON (first 100): {repr(json_str[:100])}")

        # Try parsing with multiple fallback strategies
        for attempt in range(5):
            try:
                result = json.loads(json_str)
                print(f"DEBUG: Successfully parsed on attempt {attempt + 1}")
                return result
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON parse error on attempt {attempt + 1}: {str(e)}")

                if attempt == 0:
                    # Basic newline cleanup (redundant but safe)
                    json_str = json_str.replace('\n', '').replace('\r', '').replace('\t', '')
                elif attempt == 1:
                    # More aggressive whitespace cleanup
                    json_str = re.sub(r'\s+', ' ', json_str)
                elif attempt == 2:
                    # Fix specific quote issues in choices
                    json_str = json_str.replace('"A) ', '"A) ').replace('"B) ', '"B) ').replace('"C) ', '"C) ').replace('"D) ', '"D) ').replace('"E) ', '"E) ')
                    json_str = json_str.replace('\'', '"')
                elif attempt == 3:
                    # Try to fix truncated or malformed JSON
                    if not json_str.endswith('}'):
                        if '}' in json_str:
                            json_str = json_str[:json_str.rfind('}') + 1]
                    # Fix dangling quotes
                    json_str = json_str.rstrip(',').rstrip(':') + '"'
                else:
                    # Final attempt - create robust fallback data
                    try:

                        # Extract stem with better pattern
                        stem_match = re.search(r'"stem"\s*:\s*"([^"]*(?:[^"]*\\")*[^"]*)"', json_str, re.DOTALL)
                        stem = stem_match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\r', ' ') if stem_match else "Z.ai Fizik sorusu"

                        # Extract answer
                        answer_match = re.search(r'"answer"\s*:\s*"([^"]*)"', json_str)
                        answer = answer_match.group(1) if answer_match else "C"

                        # Extract choices more robustly
                        choices = []
                        try:
                            choices_match = re.search(r'"choices"\s*:\s*\[([^\]]*)\]', json_str, re.DOTALL)
                            if choices_match:
                                choices_str = choices_match.group(1)
                                # Extract individual choices with better pattern
                                choice_patterns = [
                                    r'"([^"]*[A-E]\)[^"]*(?="[^"]*"$|[^"]*))"',  # A) "...", may have content after
                                    r'"([^"]*[^"]*[A-E][^"]*)"',  # A" (without parenthesis)
                                ]
                                for pattern in choice_patterns:
                                    matches = re.findall(pattern, choices_str)
                                    if matches:
                                        choices.extend([m.replace('""', '') for m in matches])
                            # Clean up choices
                            choices = [c.strip() for c in choices if c and len(c.strip()) > 1]
                        except:
                            choices = ["A) Seçenek 1", "B) Seçenek 2", "C) Seçenek 3", "D) Seçenek 4", "E) Seçenek 5"]

                        # Extract rubric
                        rubric_match = re.search(r'"rubric"\s*:\s*"([^"]*(?="[^"]*"$|[^"]*))', json_str, re.DOTALL)
                        rubric = rubric_match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\r', ' ') if rubric_match else "Çözüm açıklaması"

                        return {
                            "stem": stem,
                            "choices": choices,
                            "answer": answer,
                            "rubric": rubric
                        }

                    except Exception as inner_e:
                        print(f"DEBUG: Regex extraction failed: {inner_e}")

                        # Create minimal fallback data
                        return {
                            "stem": "Z.ai Fizik sorusu (parsing error)",
                            "choices": ["A) Seçenek 1", "B) Seçenek 2", "C) Seçenek 3", "D) Seçenek 4", "E) Seçenek 5"],
                            "answer": "C",
                            "rubric": f"JSON parsing hatası. Length: {len(content)} karakter. Error: {str(e)} | Last attempt"
                        }

                    raise AIProviderError(f"Failed to parse Z.ai JSON after all cleanup attempts: {e}", provider="zai")

    def _parse_standard_response(self, content: str) -> dict:
        """Parse standard API response (OpenAI, etc.)"""
        try:
            # Try direct JSON parsing first (most common case)
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed content
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                if end > start:
                    json_str = content[start:end].strip()
                    return json.loads(json_str)

            # Look for JSON object in the content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)

            raise AIProviderError("No valid JSON found in response", provider="standard")

# Singleton instance
ai_service = AIService()