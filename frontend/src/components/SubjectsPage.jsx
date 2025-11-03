import React from 'react';
import { SUBJECTS } from '../constants';

const SubjectsPage = () => (
  <div className="space-y-6">
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-4">Dersler</h2>
      <p className="text-gray-600 mb-6">
        Tüm derslerinizdeki ilerlemeyi detaylı şekilde takip edin. Her ders için çalışma istatistikleri, zayıf ve güçlü konular hakkında analizler.
      </p>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {SUBJECTS.map((subject) => (
          <div key={subject.id} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-4 mb-4">
              <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${subject.gradient} text-white flex items-center justify-center text-lg font-semibold`}>
                {subject.name.slice(0, 2)}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{subject.name}</h3>
                <p className="text-sm text-gray-500">{subject.badge}</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Başarı Oranı</span>
                <span className="text-sm font-semibold text-green-600">{75 + Math.floor(Math.random() * 20)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Çalışılan Süre</span>
                <span className="text-sm font-semibold text-blue-600">{Math.floor(Math.random() * 100 + 50)} saat</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Son Çalışma</span>
                <span className="text-sm font-semibold text-gray-600">{Math.floor(Math.random() * 7 + 1)} gün önce</span>
              </div>
            </div>

            <button className="w-full mt-4 px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors">
              Detayları Gör
            </button>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default SubjectsPage;