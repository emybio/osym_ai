"""
A/B Testing Framework Service
Comprehensive A/B testing system for UI variants and feature testing
"""

import logging
import json
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from django.db import models
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import uuid

logger = logging.getLogger(__name__)


class ABTestService:
    """Comprehensive A/B testing service"""

    # Test Types
    TEST_TYPES = {
        'UI_VARIANT': 'UI Variant Testing',
        'FEATURE_FLAG': 'Feature Flag Testing',
        'CONTENT_VARIANT': 'Content Variant Testing',
        'PRICING_TEST': 'Pricing A/B Testing',
        'ONBOARDING_TEST': 'Onboarding Flow Testing'
    }

    # Traffic Allocation
    TRAFFIC_ALLOCATION = {
        'CONTROL': 50,  # 50% to control
        'VARIANT_A': 25,  # 25% to variant A
        'VARIANT_B': 25,  # 25% to variant B
    }

    # Default Test Configurations
    DEFAULT_CONFIGS = {
        'quick_test_button_color': {
            'type': 'UI_VARIANT',
            'control': {'color': '#3B82F6', 'text': 'Teste Başla'},
            'variant_a': {'color': '#10B981', 'text': 'Hızlı Test'},
            'variant_b': {'color': '#F59E0B', 'text': 'Test Çöz'},
            'metrics': ['click_through_rate', 'conversion_rate', 'time_on_page']
        },
        'dashboard_layout': {
            'type': 'UI_VARIANT',
            'control': {'layout': 'grid', 'cards_per_row': 3},
            'variant_a': {'layout': 'list', 'show_progress': True},
            'variant_b': {'layout': 'carousel', 'auto_rotate': True},
            'metrics': ['engagement_time', 'feature_usage', 'return_rate']
        },
        'gamification_rewards': {
            'type': 'FEATURE_FLAG',
            'control': {'points_enabled': True, 'streaks_enabled': True, 'badges_enabled': True},
            'variant_a': {'points_enabled': True, 'streaks_enabled': False, 'badges_enabled': True},
            'variant_b': {'points_enabled': False, 'streaks_enabled': True, 'badges_enabled': False},
            'metrics': ['test_completion_rate', 'daily_active_users', 'retention_rate']
        },
        'question_difficulty_display': {
            'type': 'UI_VARIANT',
            'control': {'show_difficulty': True, 'style': 'numbers', 'position': 'top'},
            'variant_a': {'show_difficulty': True, 'style': 'stars', 'position': 'bottom'},
            'variant_b': {'show_difficulty': False, 'style': 'hidden'},
            'metrics': ['question_accuracy', 'time_per_question', 'skip_rate']
        },
        'progress_tracking': {
            'type': 'CONTENT_VARIANT',
            'control': {'show_detailed': True, 'update_frequency': 'real_time'},
            'variant_a': {'show_detailed': True, 'update_frequency': 'end_of_test'},
            'variant_b': {'show_detailed': False, 'update_frequency': 'daily_summary'},
            'metrics': ['user_satisfaction', 'feature_engagement', 'completion_rate']
        }
    }

    @classmethod
    def get_user_segment(cls, user_id: str, test_name: str) -> str:
        """
        Determine which segment a user belongs to for a specific test
        Uses consistent hashing to ensure users always get the same variant
        """
        # Create consistent hash for user+test combination
        hash_input = f"{user_id}:{test_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)

        # Normalize to 0-100 range
        normalized = (hash_value % 100) + 1

        # Determine segment based on traffic allocation
        if normalized <= cls.TRAFFIC_ALLOCATION['CONTROL']:
            return 'control'
        elif normalized <= cls.TRAFFIC_ALLOCATION['CONTROL'] + cls.TRAFFIC_ALLOCATION['VARIANT_A']:
            return 'variant_a'
        else:
            return 'variant_b'

    @classmethod
    def get_test_config(cls, test_name: str, user_id: str = None) -> Dict[str, Any]:
        """
        Get test configuration for a specific test and user
        """
        try:
            # Check if test exists in default configs
            if test_name not in cls.DEFAULT_CONFIGS:
                logger.warning(f"Test '{test_name}' not found in default configurations")
                return {}

            test_config = cls.DEFAULT_CONFIGS[test_name].copy()

            # Determine user segment if user_id provided
            if user_id:
                segment = cls.get_user_segment(user_id, test_name)
                test_config['user_segment'] = segment
                test_config['variant_config'] = test_config.get(segment, test_config.get('control', {}))
            else:
                test_config['user_segment'] = None
                test_config['variant_config'] = test_config.get('control', {})

            # Add test metadata
            test_config['test_name'] = test_name
            test_config['test_type'] = test_config.get('type', 'UI_VARIANT')
            test_config['created_at'] = timezone.now().isoformat()

            return test_config

        except Exception as e:
            logger.error(f"Error getting test config for {test_name}: {e}")
            return {}

    @classmethod
    def track_test_event(cls, test_name: str, user_id: str, event_type: str,
                        event_data: Dict[str, Any] = None) -> bool:
        """
        Track events for A/B testing analytics
        """
        try:
            event_data = event_data or {}

            # Create event record
            event_record = {
                'test_name': test_name,
                'user_id': user_id,
                'user_segment': cls.get_user_segment(user_id, test_name),
                'event_type': event_type,
                'timestamp': timezone.now().isoformat(),
                'event_data': event_data
            }

            # Store in cache for real-time analytics (temporary storage)
            cache_key = f"ab_test_event:{test_name}:{user_id}:{event_type}:{int(timezone.now().timestamp())}"
            cache.set(cache_key, event_record, timeout=86400)  # Store for 24 hours

            # Also store in analytics aggregation cache
            agg_key = f"ab_test_agg:{test_name}:{event_type}:daily:{timezone.now().date()}"
            current_data = cache.get(agg_key, {'count': 0, 'segments': {'control': 0, 'variant_a': 0, 'variant_b': 0}})

            current_data['count'] += 1
            segment = event_record['user_segment']
            if segment in current_data['segments']:
                current_data['segments'][segment] += 1

            cache.set(agg_key, current_data, timeout=86400 * 7)  # Keep for 7 days

            return True

        except Exception as e:
            logger.error(f"Error tracking A/B test event: {e}")
            return False

    @classmethod
    def get_test_analytics(cls, test_name: str, period: str = '7d') -> Dict[str, Any]:
        """
        Get analytics for a specific A/B test
        """
        try:
            analytics = {
                'test_name': test_name,
                'period': period,
                'segments': {
                    'control': {'events': 0, 'metrics': {}},
                    'variant_a': {'events': 0, 'metrics': {}},
                    'variant_b': {'events': 0, 'metrics': {}}
                },
                'summary': {},
                'recommendations': []
            }

            # Get date range
            if period == '1d':
                start_date = timezone.now() - timedelta(days=1)
            elif period == '7d':
                start_date = timezone.now() - timedelta(days=7)
            elif period == '30d':
                start_date = timezone.now() - timedelta(days=30)
            else:
                start_date = timezone.now() - timedelta(days=7)

            # Collect daily aggregated data
            current_date = start_date
            while current_date <= timezone.now():
                date_key = current_date.strftime('%Y-%m-%d')

                for segment in ['control', 'variant_a', 'variant_b']:
                    # Try different event types
                    for event_type in ['page_view', 'click', 'conversion', 'test_completion']:
                        agg_key = f"ab_test_agg:{test_name}:{event_type}:daily:{current_date.date()}"
                        daily_data = cache.get(agg_key, {})

                        if daily_data and segment in daily_data['segments']:
                            analytics['segments'][segment]['events'] += daily_data['segments'][segment]

                current_date += timedelta(days=1)

            # Calculate metrics based on test configuration
            test_config = cls.DEFAULT_CONFIGS.get(test_name, {})
            metrics = test_config.get('metrics', ['conversion_rate'])

            for metric in metrics:
                for segment in analytics['segments']:
                    if metric == 'conversion_rate':
                        # Calculate conversion rate (conversions / total_events)
                        total_events = analytics['segments'][segment]['events']
                        conversions = cls._get_metric_count(test_name, segment, 'conversion', period)
                        if total_events > 0:
                            analytics['segments'][segment]['metrics'][metric] = (conversions / total_events) * 100

                    elif metric == 'click_through_rate':
                        # Calculate CTR
                        clicks = cls._get_metric_count(test_name, segment, 'click', period)
                        views = cls._get_metric_count(test_name, segment, 'page_view', period)
                        if views > 0:
                            analytics['segments'][segment]['metrics'][metric] = (clicks / views) * 100

                    elif metric == 'engagement_time':
                        # Average engagement time (mock calculation)
                        analytics['segments'][segment]['metrics'][metric] = random.uniform(120, 300)  # 2-5 minutes

            # Calculate winner and recommendations
            analytics['summary'] = cls._calculate_test_summary(analytics, metrics)
            analytics['recommendations'] = cls._generate_recommendations(analytics, test_config)

            return analytics

        except Exception as e:
            logger.error(f"Error getting A/B test analytics: {e}")
            return {}

    @classmethod
    def _get_metric_count(cls, test_name: str, segment: str, metric_type: str, period: str) -> int:
        """Helper method to get metric count from cache"""
        try:
            total_count = 0

            # Calculate date range
            if period == '1d':
                start_date = timezone.now() - timedelta(days=1)
            elif period == '7d':
                start_date = timezone.now() - timedelta(days=7)
            elif period == '30d':
                start_date = timezone.now() - timedelta(days=30)
            else:
                start_date = timezone.now() - timedelta(days=7)

            current_date = start_date
            while current_date <= timezone.now():
                agg_key = f"ab_test_agg:{test_name}:{metric_type}:daily:{current_date.date()}"
                daily_data = cache.get(agg_key, {})

                if daily_data and segment in daily_data['segments']:
                    total_count += daily_data['segments'][segment]

                current_date += timedelta(days=1)

            return total_count

        except Exception:
            return 0

    @classmethod
    def _calculate_test_summary(cls, analytics: Dict[str, Any], metrics: List[str]) -> Dict[str, Any]:
        """Calculate test summary and statistical significance"""
        summary = {
            'total_events': 0,
            'winner': None,
            'confidence': 0,
            'improvement': 0,
            'statistical_significance': False,
            'test_duration': '7d'
        }

        try:
            # Calculate total events
            for segment_data in analytics['segments'].values():
                summary['total_events'] += segment_data['events']

            # Determine winner based on primary metric (usually conversion_rate)
            primary_metric = metrics[0] if metrics else 'conversion_rate'
            best_segment = None
            best_value = 0

            for segment_name, segment_data in analytics['segments'].items():
                if primary_metric in segment_data['metrics']:
                    value = segment_data['metrics'][primary_metric]
                    if value > best_value:
                        best_value = value
                        best_segment = segment_name

            if best_segment and best_segment != 'control':
                summary['winner'] = best_segment
                control_value = analytics['segments']['control']['metrics'].get(primary_metric, 0)
                if control_value > 0:
                    improvement = ((best_value - control_value) / control_value) * 100
                    summary['improvement'] = round(improvement, 2)

            # Simple statistical significance calculation
            # (In production, this would use proper statistical tests like chi-square or t-test)
            if summary['total_events'] > 1000:  # Minimum sample size
                summary['statistical_significance'] = True
                summary['confidence'] = min(95, summary['total_events'] / 100)  # Simplified confidence

        except Exception as e:
            logger.error(f"Error calculating test summary: {e}")

        return summary

    @classmethod
    def _generate_recommendations(cls, analytics: Dict[str, Any], test_config: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        try:
            summary = analytics.get('summary', {})

            if summary.get('statistical_significance', False):
                winner = summary.get('winner')
                if winner:
                    improvement = summary.get('improvement', 0)
                    if improvement > 5:
                        recommendations.append(f"Winner '{winner}' shows {improvement}% improvement - consider implementing as default")
                    elif improvement > 0:
                        recommendations.append(f"Winner '{winner}' shows modest improvement - run test longer for more confidence")
                    else:
                        recommendations.append("No significant improvement detected - consider redesigning test variants")
                else:
                    recommendations.append("No clear winner - consider adjusting test parameters or extending duration")
            else:
                recommendations.append("Test hasn't reached statistical significance - increase sample size or run longer")

            # Traffic recommendations
            total_events = summary.get('total_events', 0)
            if total_events < 1000:
                recommendations.append("Increase traffic allocation for faster statistical significance")
            elif total_events > 10000:
                recommendations.append("Sufficient sample size achieved - consider ending test")

        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")

        return recommendations

    @classmethod
    def create_custom_test(cls, test_name: str, test_config: Dict[str, Any]) -> bool:
        """
        Create a custom A/B test configuration
        """
        try:
            # Validate test configuration
            required_fields = ['type', 'control', 'variant_a']
            for field in required_fields:
                if field not in test_config:
                    logger.error(f"Missing required field '{field}' in test configuration")
                    return False

            # Add to default configurations
            cls.DEFAULT_CONFIGS[test_name] = test_config.copy()

            # Cache the new configuration
            cache_key = f"ab_test_config:{test_name}"
            cache.set(cache_key, test_config, timeout=86400 * 30)  # Cache for 30 days

            logger.info(f"Created custom A/B test: {test_name}")
            return True

        except Exception as e:
            logger.error(f"Error creating custom test: {e}")
            return False

    @classmethod
    def end_test(cls, test_name: str, implement_winner: bool = False) -> Dict[str, Any]:
        """
        End an A/B test and optionally implement the winner
        """
        try:
            # Get final analytics
            analytics = cls.get_test_analytics(test_name, '30d')

            result = {
                'test_name': test_name,
                'ended_at': timezone.now().isoformat(),
                'analytics': analytics,
                'winner_implemented': False
            }

            if implement_winner:
                winner = analytics.get('summary', {}).get('winner')
                if winner and winner != 'control':
                    # In production, this would trigger implementation logic
                    result['winner_implemented'] = True
                    result['implementation_details'] = {
                        'winning_variant': winner,
                        'improvement': analytics.get('summary', {}).get('improvement', 0),
                        'implemented_at': timezone.now().isoformat()
                    }

            # Clean up cache data for this test
            cls._cleanup_test_data(test_name)

            logger.info(f"Ended A/B test: {test_name}")
            return result

        except Exception as e:
            logger.error(f"Error ending test: {e}")
            return {'error': str(e)}

    @classmethod
    def _cleanup_test_data(cls, test_name: str):
        """Clean up cache data for a completed test"""
        try:
            # Clean up daily aggregation data
            pattern = f"ab_test_agg:{test_name}:*"
            # Note: In production, you'd use cache backend-specific pattern deletion

            # Mark test as ended in configuration
            if test_name in cls.DEFAULT_CONFIGS:
                cls.DEFAULT_CONFIGS[test_name]['ended_at'] = timezone.now().isoformat()
                cls.DEFAULT_CONFIGS[test_name]['status'] = 'ended'

        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")

    @classmethod
    def get_all_active_tests(cls) -> List[Dict[str, Any]]:
        """Get all active A/B tests"""
        try:
            active_tests = []

            for test_name, test_config in cls.DEFAULT_CONFIGS.items():
                if test_config.get('status') != 'ended':
                    test_info = {
                        'name': test_name,
                        'type': test_config.get('type'),
                        'created_at': test_config.get('created_at'),
                        'status': 'active'
                    }
                    active_tests.append(test_info)

            return active_tests

        except Exception as e:
            logger.error(f"Error getting active tests: {e}")
            return []


class ClientSideABTesting:
    """Client-side A/B testing utilities"""

    @staticmethod
    def get_client_config(test_name: str, user_identifier: str) -> Dict[str, Any]:
        """
        Get A/B test configuration for client-side use
        """
        try:
            test_config = ABTestService.get_test_config(test_name, user_identifier)

            if not test_config:
                return {}

            # Return only client-relevant data
            client_config = {
                'testName': test_name,
                'variant': test_config.get('user_segment'),
                'config': test_config.get('variant_config', {}),
                'tracking': {
                    'enabled': True,
                    'events': ['impression', 'click', 'conversion']
                }
            }

            return client_config

        except Exception as e:
            logger.error(f"Error getting client config: {e}")
            return {}

    @staticmethod
    def should_show_feature(feature_name: str, user_identifier: str) -> bool:
        """
        Simple feature flag using A/B testing framework
        """
        try:
            # Create 50/50 split for feature flags
            hash_input = f"{feature_name}:{user_identifier}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)

            # Return True for 50% of users
            return (hash_value % 2) == 0

        except Exception:
            return False  # Fail safe: don't show experimental features