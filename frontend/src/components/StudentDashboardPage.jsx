import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../api/config';
import {
  Award,
  BarChart3,
  BookOpen,
  CheckCircle,
  FileText,
  TrendingUp,
  Clock,
  Target,
  Activity,
} from 'lucide-react';
import { STUDENT_STATS, WEEKLY_ACTIVITY, WEEK_DAYS } from '../constants';

const StatisticCard = ({ title, value, icon: Icon, accent }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-3 sm:p-5 flex items-center gap-3 sm:gap-4 shadow-sm">
    <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center ${accent}`}>
      <Icon className="w-5 h-5 sm:w-6 sm:h-6" />
    </div>
    <div>
      <p className="text-xs sm:text-sm text-gray-500">{title}</p>
      <p className="text-lg sm:text-2xl font-semibold text-gray-900">{value ? value.toLocaleString() : '0'}</p>
    </div>
  </div>
);

const StudentDashboardPage = () => {
  const [quickTestStats, setQuickTestStats] = useState(null);
  const [quickTestResults, setQuickTestResults] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch quick test stats and results
  useEffect(() => {
    const fetchQuickTestData = async () => {
      try {
        // Get dashboard stats
        const statsResponse = await fetch(getApiUrl('/dashboard/stats/'), {
          credentials: 'same-origin'
        });

        // Get quick test results
        const resultsResponse = await fetch(getApiUrl('/quicktest/results/'), {
          credentials: 'same-origin'
        });

        if (statsResponse.ok) {
          const statsData = await statsResponse.json();
          setQuickTestStats(statsData);
        }

        if (resultsResponse.ok) {
          const resultsData = await resultsResponse.json();
          setQuickTestResults(resultsData.results || []);
        }
      } catch (error) {
        console.error('Error fetching quick test data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchQuickTestData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Öğrenci Paneli</h1>
        <p className="text-gray-500 mt-2">Çalışma istatistikleri ve ilerlemenizi takip edin</p>
      </div>

      {/* Original Stats + Quick Test Stats */}
      <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
        <StatisticCard
          title="Toplam Çözülen Soru"
          value={STUDENT_STATS.totalQuestions}
          icon={FileText}
          accent="bg-blue-500/10 text-blue-600"
        />
        <StatisticCard
          title="Doğru Cevap"
          value={STUDENT_STATS.correctAnswers}
          icon={CheckCircle}
          accent="bg-emerald-500/10 text-emerald-600"
        />
        <StatisticCard
          title="Sınav Sayısı"
          value={STUDENT_STATS.totalExams}
          icon={Award}
          accent="bg-purple-500/10 text-purple-600"
        />
        {!loading && quickTestStats ? (
          <StatisticCard
            title="Hızlı Test"
            value={quickTestStats.quick_test_count || 0}
            icon={Activity}
            accent="bg-green-500/10 text-green-600"
          />
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl p-3 sm:p-5 flex items-center gap-3 sm:gap-4 shadow-sm">
            <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center bg-gray-100">
              <Activity className="w-5 h-5 sm:w-6 sm:h-6 text-gray-400" />
            </div>
            <div>
              <p className="text-xs sm:text-sm text-gray-500">Hızlı Test</p>
              <div className="w-12 sm:w-16 h-3 sm:h-4 bg-gray-200 rounded animate-pulse"></div>
            </div>
          </div>
        )}
      </div>

    {/* Quick Test Results Section */}
      {!loading && quickTestResults.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-600" />
              Hızlı Test Sonuçları
            </h3>
            {!loading && quickTestStats && (
              <div className="flex items-center gap-3 sm:gap-4 text-xs sm:text-sm text-gray-600">
                <div className="flex items-center gap-1">
                  <Target className="w-3 h-3 sm:w-4 sm:h-4" />
                  <span>Ortalama: %{quickTestStats.average_score?.toFixed(1) || 0}</span>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2 sm:space-y-3">
            {quickTestResults.slice(0, 5).map((result, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-3 sm:p-4 bg-gray-50 rounded-lg border border-gray-100 gap-3 sm:gap-0">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-xs sm:text-sm font-bold flex-shrink-0 ${
                    result.percentage >= 70 ? 'bg-green-100 text-green-700' :
                    result.percentage >= 50 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {result.percentage.toFixed(0)}%
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900 text-sm sm:text-base truncate">
                      {result.exam_type} {result.branch}
                    </p>
                    <p className="text-xs sm:text-sm text-gray-500">
                      {result.correct_count}/{result.total_questions} doğru • {new Date(result.created_at).toLocaleDateString('tr-TR')}
                    </p>
                  </div>
                </div>
                <div className="text-right sm:text-right">
                  <p className="text-xs sm:text-sm font-medium text-gray-900">
                    {result.percentage >= 70 ? 'Harika!' :
                     result.percentage >= 50 ? 'İyi' : 'Geliştirilebilir'}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {quickTestResults.length > 5 && (
            <div className="text-center mt-4">
              <button className="text-blue-600 hover:text-blue-700 font-medium text-sm">
                Tüm {quickTestResults.length} test sonucunu göster →
              </button>
            </div>
          )}
        </div>
      )}

      {/* Original content */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Haftalık çalışma grafiği</h3>
          <div className="flex items-end gap-3 h-48">
            {WEEKLY_ACTIVITY.map((value, idx) => (
              <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full bg-gray-100 rounded-t-xl overflow-hidden h-full relative">
                  <div
                    className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-blue-600 to-blue-400"
                    style={{ height: `${value}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 font-medium">{WEEK_DAYS[idx]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-3">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              Güçlü konular
            </h3>
            <div className="space-y-2">
              {STUDENT_STATS.strongTopics.map((topic, idx) => (
                <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700 text-sm font-medium">
                  <span>{topic}</span>
                  <span>%{85 + idx * 3}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-3">
              <BookOpen className="w-5 h-5 text-rose-600" />
              Çalışılması gereken
            </h3>
            <div className="space-y-2">
              {STUDENT_STATS.weakTopics.map((topic, idx) => (
                <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-lg bg-rose-50 text-rose-600 text-sm font-medium">
                  <span>{topic}</span>
                  <span>%{45 + idx * 5}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentDashboardPage;
