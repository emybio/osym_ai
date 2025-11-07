import React, { useState } from 'react';
import {
  Award,
  BarChart3,
  Brain,
  Clock,
  FileText,
  Loader2,
} from 'lucide-react';
import { STUDENT_STATS, AI_RECOMMENDATIONS } from '../constants';
import LoadingSpinner from './LoadingSpinner';

const HomePage = ({ onStartExam }) => {
  const [isStarting, setIsStarting] = useState(false);

  const handleStartExam = async () => {
    setIsStarting(true);
    await onStartExam();
    setIsStarting(false);
  };

  return (
  <div className="grid gap-6 lg:grid-cols-3">
    <div className="lg:col-span-2 space-y-6">
      <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl p-8 text-white shadow-lg">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="text-blue-100 uppercase text-xs tracking-[0.3em]">AI Destekli Sınav</p>
            <h2 className="text-3xl font-semibold mt-2 mb-3">Bugün tek bir soru ile başla</h2>
            <p className="text-blue-100 max-w-xl">
              Yapay zeka seviyene uygun özgün sorular üretir, yanıtını analiz eder ve eksik olduğun konular için öneriler sunar.
            </p>
          </div>
          <button
            onClick={handleStartExam}
            disabled={isStarting}
            className="px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl shadow hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Hazırlanıyor...
              </>
            ) : (
              'AI Sorusu Oluştur'
            )}
          </button>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <Award className="w-10 h-10 text-yellow-500" />
            <div>
              <p className="text-sm text-gray-500">Ortalama başarı</p>
              <p className="text-2xl font-semibold text-gray-900">{STUDENT_STATS.avgScore}%</p>
            </div>
          </div>
          <p className="text-sm text-gray-500">Son 5 sınavda ortalama başarı oranı.</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-10 h-10 text-blue-500" />
            <div>
              <p className="text-sm text-gray-500">Çalışma serisi</p>
              <p className="text-2xl font-semibold text-gray-900">7 gün</p>
            </div>
          </div>
          <p className="text-sm text-gray-500">Planına sadık kalmaya devam et!</p>
        </div>
      </div>
    </div>

    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          Son Sınavlar
        </h3>
        <div className="space-y-3">
          {STUDENT_STATS.recentExams.map((exam, idx) => (
            <div key={idx} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2.5">
              <div>
                <p className="text-sm font-medium text-gray-900">{exam.subject}</p>
                <p className="text-xs text-gray-500">{exam.date}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-green-600">%{exam.score}</p>
                <p className="text-xs text-gray-500">{exam.duration}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
          <Brain className="w-5 h-5 text-purple-600" />
          AI Önerileri
        </h3>
        <div className="space-y-3">
          {AI_RECOMMENDATIONS.map((item, idx) => (
            <div key={idx} className="border border-gray-100 rounded-lg p-3 bg-gray-50">
              <p className="text-sm font-semibold text-gray-900">{item.title}</p>
              <p className="text-xs text-gray-500">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
  );
};

export default HomePage;