import React, { useState, useEffect } from 'react';
import { Database, Activity, Clock, TrendingUp, AlertTriangle, CheckCircle, Settings, Trash2 } from 'lucide-react';

const DatabaseStatusPage = () => {
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [adminKey, setAdminKey] = useState('');

  useEffect(() => {
    loadDatabaseStatus();
    loadDatabaseMetrics();
  }, []);

  const loadDatabaseStatus = async () => {
    try {
      const response = await fetch('/api/quiz/database/status/');
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Error loading database status:', error);
    }
  };

  const loadDatabaseMetrics = async () => {
    try {
      const response = await fetch('/api/quiz/database/metrics/');
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Error loading database metrics:', error);
    }
  };

  const runOptimization = async (type = 'full') => {
    if (!adminKey) {
      alert('Lütfen admin anahtarını girin');
      return;
    }

    setLoading(true);
    try {
      const endpoint = type === 'full' ? '/optimize/' : type === 'cleanup' ? '/cleanup/' : '/indexes/';
      const response = await fetch(`/api/quiz/database${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ admin_key: adminKey }),
      });

      const data = await response.json();

      if (response.ok) {
        setOptimizationResult(data);
        setTimeout(() => {
          loadDatabaseStatus();
          loadDatabaseMetrics();
        }, 2000);
      } else {
        alert('Hata: ' + data.error);
      }
    } catch (error) {
      console.error('Error running optimization:', error);
      alert('Optimizasyon çalıştırılırken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getHealthColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthIcon = (score) => {
    if (score >= 80) return <CheckCircle className="w-5 h-5 text-green-600" />;
    if (score >= 60) return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
    return <AlertTriangle className="w-5 h-5 text-red-600" />;
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Veritabanı Durumu</h1>
        <p className="text-gray-600">Veritabanı optimizasyonu ve performans izleme</p>
      </div>

      {/* Admin Key Input */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <div className="flex items-center space-x-4">
          <Settings className="w-5 h-5 text-yellow-600" />
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Anahtarı (optimizasyon işlemleri için)
            </label>
            <input
              type="password"
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="Admin anahtarını girin"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Database Status Overview */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500">Sağlık Skoru</h3>
              {getHealthIcon(status.health_score)}
            </div>
            <p className={`text-2xl font-bold ${getHealthColor(status.health_score)}`}>
              {status.health_score}/100
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {status.health_score >= 80 ? 'İyi' : status.health_score >= 60 ? 'Orta' : 'Düşük'}
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Veritabanı Boyutu</h3>
            <p className="text-2xl font-bold text-gray-900">
              {status.metrics?.database_size || 'Bilinmiyor'}
            </p>
            <p className="text-xs text-gray-500 mt-1">Toplam boyut</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Aktif Bağlantılar</h3>
            <p className="text-2xl font-bold text-gray-900">
              {status.metrics?.active_connections || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">Mevcut bağlantı sayısı</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Son Optimizasyon</h3>
            <p className="text-2xl font-bold text-gray-900">
              {status.last_optimization
                ? new Date(status.last_optimization).toLocaleDateString('tr-TR')
                : 'Hiç yapılmamış'}
            </p>
            <p className="text-xs text-gray-500 mt-1">Son çalıştırma</p>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow border p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Hızlı İşlemler</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => runOptimization('full')}
            disabled={loading}
            className="flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Database className="w-4 h-4" />
            <span>{loading ? 'Çalıştırılıyor...' : 'Tam Optimizasyon'}</span>
          </button>

          <button
            onClick={() => runOptimization('cleanup')}
            disabled={loading}
            className="flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-4 h-4" />
            <span>{loading ? 'Çalıştırılıyor...' : 'Temizlik'}</span>
          </button>

          <button
            onClick={() => runOptimization('indexes')}
            disabled={loading}
            className="flex items-center justify-center space-x-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Settings className="w-4 h-4" />
            <span>{loading ? 'Çalıştırılıyor...' : 'İndeks Optimizasyonu'}</span>
          </button>
        </div>
      </div>

      {/* Optimization Result */}
      {optimizationResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-green-900">Optimizasyon Sonucu</h3>
            <button
              onClick={() => setOptimizationResult(null)}
              className="text-green-600 hover:text-green-800"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-green-900 mb-2">İşlemler:</h4>
              <ul className="text-sm text-green-700 space-y-1">
                {optimizationResult.operations.map((op, index) => (
                  <li key={index}>✓ {op}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-green-900 mb-2">Süre:</h4>
              <p className="text-sm text-green-700">
                {optimizationResult.duration_seconds?.toFixed(2)} saniye
              </p>
            </div>
          </div>
          {optimizationResult.errors && optimizationResult.errors.length > 0 && (
            <div className="mt-4">
              <h4 className="font-medium text-red-900 mb-2">Hatalar:</h4>
              <ul className="text-sm text-red-700 space-y-1">
                {optimizationResult.errors.map((error, index) => (
                  <li key={index}>✗ {error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Detailed Metrics */}
      {metrics && (
        <div className="space-y-6">
          {/* Table Sizes */}
          {metrics.table_sizes && (
            <div className="bg-white rounded-lg shadow border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Tablo Boyutları</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Tablo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Boyut
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Boyut (MB)
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(metrics.table_sizes).map(([table, info], index) => (
                      <tr key={index} className={info.size_mb > 100 ? 'bg-red-50' : ''}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {table}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {info.size_pretty}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {info.size_mb.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Slow Queries */}
          {metrics.slow_queries && metrics.slow_queries.length > 0 && (
            <div className="bg-white rounded-lg shadow border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Yavaş Sorgular</h3>
              <div className="space-y-3">
                {metrics.slow_queries.map((query, index) => (
                  <div key={index} className="border-l-4 border-orange-400 pl-4 py-2">
                    <div className="flex justify-between items-start">
                      <code className="text-xs bg-gray-100 p-2 rounded flex-1">
                        {query.query}
                      </code>
                      <span className="ml-4 text-sm font-medium text-orange-600">
                        {query.mean_time_ms.toFixed(2)}ms
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {query.calls} çağrı, toplam: {query.total_time_ms.toFixed(2)}ms
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unused Indexes */}
          {metrics.unused_indexes && metrics.unused_indexes.length > 0 && (
            <div className="bg-white rounded-lg shadow border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Kullanılmayan İndeksler</h3>
              <div className="space-y-2">
                {metrics.unused_indexes.map((index, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-yellow-50 rounded">
                    <span className="text-sm font-medium">{index.index}</span>
                    <span className="text-xs text-gray-500">{index.table}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {status.recommendations && status.recommendations.length > 0 && (
            <div className="bg-white rounded-lg shadow border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Öneriler</h3>
              <div className="space-y-2">
                {status.recommendations.map((rec, index) => (
                  <div key={index} className="flex items-start space-x-2 p-3 bg-blue-50 rounded">
                    <TrendingUp className="w-4 h-4 text-blue-600 mt-0.5" />
                    <span className="text-sm text-blue-800">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DatabaseStatusPage;