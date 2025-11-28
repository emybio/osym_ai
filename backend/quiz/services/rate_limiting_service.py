import logging
import time
from typing import Dict, List, Tuple, Optional, Any
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.cache import cache
from django.http import HttpRequest
from django.db import models
from django.conf import settings
import hashlib
import json

from quiz.models import AnonymousUser, TempExamSession, TempExamResult

logger = logging.getLogger(__name__)


class RateLimitingService:
    """Gelişmiş Rate Limiting ve Anti-Spam Servisi"""

    # Cache anahtarları ve süreleri
    CACHE_TIMEOUT = 3600  # 1 saat
    SHORT_CACHE = 300     # 5 dakika
    MEDIUM_CACHE = 1800   # 30 dakika

    # Rate limit kuralları
    RATE_LIMITS = {
        'test_creation': {
            'short_term': {'requests': 3, 'window': 60},      # 1 dakikada 3 test
            'medium_term': {'requests': 10, 'window': 3600},    # 1 saatte 10 test
            'long_term': {'requests': 50, 'window': 86400},     # 1 günde 50 test
        },
        'test_submission': {
            'short_term': {'requests': 5, 'window': 60},      # 1 dakikada 5 test
            'medium_term': {'requests': 15, 'window': 3600},    # 1 saatte 15 test
            'long_term': {'requests': 60, 'window': 86400},     # 1 günde 60 test
        },
        'api_requests': {
            'short_term': {'requests': 100, 'window': 60},     # 1 dakikada 100 istek
            'medium_term': {'requests': 1000, 'window': 3600},  # 1 saatte 1000 istek
            'long_term': {'requests': 10000, 'window': 86400}, # 1 günde 10000 istek
        }
    }

    # Anti-spam kuralları
    ANTI_SPAM_RULES = {
        'rapid_test_attempts': {
            'max_attempts': 5,
            'time_window': 300,  # 5 dakika
            'block_duration': 900  # 15 dakika block
        },
        'failed_test_ratio': {
            'min_successful': 0.1,  # En az %10 başarılık
            'evaluation_window': 3600,  # 1 saatlik değerlendirme
            'block_threshold': 0.9,  # %90'dan fazlası başarısızsa block
        },
        'suspicious_patterns': {
            'consecutive_failures': 10,
            'time_threshold': 1800,  # 30 dakika
            'block_duration': 7200   # 2 saat block
        },
        'multiple_sessions': {
            'max_concurrent_sessions': 3,
            'cleanup_threshold': 3600  # 1 saat eski oturumları temizle
        }
    }

    # IP tabanlı limitler
    IP_BASED_LIMITS = {
        'requests_per_minute': 60,
        'requests_per_hour': 500,
        'max_concurrent_sessions': 5,
        'block_duration': 1800  # 30 dakika
    }

    @classmethod
    def check_rate_limit(cls, request: HttpRequest, action: str, user_identifier: str = None) -> Dict[str, Any]:
        """
        Rate limit kontrolü yap
        """
        try:
            # User identifier'ı belirle
            if not user_identifier:
                user_identifier = cls._get_identifier(request)

            # Rate limit kurallarını kontrol et
            rate_limits = cls.RATE_LIMITS.get(action, {})
            if not rate_limits:
                return {'allowed': True, 'remaining': float('inf')}

            # Her zaman dilimi için kontrol yap
            for period, rule in rate_limits.items():
                result = cls._check_sliding_window(user_identifier, action, rule['requests'], rule['window'])
                if not result['allowed']:
                    # Block bilgilerini kaydet
                    cls._record_violation(user_identifier, action, period, result)
                    return result

            return {'allowed': True, 'remaining': float('inf')}

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Hata durumunda izin ver (fail-safe)
            return {'allowed': True, 'remaining': float('inf')}

    @classmethod
    def check_anti_spam(cls, request: HttpRequest, anonymous_user: AnonymousUser = None) -> Dict[str, Any]:
        """
        Anti-spam kontrolü yap
        """
        try:
            user_id = anonymous_user.id if anonymous_user else cls._get_identifier(request)
            violations = []

            # Hızlı test denemeleri kontrolü
            rapid_test_result = cls._check_rapid_test_attempts(user_id)
            if not rapid_test_result['allowed']:
                violations.append(rapid_test_result)

            # Başarısızlık oranı kontrolü
            if anonymous_user:
                failure_result = cls._check_failure_ratio(anonymous_user)
                if not failure_result['allowed']:
                    violations.append(failure_result)

            # Şüpheli desenler kontrolü
            if anonymous_user:
                pattern_result = cls._check_suspicious_patterns(anonymous_user)
                if not pattern_result['allowed']:
                    violations.append(pattern_result)

            # Çoklu oturum kontrolü
            session_result = cls._check_multiple_sessions(user_id)
            if not session_result['allowed']:
                violations.append(session_result)

            # IP tabanlı kontroller
            ip_result = cls._check_ip_limits(request)
            if not ip_result['allowed']:
                violations.append(ip_result)

            return {
                'allowed': len(violations) == 0,
                'violations': violations,
                'user_id': user_id
            }

        except Exception as e:
            logger.error(f"Anti-spam check error: {e}")
            return {'allowed': True, 'violations': []}

    @classmethod
    def record_action(cls, request: HttpRequest, action: str, success: bool = True, metadata: Dict = None):
        """
        Aksiyonu kaydet ve istatistikleri güncelle
        """
        try:
            user_identifier = cls._get_identifier(request)
            timestamp = time.time()

            # Aksiyon kaydı
            action_key = f"action_{user_identifier}_{action}"
            action_data = cache.get(action_key, [])

            # Yeni aksiyonu ekle
            new_action = {
                'timestamp': timestamp,
                'success': success,
                'metadata': metadata or {}
            }

            action_data.append(new_action)

            # Sadece son 1000 aksiyonu sakla
            if len(action_data) > 1000:
                action_data = action_data[-1000:]

            # Cache'e kaydet
            cache.set(action_key, action_data, timeout=cls.CACHE_TIMEOUT)

            # Başarısızlık oranını güncelle
            if not success:
                cls._update_failure_stats(user_identifier, action)

            logger.info(f"Action recorded: {action} for {user_identifier}, success: {success}")

        except Exception as e:
            logger.error(f"Action recording error: {e}")

    @classmethod
    def get_user_stats(cls, request: HttpRequest, anonymous_user: AnonymousUser = None) -> Dict[str, Any]:
        """
        Kullanıcının rate limiting istatistiklerini al
        """
        try:
            user_identifier = anonymous_user.id if anonymous_user else cls._get_identifier(request)

            stats = {
                'user_identifier': user_identifier,
                'current_limits': {},
                'violation_history': cls._get_violation_history(user_identifier),
                'action_history': cls._get_action_history(user_identifier),
                'reputation_score': cls._calculate_reputation_score(user_identifier),
                'risk_level': 'low'
            }

            # Mevcut limitleri hesapla
            for action, limits in cls.RATE_LIMITS.items():
                stats['current_limits'][action] = {}
                for period, rule in limits.items():
                    key = f"rate_limit_{user_identifier}_{action}_{period}"
                    count = cache.get(key, 0)
                    stats['current_limits'][action][period] = {
                        'current': count,
                        'max': rule['requests'],
                        'remaining': max(0, rule['requests'] - count),
                        'reset_time': cls._get_reset_time(key, rule['window'])
                    }

            # Risk seviyesini belirle
            stats['risk_level'] = cls._calculate_risk_level(stats)

            return stats

        except Exception as e:
            logger.error(f"User stats error: {e}")
            return {'error': str(e)}

    @classmethod
    def block_user(cls, user_identifier: str, reason: str, duration: int = 3600, metadata: Dict = None) -> bool:
        """
        Kullanıcıyı belirli bir süre için block'la
        """
        try:
            block_key = f"blocked_{user_identifier}"
            block_data = {
                'blocked': True,
                'reason': reason,
                'blocked_at': timezone.now().isoformat(),
                'duration': duration,
                'unblock_time': (timezone.now() + timedelta(seconds=duration)).isoformat(),
                'metadata': metadata or {}
            }

            cache.set(block_key, block_data, timeout=duration)

            # Block kaydını log'a ekle
            cls._log_block_event(user_identifier, reason, duration, metadata)

            logger.warning(f"User blocked: {user_identifier}, reason: {reason}, duration: {duration}s")
            return True

        except Exception as e:
            logger.error(f"User blocking error: {e}")
            return False

    @classmethod
    def is_user_blocked(cls, user_identifier: str) -> Dict[str, Any]:
        """
        Kullanıcının block'lı olup olmadığını kontrol et
        """
        try:
            block_key = f"blocked_{user_identifier}"
            block_data = cache.get(block_key)

            if not block_data:
                return {'blocked': False}

            # Block süresi dolmuş mu kontrol et
            unblock_time = datetime.fromisoformat(block_data['unblock_time'].replace('Z', '+00:00'))
            if timezone.now() > unblock_time:
                cache.delete(block_key)
                return {'blocked': False}

            return block_data

        except Exception as e:
            logger.error(f"Block check error: {e}")
            return {'blocked': False}

    @classmethod
    def unblock_user(cls, user_identifier: str, reason: str = "Manual unblock") -> bool:
        """
        Kullanıcının block'ını kaldır
        """
        try:
            block_key = f"blocked_{user_identifier}"
            cache.delete(block_key)

            # Unblock kaydını log'a ekle
            cls._log_unblock_event(user_identifier, reason)

            logger.info(f"User unblocked: {user_identifier}, reason: {reason}")
            return True

        except Exception as e:
            logger.error(f"User unblocking error: {e}")
            return False

    # ==================== PRIVATE METHODS ====================

    @classmethod
    def _get_identifier(cls, request: HttpRequest) -> str:
        """
        Request'ten unique identifier oluştur
        """
        # IP adresi ve User Agent hash'le
        ip_address = cls._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Browser ID'si varsa kullan
        browser_id = request.COOKIES.get('browser_id')
        if browser_id:
            identifier = f"browser_{browser_id}"
        else:
            identifier = f"ip_{hashlib.md5(f'{ip_address}_{user_agent}'.encode()).hexdigest()}"

        return identifier

    @classmethod
    def _get_client_ip(cls, request: HttpRequest) -> str:
        """
        Client IP adresini al (proxy'leri dikkate alarak)
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip.strip()

    @classmethod
    def _check_sliding_window(cls, user_identifier: str, action: str, max_requests: int, window: int) -> Dict[str, Any]:
        """
        Sliding window rate limiting
        """
        try:
            current_time = time.time()
            window_start = current_time - window

            # Rate limit key'i
            rate_key = f"rate_limit_{user_identifier}_{action}_{window}"

            # Mevcut request'leri al
            requests = cache.get(rate_key, [])

            # Penceredeki request'leri filtrele
            valid_requests = [req for req in requests if req > window_start]

            # Yeni request'i ekle
            valid_requests.append(current_time)

            # Eski request'leri temizle (performans için)
            if len(valid_requests) > max_requests * 2:
                valid_requests = valid_requests[-max_requests:]

            # Cache'e güncelle
            cache.set(rate_key, valid_requests, timeout=window)

            return {
                'allowed': len(valid_requests) <= max_requests,
                'remaining': max(0, max_requests - len(valid_requests)),
                'reset_time': int(min(valid_requests) + window if valid_requests else current_time + window),
                'current': len(valid_requests),
                'max': max_requests
            }

        except Exception as e:
            logger.error(f"Sliding window check error: {e}")
            return {'allowed': True, 'remaining': float('inf')}

    @classmethod
    def _check_rapid_test_attempts(cls, user_id: str) -> Dict[str, Any]:
        """
        Hızlı test denemelerini kontrol et
        """
        try:
            rule = cls.ANTI_SPAM_RULES['rapid_test_attempts']
            time_window = rule['time_window']
            max_attempts = rule['max_attempts']

            # Son test denemelerini al
            attempts_key = f"test_attempts_{user_id}"
            attempts = cache.get(attempts_key, [])

            current_time = time.time()
            recent_attempts = [attempt for attempt in attempts if current_time - attempt < time_window]

            if len(recent_attempts) >= max_attempts:
                # Kullanıcıyı block'la
                cls.block_user(user_id, f"Too many test attempts: {len(recent_attempts)} in {time_window}s",
                              rule['block_duration'])

                return {
                    'allowed': False,
                    'reason': 'rapid_test_attempts',
                    'attempts': len(recent_attempts),
                    'max_allowed': max_attempts,
                    'block_duration': rule['block_duration']
                }

            # Yeni denemeyi kaydet
            recent_attempts.append(current_time)
            cache.set(attempts_key, recent_attempts, timeout=time_window + 60)

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Rapid test attempts check error: {e}")
            return {'allowed': True}

    @classmethod
    def _check_failure_ratio(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Başarısızlık oranını kontrol et
        """
        try:
            rule = cls.ANTI_SPAM_RULES['failed_test_ratio']
            evaluation_window = rule['evaluation_window']

            # Son test sonuçlarını al
            cutoff_time = timezone.now() - timedelta(seconds=evaluation_window)
            recent_results = TempExamResult.objects.filter(
                anonymous_user=anonymous_user,
                created_at__gte=cutoff_time
            )

            if recent_results.count() < 5:  # Yeterli veri yoksa kontrol yapma
                return {'allowed': True}

            successful_tests = recent_results.filter(result__percentage__gte=50).count()
            total_tests = recent_results.count()
            success_rate = successful_tests / total_tests

            if success_rate < rule['min_successful']:
                cls.block_user(
                    str(anonymous_user.id),
                    f"Low success rate: {success_rate:.2%} ({successful_tests}/{total_tests})",
                    rule['block_duration'],
                    {'failure_data': {'success_rate': success_rate, 'total_tests': total_tests}}
                )

                return {
                    'allowed': False,
                    'reason': 'low_success_rate',
                    'success_rate': success_rate,
                    'successful_tests': successful_tests,
                    'total_tests': total_tests,
                    'min_required': rule['min_successful'],
                    'block_duration': rule['block_duration']
                }

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Failure ratio check error: {e}")
            return {'allowed': True}

    @classmethod
    def _check_suspicious_patterns(cls, anonymous_user: AnonymousUser) -> Dict[str, Any]:
        """
        Şüpheli desenleri kontrol et
        """
        try:
            rule = cls.ANTI_SPAM_RULES['suspicious_patterns']
            consecutive_failures = rule['consecutive_failures']
            time_threshold = rule['time_threshold']

            # Son test sonuçlarını al
            recent_results = TempExamResult.objects.filter(
                anonymous_user=anonymous_user
            ).order_by('-created_at')[:consecutive_failures]

            # Son N testin başarısız olup olmadığını kontrol et
            failed_count = sum(1 for result in recent_results if result.percentage < 20)

            if failed_count >= consecutive_failures:
                # Bu başarısızlıkların zaman aralığını kontrol et
                first_failure = recent_results.last()
                time_span = (timezone.now() - first_failure.created_at).total_seconds()

                if time_span <= time_threshold:
                    cls.block_user(
                        str(anonymous_user.id),
                        f"Suspicious pattern: {failed_count} consecutive failures in {time_span}s",
                        rule['block_duration'],
                        {'pattern_data': {'failed_count': failed_count, 'time_span': time_span}}
                    )

                    return {
                        'allowed': False,
                        'reason': 'suspicious_pattern',
                        'consecutive_failures': failed_count,
                        'time_span': time_span,
                        'threshold': consecutive_failures,
                        'block_duration': rule['block_duration']
                    }

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Suspicious patterns check error: {e}")
            return {'allowed': True}

    @classmethod
    def _check_multiple_sessions(cls, user_id: str) -> Dict[str, Any]:
        """
        Çoklu oturumları kontrol et
        """
        try:
            rule = cls.ANTI_SPAM_RULES['multiple_sessions']
            max_concurrent = rule['max_concurrent_sessions']

            # Aktif oturumları say
            active_sessions = TempExamSession.objects.filter(
                anonymous_user__id=user_id if user_id.isdigit() else None,
                status='active'
            ).count()

            # Browser ID için kontrol
            if not user_id.isdigit():
                browser_sessions = TempExamSession.objects.filter(
                    status='active'
                ).count()
                active_sessions = max(active_sessions, browser_sessions)

            if active_sessions > max_concurrent:
                return {
                    'allowed': False,
                    'reason': 'too_many_sessions',
                    'active_sessions': active_sessions,
                    'max_allowed': max_concurrent
                }

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Multiple sessions check error: {e}")
            return {'allowed': True}

    @classmethod
    def _check_ip_limits(cls, request: HttpRequest) -> Dict[str, Any]:
        """
        IP tabanlı limitleri kontrol et
        """
        try:
            ip_address = cls._get_client_ip(request)
            limits = cls.IP_BASED_LIMITS

            # IP block'ı kontrol et
            block_data = cls.is_user_blocked(f"ip_{ip_address}")
            if block_data['blocked']:
                return {
                    'allowed': False,
                    'reason': 'ip_blocked',
                    'block_data': block_data
                }

            # IP rate limit kontrolü
            minute_key = f"ip_rate_{ip_address}_minute"
            minute_requests = cache.get(minute_key, 0)

            if minute_requests >= limits['requests_per_minute']:
                cls.block_user(f"ip_{ip_address}", f"IP rate limit exceeded: {minute_requests}/min",
                              limits['block_duration'])

                return {
                    'allowed': False,
                    'reason': 'ip_rate_limit',
                    'requests': minute_requests,
                    'max_allowed': limits['requests_per_minute']
                }

            # Request sayısını artır
            cache.set(minute_key, minute_requests + 1, timeout=60)

            return {'allowed': True}

        except Exception as e:
            logger.error(f"IP limits check error: {e}")
            return {'allowed': True}

    @classmethod
    def _record_violation(cls, user_identifier: str, action: str, period: str, violation_data: Dict):
        """
        Violasyon kaydı tut
        """
        try:
            violations_key = f"violations_{user_identifier}"
            violations = cache.get(violations_key, [])

            violation = {
                'timestamp': timezone.now().isoformat(),
                'action': action,
                'period': period,
                'data': violation_data
            }

            violations.append(violation)

            # Son 100 violation'ı sakla
            if len(violations) > 100:
                violations = violations[-100:]

            cache.set(violations_key, violations, timeout=cls.CACHE_TIMEOUT)

        except Exception as e:
            logger.error(f"Violation recording error: {e}")

    @classmethod
    def _update_failure_stats(cls, user_identifier: str, action: str):
        """
        Başarısızlık istatistiklerini güncelle
        """
        try:
            failure_key = f"failures_{user_identifier}_{action}"
            failures = cache.get(failure_key, 0)
            cache.set(failure_key, failures + 1, timeout=cls.MEDIUM_CACHE)

        except Exception as e:
            logger.error(f"Failure stats update error: {e}")

    @classmethod
    def _get_violation_history(cls, user_identifier: str) -> List[Dict]:
        """
        Violasyon geçmişini al
        """
        try:
            violations_key = f"violations_{user_identifier}"
            return cache.get(violations_key, [])
        except Exception:
            return []

    @classmethod
    def _get_action_history(cls, user_identifier: str) -> List[Dict]:
        """
        Aksiyon geçmişini al
        """
        try:
            action_history = {}
            for action in cls.RATE_LIMITS.keys():
                action_key = f"action_{user_identifier}_{action}"
                action_history[action] = cache.get(action_key, [])
            return action_history
        except Exception:
            return {}

    @classmethod
    def _calculate_reputation_score(cls, user_identifier: str) -> float:
        """
        Kullanıcı itibar skorunu hesapla (0-1)
        """
        try:
            violations = cls._get_violation_history(user_identifier)

            # Basit itibar skoru
            base_score = 1.0

            # Her violation için puan düşür
            for violation in violations:
                violation_age = (timezone.now() - datetime.fromisoformat(violation['timestamp'].replace('Z', '+00:00'))).total_seconds()

                # Eski violation'lar daha az etkili
                age_factor = max(0, 1 - (violation_age / 86400))  # 24 saat içindeki violation'lar

                # Violasyon tipine göre penalty
                if violation['period'] == 'short_term':
                    penalty = 0.1
                elif violation['period'] == 'medium_term':
                    penalty = 0.05
                else:
                    penalty = 0.02

                base_score -= penalty * age_factor

            return max(0, min(1, base_score))

        except Exception:
            return 0.5

    @classmethod
    def _calculate_risk_level(cls, stats: Dict) -> str:
        """
        Risk seviyesini hesapla
        """
        try:
            reputation = stats.get('reputation_score', 1.0)
            violations = len(stats.get('violation_history', []))

            if reputation < 0.3 or violations > 10:
                return 'high'
            elif reputation < 0.6 or violations > 5:
                return 'medium'
            else:
                return 'low'

        except Exception:
            return 'low'

    @classmethod
    def _get_reset_time(cls, key: str, window: int) -> int:
        """
        Rate limit reset zamanını hesapla
        """
        try:
            requests = cache.get(key, [])
            if not requests:
                return int(time.time() + window)

            oldest_request = min(requests)
            return int(oldest_request + window)

        except Exception:
            return int(time.time() + window)

    @classmethod
    def _log_block_event(cls, user_identifier: str, reason: str, duration: int, metadata: Dict):
        """
        Block olayını log'a ekle
        """
        try:
            log_key = f"block_log_{user_identifier}"
            logs = cache.get(log_key, [])

            log_entry = {
                'timestamp': timezone.now().isoformat(),
                'reason': reason,
                'duration': duration,
                'metadata': metadata
            }

            logs.append(log_entry)

            # Son 50 log'u sakla
            if len(logs) > 50:
                logs = logs[-50:]

            cache.set(log_key, logs, timeout=cls.CACHE_TIMEOUT)

        except Exception as e:
            logger.error(f"Block logging error: {e}")

    @classmethod
    def _log_unblock_event(cls, user_identifier: str, reason: str):
        """
        Unblock olayını log'a ekle
        """
        try:
            log_key = f"unblock_log_{user_identifier}"
            logs = cache.get(log_key, [])

            log_entry = {
                'timestamp': timezone.now().isoformat(),
                'reason': reason
            }

            logs.append(log_entry)

            # Son 20 log'u sakla
            if len(logs) > 20:
                logs = logs[-20:]

            cache.set(log_key, logs, timeout=cls.CACHE_TIMEOUT)

        except Exception as e:
            logger.error(f"Unblock logging error: {e}")