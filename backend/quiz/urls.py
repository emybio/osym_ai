from django.urls import path
from . import views
from . import auth_views
from . import optimized_views

app_name = 'quiz'

urlpatterns = [
    path("questions/", views.question_list, name='question-list'),
    path("questions/generate/", views.generate_question, name='generate-question'),
    path("questions/<int:pk>/explain/", views.explain, name='explain-question'),
    path("questions/stats/", views.question_stats, name='question-stats'),
    path("questions/cleanup/", views.cleanup_questions, name='cleanup-questions'),

    # PDF management endpoints
    path("pdf/upload/", views.bulk_pdf_upload, name='bulk-pdf-upload'),
    path("pdf/stats/", views.pdf_stats, name='pdf-stats'),
    path("pdf/process/<int:pdf_id>/", views.process_pdf, name='process-pdf'),
    path("subjects/", views.get_subjects, name='get-subjects'),

    # Authentication endpoints
    path("auth/csrf/", auth_views.get_csrf_token, name='get-csrf-token'),
    path("auth/login/", auth_views.login_view, name='login'),
    path("auth/logout/", auth_views.logout_view, name='logout'),
    path("auth/profile/", auth_views.user_profile, name='user-profile'),
    path("auth/check/", auth_views.check_auth, name='check-auth'),

    # Hızlı Test endpoint'leri
    path("quicktest/init/", views.init_temp_exam, name='init-temp-exam'),
    path("quicktest/status/", views.get_exam_status, name='get-exam-status'),
    path("quicktest/get/", views.get_temp_exam, name='get-temp-exam'),
    path("quicktest/save/", views.save_temp_exam, name='save-temp-exam'),
    path("quicktest/summary/", views.temp_exam_summary, name='temp-exam-summary'),
    path("quicktest/register/", views.register_and_merge, name='register-and-merge'),
    path("quicktest/results/", views.quicktest_results, name='quicktest-results'),
    path("dashboard/stats/", views.dashboard_stats, name='dashboard-stats'),

    # Progressive Statistics endpoint'leri
    path("stats/performance/", views.get_anonymous_performance_overview, name='anonymous-performance-overview'),
    path("stats/progress/", views.get_anonymous_progress_chart, name='anonymous-progress-chart'),
    path("stats/topics/", views.get_anonymous_topic_analysis, name='anonymous-topic-analysis'),
    path("stats/recommendations/", views.get_anonymous_recommendations, name='anonymous-recommendations'),
    path("stats/export/", views.export_anonymous_statistics, name='export-anonymous-statistics'),
    path("stats/cache/clear/", views.clear_anonymous_cache, name='clear-anonymous-cache'),

    # Gamification endpoint'leri
    path("gamification/profile/", views.get_gamification_profile, name='gamification-profile'),
    path("gamification/leaderboard/", views.get_leaderboard, name='leaderboard'),
    path("gamification/daily-challenge/", views.get_daily_challenge, name='daily-challenge'),
    path("gamification/achievements/", views.get_achievements_list, name='achievements-list'),
    path("gamification/claim-reward/", views.claim_reward, name='claim-reward'),

    # Adaptive Difficulty endpoint'leri
    path("adaptive/profile/", views.get_adaptive_difficulty_profile, name='adaptive-difficulty-profile'),
    path("adaptive/recommendations/", views.get_adaptive_recommendations, name='adaptive-recommendations'),
    path("adaptive/analytics/", views.get_difficulty_analytics, name='difficulty-analytics'),
    path("adaptive/reset/", views.reset_difficulty_profile, name='reset-difficulty-profile'),
    path("adaptive/preference/", views.set_manual_difficulty_preference, name='manual-difficulty-preference'),

    # Rate Limiting & Anti-Spam endpoint'leri
    path("rate-limits/status/", views.get_rate_limits_status, name='rate-limits-status'),
    path("rate-limits/check/", views.check_rate_limits, name='check-rate-limits'),
    path("security/report-suspicious/", views.report_suspicious_activity, name='report-suspicious-activity'),
    path("security/suspicious-activities/", views.get_suspicious_activities, name='get-suspicious-activities'),
    path("security/block-user/", views.manual_block_user, name='manual-block-user'),
    path("security/unblock-user/", views.manual_unblock_user, name='manual-unblock-user'),

    # Analytics & Insights endpoint'leri
    path("analytics/dashboard/", views.get_analytics_dashboard, name='analytics-dashboard'),
    path("analytics/user/", views.get_analytics_user, name='analytics-user'),
    path("analytics/content/", views.get_analytics_content, name='analytics-content'),
    path("analytics/engagement/", views.get_analytics_engagement, name='analytics-engagement'),
    path("analytics/conversion-funnel/", views.get_analytics_conversion_funnel, name='analytics-conversion-funnel'),

    # Database Optimization endpoint'leri
    path("database/status/", views.get_database_status, name='database-status'),
    path("database/metrics/", views.get_database_metrics, name='database-metrics'),
    path("database/optimize/", views.run_database_optimization, name='database-optimize'),
    path("database/cleanup/", views.run_cleanup, name='database-cleanup'),
    path("database/indexes/", views.optimize_indexes, name='database-indexes'),

    # A/B Testing endpoint'leri
    path("ab-tests/config/", views.get_ab_test_config, name='ab-test-config'),
    path("ab-tests/track/", views.track_ab_test_event, name='ab-test-track'),
    path("ab-tests/analytics/", views.get_ab_test_analytics, name='ab-test-analytics'),
    path("ab-tests/active/", views.get_active_ab_tests, name='ab-test-active'),
    path("ab-tests/create/", views.create_ab_test, name='ab-test-create'),
    path("ab-tests/end/", views.end_ab_test, name='ab-test-end'),
    path("ab-tests/client/", views.get_client_ab_config, name='ab-test-client'),
    path("ab-tests/feature-flag/", views.check_feature_flag, name='ab-test-feature-flag'),

    # Duplicate Prevention endpoint'leri
    path("duplicate/check-similarity/", views.check_question_similarity, name='check-question-similarity'),
    path("duplicate/diversity-stats/", views.get_question_diversity_stats, name='get-question-diversity-stats'),
    path("duplicate/batch-check/", views.batch_check_duplicates, name='batch-check-duplicates'),
    path("duplicate/mark/", views.mark_question_duplicates, name='mark-question-duplicates'),
    path("duplicate/overview/", views.get_duplicate_overview, name='get-duplicate-overview'),
    path("duplicate/settings/", views.update_duplicate_settings, name='update-duplicate-settings'),

    # Hybrid AI Provider System endpoint'leri
    path("ai/test-providers/", views.test_providers, name='test-providers'),
    path("ai/provider-metrics/", views.provider_metrics, name='provider-metrics'),
    path("ai/cost-estimate/", views.cost_estimate, name='cost-estimate'),

    # Optimized Question Selection endpoint'leri
    path("optimized/questions/", optimized_views.get_optimized_questions, name='get-optimized-questions'),
    path("optimized/answers/", optimized_views.submit_user_answers, name='submit-user-answers'),
    path("optimized/analytics/", optimized_views.get_user_analytics, name='get-user-analytics'),
    path("optimized/clear-cache/", optimized_views.clear_user_cache, name='clear-user-cache'),
    path("optimized/system-stats/", optimized_views.get_system_question_stats, name='get-system-question-stats'),
]
