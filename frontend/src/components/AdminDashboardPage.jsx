import React, { useState } from 'react';
import {
  BarChart3,
  Database,
  Beaker,
  Settings,
  AlertCircle,
  CheckCircle,
  TrendingUp,
  Activity,
  Users,
} from 'lucide-react';
import AnalyticsPage from './AnalyticsPage';
import DatabaseStatusPage from './DatabaseStatusPage';
import ABTestingPage from './ABTestingPage';

const AdminDashboardPage = () => {
  const [activeTab, setActiveTab] = useState('analytics');

  const tabs = [
    {
      id: 'analytics',
      label: 'Analytics',
      icon: BarChart3,
      description: 'Sistem analitikleri ve istatistikleri'
    },
    {
      id: 'database',
      label: 'Veritabanı',
      icon: Database,
      description: 'Veritabanı durumu ve optimizasyonu'
    },
    {
      id: 'ab_testing',
      label: 'A/B Testing',
      icon: Beaker,
      description: 'A/B test yönetimi ve sonuçları'
    },
  ];

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-8 h-8 text-blue-600" />
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Sistem Yönetim Paneli</h1>
        </div>
        <p className="text-gray-500">Sistem performansı, analitikleri ve test yönetimini kontrol edin</p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border border-gray-200 rounded-xl p-1 flex gap-1 flex-wrap">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              title={tab.description}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'analytics' && (
          <div className="animate-in fade-in duration-300">
            <AnalyticsPage />
          </div>
        )}
        {activeTab === 'database' && (
          <div className="animate-in fade-in duration-300">
            <DatabaseStatusPage />
          </div>
        )}
        {activeTab === 'ab_testing' && (
          <div className="animate-in fade-in duration-300">
            <ABTestingPage />
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboardPage;
