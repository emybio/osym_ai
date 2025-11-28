"""
Advanced Caching Service
Multi-tier caching with Redis, memcached, and in-memory caching
"""

import logging
import json
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.core.serializers.json import DjangoJSONEncoder
import redis
import threading
import time
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheService:
    """Advanced multi-tier caching service"""

    # Cache tiers
    MEMORY_CACHE = {}
    MEMORY_CACHE_LOCK = threading.Lock()

    # Cache configuration
    DEFAULT_TIMEOUT = 300  # 5 minutes
    LONG_TIMEOUT = 3600  # 1 hour
    SHORT_TIMEOUT = 60   # 1 minute

    # Cache keys patterns
    KEYS = {
        'QUESTIONS_BY_SUBJECT': 'questions:subject:{subject_id}',
        'QUESTIONS_BY_TOPIC': 'questions:topic:{topic_id}',
        'USER_PROFILE': 'user:profile:{user_id}',
        'USER_STATS': 'user:stats:{user_id}:{period}',
        'LEADERBOARD': 'leaderboard:{exam_type}:{branch}',
        'ANALYTICS_DASHBOARD': 'analytics:dashboard:{period}',
        'TEMP_EXAM_SESSION': 'temp_exam:session:{uuid}',
        'RATE_LIMIT': 'rate_limit:{identifier}:{action}',
        'ADAPTIVE_PROFILE': 'adaptive:profile:{user_id}',
        'GAMIFICATION_STREAKS': 'gamification:streaks:{user_id}',
        'PERFORMANCE_METRICS': 'metrics:performance:{period}',
        'CONTENT_ANALYTICS': 'analytics:content:{period}',
        'DIFFICULTY_DISTRIBUTION': 'difficulty:dist:{subject_id}',
        'POPULAR_QUESTIONS': 'questions:popular:{subject_id}',
        'QUICK_TEST_QUESTIONS': 'quicktest:{exam_type}:{branch}:{count}',
        'SUBJECT_MASTERY': 'mastery:{user_id}:{subject_id}',
        'USER_RECOMMENDATIONS': 'recommendations:{user_id}',
    }

    @classmethod
    def get_redis_client(cls) -> Optional[redis.Redis]:
        """Get Redis client"""
        try:
            return redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return None

    @classmethod
    def generate_cache_key(cls, pattern: str, **kwargs) -> str:
        """Generate cache key with parameters"""
        try:
            key = pattern.format(**kwargs)
            # Add namespace prefix
            return f"osym_ai:{key}"
        except KeyError as e:
            logger.error(f"Missing parameter for cache key pattern: {e}")
            return f"osym_ai:unknown:{hash(str(kwargs))}"

    @classmethod
    def set(cls, key: str, value: Any, timeout: int = None) -> bool:
        """
        Set cache value with multi-tier strategy
        """
        if timeout is None:
            timeout = cls.DEFAULT_TIMEOUT

        try:
            # Level 1: Memory cache (fastest)
            with cls.MEMORY_CACHE_LOCK:
                cls.MEMORY_CACHE[key] = {
                    'value': value,
                    'expires_at': time.time() + timeout,
                    'timestamp': time.time()
                }

            # Level 2: Django cache (Redis/Memcached)
            cache.set(key, value, timeout)

            # Level 3: Redis directly for complex operations
            redis_client = cls.get_redis_client()
            if redis_client:
                try:
                    # Store additional metadata
                    metadata = {
                        'timestamp': time.time(),
                        'timeout': timeout,
                        'size': len(str(value))
                    }
                    redis_client.set(f"{key}:meta", json.dumps(metadata), ex=timeout)
                except Exception as e:
                    logger.warning(f"Redis metadata set failed: {e}")

            return True

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    @classmethod
    def get(cls, key: str) -> Any:
        """
        Get cache value with multi-tier fallback
        """
        try:
            # Level 1: Check memory cache first
            with cls.MEMORY_CACHE_LOCK:
                if key in cls.MEMORY_CACHE:
                    cache_item = cls.MEMORY_CACHE[key]
                    if cache_item['expires_at'] > time.time():
                        return cache_item['value']
                    else:
                        # Expired, remove from memory
                        del cls.MEMORY_CACHE[key]

            # Level 2: Check Django cache
            value = cache.get(key)
            if value is not None:
                # Repopulate memory cache
                with cls.MEMORY_CACHE_LOCK:
                    cls.MEMORY_CACHE[key] = {
                        'value': value,
                        'expires_at': time.time() + cls.DEFAULT_TIMEOUT,
                        'timestamp': time.time()
                    }
                return value

            return None

        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    @classmethod
    def delete(cls, key: str) -> bool:
        """Delete cache key from all tiers"""
        try:
            # Remove from memory cache
            with cls.MEMORY_CACHE_LOCK:
                cls.MEMORY_CACHE.pop(key, None)

            # Remove from Django cache
            cache.delete(key)

            # Remove from Redis
            redis_client = cls.get_redis_client()
            if redis_client:
                redis_client.delete(key, f"{key}:meta")

            return True

        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """Delete cache keys matching pattern"""
        try:
            count = 0

            # Clear memory cache
            with cls.MEMORY_CACHE_LOCK:
                keys_to_remove = [k for k in cls.MEMORY_CACHE.keys() if pattern in k]
                for key in keys_to_remove:
                    del cls.MEMORY_CACHE[key]
                    count += 1

            # Clear Django cache
            # Note: Django cache doesn't support pattern deletion by default
            # This would need custom implementation based on cache backend

            # Clear Redis
            redis_client = cls.get_redis_client()
            if redis_client:
                redis_pattern = f"*{pattern}*"
                redis_keys = redis_client.keys(redis_pattern)
                if redis_keys:
                    count += redis_client.delete(*redis_keys)

            return count

        except Exception as e:
            logger.error(f"Cache pattern delete failed: {e}")
            return 0

    @classmethod
    def get_or_set(cls, key: str, default_func: Callable, timeout: int = None) -> Any:
        """Get value from cache or set using default function"""
        value = cls.get(key)
        if value is not None:
            return value

        value = default_func()
        cls.set(key, value, timeout)
        return value

    @classmethod
    def invalidate_user_cache(cls, user_id: str):
        """Invalidate all cache entries for a user"""
        patterns = [
            f"user:profile:{user_id}",
            f"user:stats:{user_id}",
            f"adaptive:profile:{user_id}",
            f"gamification:streaks:{user_id}",
            f"mastery:{user_id}",
            f"recommendations:{user_id}"
        ]

        for pattern in patterns:
            cls.delete_pattern(pattern)

    @classmethod
    def warm_cache(cls) -> Dict[str, int]:
        """Warm up frequently accessed cache entries"""
        results = {
            'warmed_keys': 0,
            'errors': 0
        }

        try:
            from ..models import Subject, Question, AnonymousUser

            # Warm popular subjects
            subjects = Subject.objects.all()[:10]
            for subject in subjects:
                try:
                    questions = list(Question.objects.filter(
                        subject=subject
                    ).values('id', 'difficulty', 'topic_id')[:50])

                    key = cls.generate_cache_key(
                        cls.KEYS['QUESTIONS_BY_SUBJECT'],
                        subject_id=subject.id
                    )
                    cls.set(key, questions, cls.LONG_TIMEOUT)
                    results['warmed_keys'] += 1

                except Exception as e:
                    logger.warning(f"Failed to warm cache for subject {subject.id}: {e}")
                    results['errors'] += 1

            # Warm leaderboard cache
            try:
                key = cls.generate_cache_key(cls.KEYS['LEADERBOARD'], exam_type='TYT', branch='ALL')
                cls.set(key, [], cls.SHORT_TIMEOUT)  # Will be populated by actual queries
                results['warmed_keys'] += 1
            except Exception as e:
                logger.warning(f"Failed to warm leaderboard cache: {e}")
                results['errors'] += 1

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            results['errors'] += 1

        return results

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """Get cache statistics and health"""
        stats = {
            'memory_cache_size': 0,
            'redis_connected': False,
            'cache_hit_rate': 0,
            'total_keys': 0
        }

        try:
            # Memory cache stats
            with cls.MEMORY_CACHE_LOCK:
                stats['memory_cache_size'] = len(cls.MEMORY_CACHE)
                stats['memory_cache_items'] = list(cls.MEMORY_CACHE.keys())

            # Redis stats
            redis_client = cls.get_redis_client()
            if redis_client:
                try:
                    redis_client.ping()
                    stats['redis_connected'] = True
                    info = redis_client.info()
                    stats['redis_memory_used'] = info.get('used_memory_human', 'Unknown')
                    stats['redis_keys'] = info.get('db0', {}).get('keys', 0)
                except Exception as e:
                    logger.warning(f"Redis stats failed: {e}")

        except Exception as e:
            logger.error(f"Cache stats collection failed: {e}")

        return stats


def cached_result(timeout: int = 300, key_pattern: str = None):
    """
    Decorator for caching function results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_pattern:
                try:
                    cache_key = CacheService.generate_cache_key(key_pattern, **kwargs)
                except:
                    # Fallback to function-based key
                    key_data = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(kwargs))}"
                    cache_key = f"osym_ai:function:{hashlib.md5(key_data.encode()).hexdigest()}"
            else:
                key_data = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(kwargs))}"
                cache_key = f"osym_ai:function:{hashlib.md5(key_data.encode()).hexdigest()}"

            # Try to get from cache
            result = CacheService.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheService.set(cache_key, result, timeout)
            return result

        return wrapper
    return decorator


def cached_queryset(timeout: int = 300):
    """
    Decorator for caching Django QuerySet results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(kwargs))}"
            cache_key = f"osym_ai:queryset:{hashlib.md5(key_data.encode()).hexdigest()}"

            # Try to get from cache
            result = CacheService.get(cache_key)
            if result is not None:
                return result

            # Execute function
            queryset = func(*args, **kwargs)

            # Cache QuerySet data
            if isinstance(queryset, QuerySet):
                # Evaluate queryset and cache as list
                data = list(queryset)
                CacheService.set(cache_key, data, timeout)
                return data
            else:
                CacheService.set(cache_key, queryset, timeout)
                return queryset

        return wrapper
    return decorator


class QuestionCacheService:
    """Specialized caching service for questions"""

    @classmethod
    def cache_questions(cls, subject_id: str = None, topic_id: str = None,
                       difficulty: int = None, count: int = 50) -> List[Dict]:
        """
        Cache questions with various filters
        """
        from ..models import Question, Topic

        try:
            # Build base queryset
            queryset = Question.objects.select_related('subject', 'topic').prefetch_related('choices')

            if subject_id:
                queryset = queryset.filter(subject_id=subject_id)
                cache_key = CacheService.generate_cache_key(
                    CacheService.KEYS['QUESTIONS_BY_SUBJECT'],
                    subject_id=subject_id
                )
            elif topic_id:
                queryset = queryset.filter(topic_id=topic_id)
                cache_key = CacheService.generate_cache_key(
                    CacheService.KEYS['QUESTIONS_BY_TOPIC'],
                    topic_id=topic_id
                )
            else:
                cache_key = f"osym_ai:questions:all"

            if difficulty:
                queryset = queryset.filter(difficulty=difficulty)
                cache_key += f":difficulty:{difficulty}"

            cache_key += f":limit:{count}"

            # Try cache first
            cached_questions = CacheService.get(cache_key)
            if cached_questions:
                return cached_questions

            # Get from database
            questions = queryset.order_by('?')[:count]

            # Serialize for caching
            questions_data = []
            for q in questions:
                questions_data.append({
                    'id': q.id,
                    'subject': q.subject.code,
                    'topic': q.topic.name if q.topic else None,
                    'question_text': q.question_text,
                    'difficulty': q.difficulty,
                    'cognitive': q.cognitive,
                    'choices': [
                        {
                            'label': c.label,
                            'text': c.text,
                            'is_correct': c.is_correct
                        } for c in q.choices.all()
                    ],
                    'explanation': q.explanation
                })

            # Cache for 1 hour
            CacheService.set(cache_key, questions_data, CacheService.LONG_TIMEOUT)

            return questions_data

        except Exception as e:
            logger.error(f"Question caching failed: {e}")
            return []

    @classmethod
    def get_popular_questions(cls, subject_id: str = None, limit: int = 20) -> List[Dict]:
        """Get popular/cached questions"""
        cache_key = CacheService.generate_cache_key(
            CacheService.KEYS['POPULAR_QUESTIONS'],
            subject_id=subject_id or 'all'
        )
        cache_key += f":limit:{limit}"

        return CacheService.get_or_set(
            cache_key,
            lambda: cls.cache_questions(subject_id=subject_id, count=limit),
            CacheService.LONG_TIMEOUT
        )

    @classmethod
    def invalidate_question_cache(cls, subject_id: str = None):
        """Invalidate question caches"""
        patterns = ['questions:subject', 'questions:topic', 'questions:all', 'popular:questions']

        if subject_id:
            patterns.append(f"questions:subject:{subject_id}")

        for pattern in patterns:
            CacheService.delete_pattern(pattern)


class UserCacheService:
    """Specialized caching service for user data"""

    @classmethod
    def cache_user_profile(cls, user_id: str, profile_data: Dict):
        """Cache user profile data"""
        cache_key = CacheService.generate_cache_key(
            CacheService.KEYS['USER_PROFILE'],
            user_id=user_id
        )
        CacheService.set(cache_key, profile_data, CacheService.LONG_TIMEOUT)

    @classmethod
    def get_user_profile(cls, user_id: str) -> Optional[Dict]:
        """Get cached user profile"""
        cache_key = CacheService.generate_cache_key(
            CacheService.KEYS['USER_PROFILE'],
            user_id=user_id
        )
        return CacheService.get(cache_key)

    @classmethod
    def cache_user_stats(cls, user_id: str, stats_data: Dict, period: str = 'month'):
        """Cache user statistics"""
        cache_key = CacheService.generate_cache_key(
            CacheService.KEYS['USER_STATS'],
            user_id=user_id,
            period=period
        )
        CacheService.set(cache_key, stats_data, CacheService.LONG_TIMEOUT)

    @classmethod
    def get_user_stats(cls, user_id: str, period: str = 'month') -> Optional[Dict]:
        """Get cached user statistics"""
        cache_key = CacheService.generate_cache_key(
            CacheService.KEYS['USER_STATS'],
            user_id=user_id,
            period=period
        )
        return CacheService.get(cache_key)