import React from 'react';
import {
  BookOpen,
  TrendingUp,
} from 'lucide-react';

const ProgressPage = () => (
  <div className="grid gap-6 md:grid-cols-2">
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
        <TrendingUp className="w-5 h-5 text-blue-600" />
        Sınav performansı
      </h3>
      <p className="text-sm text-gray-500 mb-5">
        Son 6 sınavda performansındaki değişim. Yapay zeka, düzenli pratik ile başarı oranını %15 artırabileceğini öngörüyor.
      </p>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="p-4 rounded-xl bg-blue-50 text-blue-700 font-medium text-center">
          <p className="text-2xl font-semibold text-blue-900 mb-1">78%</p>
          Ortalama
        </div>
        <div className="p-4 rounded-xl bg-emerald-50 text-emerald-700 font-medium text-center">
          <p className="text-2xl font-semibold text-emerald-900 mb-1">+6%</p>
          Haftalık artış
        </div>
        <div className="p-4 rounded-xl bg-purple-50 text-purple-700 font-medium text-center">
          <p className="text-2xl font-semibold text-purple-900 mb-1">320 dk</p>
          Haftalık hedef
        </div>
      </div>
    </div>

    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
        <BookOpen className="w-5 h-5 text-indigo-600" />
        Çalışma planı
      </h3>
      <div className="space-y-3 text-sm text-gray-600">
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Pazartesi - Çarşamba: 45 dk Matematik, 30 dk Türkçe
        </div>
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Perşembe - Cuma: 40 dk Fen Bilimleri, 20 dk Sosyal Bilimler
        </div>
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Hafta sonu: 2 deneme sınavı + analiz
        </div>
      </div>
    </div>
  </div>
);

export default ProgressPage;