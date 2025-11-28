import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  TrendingUp,
  TrendingDown,
  Award,
  Target,
  Clock,
  AlertCircle,
  BarChart3,
  Brain,
  Activity,
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';
import Toast from './Toast';
import { getApiUrl } from '../api/config';

const ProgressPage = () => {
  const [performance, setPerformance] = useState(null);
  const [topicAnalysis, setTopicAnalysis] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    fetchProgressData();
  }, []);

  const fetchProgressData = async () => {
    try {
      setLoading(true);

      // Parallel API calls with error handling
      const [performanceRes, topicsRes, recommendationsRes] = await Promise.allSettled([
        fetch(getApiUrl('/stats/performance/')),
        fetch(getApiUrl('/stats/topics/')),
        fetch(getApiUrl('/stats/recommendations/'))
      ]);

      // Handle each response separately with better defaults
      const performanceData = performanceRes.status === 'fulfilled' ? await performanceRes.value.json() : {
        performance: {
          basic_stats: { average_score: 0, total_tests: 0, highest_score: 0, current_streak: 0, best_streak: 0, total_time_hours: 0 },
          weekly_performance: { test_count: 0, average_score: 0, total_time_minutes: 0, improvement: 0 },
          improvement_trend: { trend: 'stable', percentage: 0 },
          performance_prediction: { predicted_score: 0, confidence: 0, prediction: 'stable' }
        }
      };
      const topicsData = topicsRes.status === 'fulfilled' ? await topicsRes.value.json() : {
        topics: {
          strong_topics: [],
          weak_topics: [],
          moderate_topics: [],
          total_topics: 0
        }
      };
      const recommendationsData = recommendationsRes.status === 'fulfilled' ? await recommendationsRes.value.json() : { recommendations: [] };

      setPerformance(performanceData);
      setTopicAnalysis(topicsData);
      setRecommendations(recommendationsData);

    } catch (error) {
      console.error('Progress data fetch error:', error);
      showToast('İstatistikler yüklenirken bir hata oluştu', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'improving':
        return <TrendingUp className="w-4 h-4 text-green-600" />;
      case 'declining':
        return <TrendingDown className="w-4 h-4 text-red-600" />;
      default:
        return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  const getTrendColor = (trend) => {
    switch (trend) {
      case 'improving':
        return 'text-green-600';
      case 'declining':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Performance Overview */}
      {performance && (
        <div className="grid gap-4 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
              <BarChart3 className="w-4 h-4 sm:w-5 sm:h-5 text-blue-600" />
              Performans Özeti
            </h3>

            <div className="space-y-3 sm:space-y-4">
              <div className="text-center">
                <p className="text-2xl sm:text-3xl font-bold text-blue-900">
                  {performance.basic_stats?.average_score || 0}%
                </p>
                <p className="text-xs sm:text-sm text-gray-500">Ortalama Skor</p>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm">
                <div className="text-center p-2 sm:p-3 rounded-lg bg-blue-50">
                  <p className="font-semibold text-blue-900 text-sm sm:text-base">
                    {performance.basic_stats?.total_tests || 0}
                  </p>
                  <p className="text-blue-700 text-xs sm:text-sm">Toplam Test</p>
                </div>
                <div className="text-center p-2 sm:p-3 rounded-lg bg-green-50">
                  <p className="font-semibold text-green-900 text-sm sm:text-base">
                    {performance.basic_stats?.highest_score || 0}%
                  </p>
                  <p className="text-green-700 text-xs sm:text-sm">En Yüksek</p>
                </div>
              </div>

              {/* Trend */}
              {performance.improvement_trend && (
                <div className="flex items-center justify-between p-2 sm:p-3 rounded-lg bg-gray-50">
                  <span className="text-xs sm:text-sm text-gray-600">Gelişim Trendi</span>
                  <div className="flex items-center gap-1 sm:gap-2">
                    {getTrendIcon(performance.improvement_trend.trend)}
                    <span className={`text-xs sm:text-sm font-medium ${getTrendColor(performance.improvement_trend.trend)}`}>
                      {performance.improvement_trend.percentage > 0 ? '+' : ''}{performance.improvement_trend.percentage}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Streak Information */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-orange-600" />
              Seri Takibi
            </h3>

            <div className="space-y-3 sm:space-y-4">
              <div className="text-center">
                <p className="text-2xl sm:text-3xl font-bold text-orange-900">
                  {performance.basic_stats?.current_streak || 0}
                </p>
                <p className="text-xs sm:text-sm text-gray-500">Mevcut Seri</p>
              </div>

              <div className="text-center p-2 sm:p-3 rounded-lg bg-orange-50">
                <p className="text-xl sm:text-2xl font-bold text-orange-900">
                  {performance.basic_stats?.best_streak || 0}
                </p>
                <p className="text-orange-700 text-xs sm:text-sm">En İyi Seri</p>
              </div>

              <div className="text-center p-2 sm:p-3 rounded-lg bg-blue-50">
                <Clock className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600 mx-auto mb-1 sm:mb-2" />
                <p className="text-xs sm:text-sm font-medium text-blue-900">
                  {Math.round(performance.basic_stats?.total_time_hours || 0)} saat
                </p>
                <p className="text-blue-700 text-xs sm:text-sm">Toplam Çalışma</p>
              </div>
            </div>
          </div>

          {/* Weekly Performance */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
              <Target className="w-4 h-4 sm:w-5 sm:h-5 text-purple-600" />
              Haftalık Performans
            </h3>

            <div className="space-y-3 sm:space-y-4">
              <div className="text-center">
                <p className="text-2xl sm:text-3xl font-bold text-purple-900">
                  {performance.weekly_performance?.test_count || 0}
                </p>
                <p className="text-xs sm:text-sm text-gray-500">Bu Hafta Test</p>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:gap-3 text-xs sm:text-sm">
                <div className="text-center p-2 sm:p-3 rounded-lg bg-purple-50">
                  <p className="font-semibold text-purple-900 text-sm sm:text-base">
                    {performance.weekly_performance?.average_score || 0}%
                  </p>
                  <p className="text-purple-700 text-xs sm:text-sm">Haftalık Ortalama</p>
                </div>
                <div className="text-center p-2 sm:p-3 rounded-lg bg-green-50">
                  <p className="font-semibold text-green-900 text-sm sm:text-base">
                    {Math.round(performance.weekly_performance?.total_time_minutes || 0)} dk
                  </p>
                  <p className="text-green-700 text-xs sm:text-sm">Haftalık Süre</p>
                </div>
              </div>

              {performance.weekly_performance?.improvement !== 0 && performance.weekly_performance?.improvement !== undefined && (
                <div className="flex items-center justify-center p-2 sm:p-3 rounded-lg bg-gray-50">
                  {performance.weekly_performance.improvement > 0 ? (
                    <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4 text-green-600 mr-1 sm:mr-2" />
                  ) : (
                    <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4 text-red-600 mr-1 sm:mr-2" />
                  )}
                  <span className={`text-xs sm:text-sm font-medium ${
                    performance.weekly_performance.improvement > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {performance.weekly_performance.improvement > 0 ? '+' : ''}{performance.weekly_performance.improvement}%
                    geçen haftaya göre
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Performance Prediction */}
          {performance.performance_prediction && (
            <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
              <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
                <Brain className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-600" />
                AI Tahmini
              </h3>

              <div className="space-y-3 sm:space-y-4">
                <div className="text-center">
                  <p className="text-2xl sm:text-3xl font-bold text-indigo-900">
                    {performance.performance_prediction.predicted_score || 0}%
                  </p>
                  <p className="text-xs sm:text-sm text-gray-500">Tahmini Sonraki Skor</p>
                </div>

                <div className="text-center p-2 sm:p-3 rounded-lg bg-indigo-50">
                  <div className="flex items-center justify-center gap-1 sm:gap-2 mb-1 sm:mb-2">
                    <div className="text-xs sm:text-sm text-gray-600">Güven:</div>
                    <div className="w-12 sm:w-16 bg-gray-200 rounded-full h-1.5 sm:h-2">
                      <div
                        className="bg-indigo-600 h-1.5 sm:h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(performance.performance_prediction.confidence || 0) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs sm:text-sm font-medium text-indigo-900">
                      {Math.round((performance.performance_prediction.confidence || 0) * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-indigo-700">
                    {performance.performance_prediction.prediction === 'improving' && 'İyileşme eğilimindesiniz'}
                    {performance.performance_prediction.prediction === 'declining' && 'Düşüş eğilimindesiniz'}
                    {performance.performance_prediction.prediction === 'stable' && 'Kararlı performans'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Topic Analysis */}
      {topicAnalysis && (
        <div className="grid gap-4 sm:gap-6 grid-cols-1 md:grid-cols-2">
          {/* Strong Topics */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
              <Award className="w-4 h-4 sm:w-5 sm:h-5 text-green-600" />
              Güçlü Olduğun Konular
            </h3>

            {topicAnalysis.strong_topics?.length > 0 ? (
              <div className="space-y-2 sm:space-y-3">
                {topicAnalysis.strong_topics.slice(0, 5).map((topic, index) => (
                  <div key={index} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-2 sm:p-3 rounded-lg bg-green-50 gap-2 sm:gap-0">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-green-900 text-sm sm:text-base truncate">{topic.topic}</p>
                      <p className="text-xs sm:text-sm text-green-700">
                        {topic.total_attempts} deneme
                      </p>
                    </div>
                    <div className="text-right sm:text-left">
                      <p className="text-base sm:text-lg font-bold text-green-900">{topic.accuracy_rate}%</p>
                      <p className="text-xs text-green-700">Doğruluk</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4 text-sm">
                Henüz yeterli veri bulunmuyor
              </p>
            )}
          </div>

          {/* Weak Topics */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
              <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-600" />
              Geliştirilmesi Gereken Konular
            </h3>

            {topicAnalysis.weak_topics?.length > 0 ? (
              <div className="space-y-2 sm:space-y-3">
                {topicAnalysis.weak_topics.slice(0, 5).map((topic, index) => (
                  <div key={index} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-2 sm:p-3 rounded-lg bg-red-50 gap-2 sm:gap-0">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-red-900 text-sm sm:text-base truncate">{topic.topic}</p>
                      <p className="text-xs sm:text-sm text-red-700">
                        {topic.total_attempts} deneme
                      </p>
                    </div>
                    <div className="text-right sm:text-left">
                      <p className="text-base sm:text-lg font-bold text-red-900">{topic.accuracy_rate}%</p>
                      <p className="text-xs text-red-700">Doğruluk</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4 text-sm">
                Henüz yeterli veri bulunmuyor
              </p>
            )}
          </div>
        </div>
      )}

      {/* Learning Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
          <h3 className="flex items-center gap-2 text-sm sm:text-base text-gray-900 font-semibold mb-3 sm:mb-4">
            <Brain className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-600" />
            Kişiselleştirilmiş Öneriler
          </h3>

          <div className="grid gap-3 sm:gap-4 grid-cols-1 md:grid-cols-2">
            {recommendations.map((rec, index) => (
              <div
                key={index}
                className={`p-3 sm:p-4 rounded-lg border-l-4 ${
                  rec.priority === 'high'
                    ? 'bg-red-50 border-red-400'
                    : rec.priority === 'medium'
                    ? 'bg-yellow-50 border-yellow-400'
                    : 'bg-blue-50 border-blue-400'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-0">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-900 mb-1 text-sm sm:text-base">{rec.title}</h4>
                    <p className="text-xs sm:text-sm text-gray-600 mb-2 sm:mb-3">{rec.description}</p>
                    {rec.action_url && (
                      <button
                        onClick={() => window.location.href = rec.action_url}
                        className="text-xs sm:text-sm font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
                      >
                        {rec.action_text} →
                      </button>
                    )}
                  </div>
                  {rec.priority === 'high' && (
                    <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-500 flex-shrink-0 ml-0 sm:ml-2" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:justify-center gap-3 sm:gap-4">
        <button
          onClick={() => window.location.href = '/quick-test'}
          className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm sm:text-base"
        >
          Yeni Test Başlat
        </button>
        <button
          onClick={fetchProgressData}
          className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium text-sm sm:text-base"
        >
          Verileri Yenile
        </button>
        <button
          onClick={() => window.location.href = '/api/v1/stats/export/'}
          className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-sm sm:text-base"
        >
          İstatistikleri İndir
        </button>
      </div>
    </div>
  );
};

export default ProgressPage;