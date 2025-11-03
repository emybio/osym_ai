import React from 'react';
import {
  Award,
  BarChart3,
  BookOpen,
  CheckCircle,
  FileText,
  TrendingUp,
} from 'lucide-react';
import { STUDENT_STATS, WEEKLY_ACTIVITY, WEEK_DAYS } from '../constants';

const StatisticCard = ({ title, value, icon: Icon, accent }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4 shadow-sm">
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${accent}`}>
      <Icon className="w-6 h-6" />
    </div>
    <div>
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-2xl font-semibold text-gray-900">{value.toLocaleString()}</p>
    </div>
  </div>
);

const DashboardPage = () => (
  <div className="space-y-6">
    <div className="grid gap-4 md:grid-cols-3">
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
    </div>

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

export default DashboardPage;