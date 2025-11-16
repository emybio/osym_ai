import React, { useState, useEffect } from 'react';
import { Beaker, BarChart3, Users, Target, TrendingUp, Settings, Play, Square, CheckCircle, AlertTriangle, Clock } from 'lucide-react';

const ABTestingPage = () => {
  const [activeTests, setActiveTests] = useState([]);
  const [selectedTest, setSelectedTest] = useState(null);
  const [testAnalytics, setTestAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [adminKey, setAdminKey] = useState('');
  const [newTest, setNewTest] = useState({
    name: '',
    type: 'UI_VARIANT',
    control: {},
    variant_a: {},
    variant_b: {}
  });
  const [creatingTest, setCreatingTest] = useState(false);

  useEffect(() => {
    loadActiveTests();
  }, []);

  const loadActiveTests = async () => {
    try {
      const response = await fetch('/api/quiz/ab-tests/active/');
      const data = await response.json();
      setActiveTests(data.active_tests || []);
    } catch (error) {
      console.error('Error loading active tests:', error);
    }
  };

  const loadTestAnalytics = async (testName) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/quiz/ab-tests/analytics/?test_name=${testName}&period=7d`);
      const data = await response.json();
      setTestAnalytics(data);
    } catch (error) {
      console.error('Error loading test analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const createTest = async () => {
    if (!adminKey || !newTest.name) {
      alert('Lütfen admin anahtarını ve test adını girin');
      return;
    }

    setCreatingTest(true);
    try {
      const response = await fetch('/api/quiz/ab-tests/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          admin_key: adminKey,
          test_name: newTest.name,
          test_config: {
            type: newTest.type,
            control: newTest.control,
            variant_a: newTest.variant_a,
            variant_b: newTest.variant_b
          }
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Test başarıyla oluşturuldu: ${data.test_name}`);
        setNewTest({
          name: '',
          type: 'UI_VARIANT',
          control: {},
          variant_a: {},
          variant_b: {}
        });
        loadActiveTests();
      } else {
        alert('Hata: ' + data.error);
      }
    } catch (error) {
      console.error('Error creating test:', error);
      alert('Test oluşturulurken hata oluştu');
    } finally {
      setCreatingTest(false);
    }
  };

  const endTest = async (testName, implementWinner = false) => {
    if (!adminKey) {
      alert('Lütfen admin anahtarını girin');
      return;
    }

    if (!confirm(`'${testName}' testini bitirmek istediğinizden emin misiniz?${implementWinner ? ' Kazanan varyant uygulanacak.' : ''}`)) {
      return;
    }

    try {
      const response = await fetch('/api/quiz/ab-tests/end/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          admin_key: adminKey,
          test_name: testName,
          implement_winner: implementWinner
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Test başarıyla bitirildi: ${testName}`);
        if (data.winner_implemented) {
          alert(`Kazanan varyant uygulandı: ${data.implementation_details.winning_variant}`);
        }
        loadActiveTests();
        if (selectedTest === testName) {
          setSelectedTest(null);
          setTestAnalytics(null);
        }
      } else {
        alert('Hata: ' + data.error);
      }
    } catch (error) {
      console.error('Error ending test:', error);
      alert('Test bitirilirken hata oluştu');
    }
  };

  const getVariantIcon = (variant) => {
    switch (variant) {
      case 'control':
        return <Square className="w-4 h-4 text-gray-600" />;
      case 'variant_a':
        return <Target className="w-4 h-4 text-blue-600" />;
      case 'variant_b':
        return <Beaker className="w-4 h-4 text-green-600" />;
      default:
        return <Settings className="w-4 h-4 text-gray-400" />;
    }
  };

  const getVariantName = (variant) => {
    switch (variant) {
      case 'control':
        return 'Kontrol';
      case 'variant_a':
        return 'Varyant A';
      case 'variant_b':
        return 'Varyant B';
      default:
        return variant;
    }
  };

  const formatPercentage = (num) => {
    return num ? (num * 100).toFixed(1) + '%' : '0%';
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">A/B Testing Paneli</h1>
        <p className="text-gray-600">UI varyantları ve özellikleri için A/B test yönetimi</p>
      </div>

      {/* Admin Key Input */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <div className="flex items-center space-x-4">
          <Settings className="w-5 h-5 text-yellow-600" />
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin Anahtarı (test yönetimi için)
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

      {/* Create New Test */}
      <div className="bg-white rounded-lg shadow border p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Yeni Test Oluştur</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Test Adı"
            value={newTest.name}
            onChange={(e) => setNewTest({...newTest, name: e.target.value})}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
          <select
            value={newTest.type}
            onChange={(e) => setNewTest({...newTest, type: e.target.value})}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="UI_VARIANT">UI Varyant</option>
            <option value="FEATURE_FLAG">Feature Flag</option>
            <option value="CONTENT_VARIANT">Content Varyant</option>
            <option value="PRICING_TEST">Pricing Test</option>
          </select>
          <button
            onClick={createTest}
            disabled={creatingTest}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creatingTest ? 'Oluşturuluyor...' : 'Test Oluştur'}
          </button>
        </div>
      </div>

      {/* Active Tests */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Test List */}
        <div className="bg-white rounded-lg shadow border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Aktif Testler ({activeTests.length})</h2>
          <div className="space-y-3">
            {activeTests.map((test, index) => (
              <div
                key={index}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedTest === test.name
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => {
                  setSelectedTest(test.name);
                  loadTestAnalytics(test.name);
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">{test.name}</h3>
                    <p className="text-sm text-gray-500">{test.type}</p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        endTest(test.name, true);
                      }}
                      className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                    >
                      Kazananı Uygula
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        endTest(test.name, false);
                      }}
                      className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                    >
                      Bitir
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {activeTests.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <Beaker className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>Aktif test bulunmuyor</p>
              </div>
            )}
          </div>
        </div>

        {/* Test Analytics */}
        <div className="bg-white rounded-lg shadow border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Test Analitikleri {selectedTest && `- ${selectedTest}`}
          </h2>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : testAnalytics ? (
            <div className="space-y-6">
              {/* Summary */}
              {testAnalytics.summary && (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-medium text-gray-900 mb-3">Özet</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Toplam Event:</p>
                      <p className="font-medium">{testAnalytics.summary.total_events || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Kazanan:</p>
                      <p className="font-medium">
                        {testAnalytics.summary.winner || 'Belirlenmedi'}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">İyileştirme:</p>
                      <p className="font-medium text-green-600">
                        +{testAnalytics.summary.improvement || 0}%
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-500">Güven:</p>
                      <p className="font-medium">
                        {testAnalytics.summary.statistical_significance ? (
                          <span className="text-green-600">Anlamlı</span>
                        ) : (
                          <span className="text-yellow-600">Yetersiz</span>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Segment Performance */}
              {testAnalytics.segments && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Segment Performansı</h3>
                  <div className="space-y-3">
                    {Object.entries(testAnalytics.segments).map(([segment, data]) => (
                      <div key={segment} className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            {getVariantIcon(segment)}
                            <span className="font-medium">{getVariantName(segment)}</span>
                          </div>
                          <span className="text-sm text-gray-500">{data.events} events</span>
                        </div>
                        {data.metrics && Object.entries(data.metrics).length > 0 && (
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            {Object.entries(data.metrics).map(([metric, value]) => (
                              <div key={metric}>
                                <span className="text-gray-500">{metric}:</span>
                                <span className="font-medium ml-1">
                                  {typeof value === 'number' ? formatPercentage(value) : value}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {testAnalytics.recommendations && testAnalytics.recommendations.length > 0 && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Öneriler</h3>
                  <div className="space-y-2">
                    {testAnalytics.recommendations.map((rec, index) => (
                      <div key={index} className="flex items-start space-x-2 p-2 bg-blue-50 rounded">
                        <TrendingUp className="w-4 h-4 text-blue-600 mt-0.5" />
                        <span className="text-sm text-blue-800">{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>Analitik için test seçin</p>
            </div>
          )}
        </div>
      </div>

      {/* Pre-defined Tests Info */}
      <div className="bg-white rounded-lg shadow border p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Ön Tanımlı Testler</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Quick Test Button</h3>
            <p className="text-sm text-gray-600 mb-2">Buton renkleri ve metinleri test eder</p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center space-x-1">
                <Square className="w-3 h-3 text-gray-500" />
                <span>Kontrol: Mavi buton</span>
              </div>
              <div className="flex items-center space-x-1">
                <Target className="w-3 h-3 text-blue-500" />
                <span>Varyant A: Yeşil buton</span>
              </div>
              <div className="flex items-center space-x-1">
                <Beaker className="w-3 h-3 text-green-500" />
                <span>Varyant B: Sarı buton</span>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Dashboard Layout</h3>
            <p className="text-sm text-gray-600 mb-2">Farklı düzenleri ve gösterim şekillerini test eder</p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center space-x-1">
                <Square className="w-3 h-3 text-gray-500" />
                <span>Grid düzen</span>
              </div>
              <div className="flex items-center space-x-1">
                <Target className="w-3 h-3 text-blue-500" />
                <span>Liste düzen</span>
              </div>
              <div className="flex items-center space-x-1">
                <Beaker className="w-3 h-3 text-green-500" />
                <span>Carousel düzen</span>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Gamification</h3>
            <p className="text-sm text-gray-600 mb-2">Oyunlaştırma özelliklerini test eder</p>
            <div className="space-y-1 text-xs">
              <div className="flex items-center space-x-1">
                <Square className="w-3 h-3 text-gray-500" />
                <span>Tüm özellikler açık</span>
              </div>
              <div className="flex items-center space-x-1">
                <Target className="w-3 h-3 text-blue-500" />
                <span>Sadece puanlar</span>
              </div>
              <div className="flex items-center space-x-1">
                <Beaker className="w-3 h-3 text-green-500" />
                <span>Sadece seriler</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ABTestingPage;