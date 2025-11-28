import React, { useState, useEffect } from 'react';
import { useProtectedRoute } from '../hooks/useProtectedRoute';
import { getApiUrl } from '../api/config';
import Toast from './Toast';

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#F97316', '#06B6D4', '#84CC16'];

// Simple Bar Chart Component
const SimpleBarChart = ({ data, title, dataKey = 'value', labelKey = 'name' }) => (
    <div className="bg-white p-4 sm:p-6 rounded-lg shadow border">
        <h3 className="text-lg sm:text-xl font-semibold mb-4">{title}</h3>
        <div className="space-y-3">
            {data?.map((item, index) => (
                <div key={index} className="flex items-center space-x-3 sm:space-x-4">
                    <div className="w-24 sm:w-32 flex-shrink-0 text-xs sm:text-sm font-medium truncate">{item[labelKey] || item.name || item.subject || item.level}</div>
                    <div className="flex-1 min-w-0">
                        <div className="bg-gray-200 rounded-full h-5 sm:h-6 relative">
                            <div
                                className="bg-gradient-to-r from-blue-400 to-blue-600 h-5 sm:h-6 rounded-full flex items-center justify-center text-white text-xs font-medium px-1"
                                style={{ width: `${Math.min((item[dataKey] || item.value || item.count) / Math.max(...data.map(d => d[dataKey] || d.value || d.count)) * 100, 100)}%` }}
                            >
                                <span className="truncate">{item[dataKey] || item.value || item.count}</span>
                            </div>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    </div>
);

// Simple Pie Chart Component
const SimplePieChart = ({ data, title }) => {
    const total = data?.reduce((sum, item) => sum + (item.value || item.count), 0) || 0;

    return (
        <div className="bg-white p-4 sm:p-6 rounded-lg shadow border">
            <h3 className="text-lg sm:text-xl font-semibold mb-4">{title}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {data?.map((item, index) => (
                    <div key={index} className="flex items-center space-x-2 sm:space-x-3">
                        <div
                            className="w-3 h-3 sm:w-4 sm:h-4 rounded-full flex-shrink-0"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        ></div>
                        <div className="text-xs sm:text-sm min-w-0 flex-1">
                            <div className="font-medium truncate">{item.name || item.subject || item.exam_type}</div>
                            <div className="text-gray-500">
                                {item.value || item.count} ({total > 0 ? ((item.value || item.count) / total * 100).toFixed(1) : 0}%)
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

// Simple Line Chart Component
const SimpleLineChart = ({ data, title, lines = [] }) => (
    <div className="bg-white p-4 rounded-lg shadow border">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="space-y-4">
            {lines.map((line, lineIndex) => (
                <div key={lineIndex}>
                    <div className="text-sm font-medium mb-2" style={{ color: COLORS[lineIndex % COLORS.length] }}>
                        {line.name}
                    </div>
                    <div className="flex items-end space-x-1 h-20">
                        {data?.map((item, index) => {
                            const maxValue = Math.max(...data.map(d => d[line.key]));
                            const height = maxValue > 0 ? (item[line.key] / maxValue * 100) : 0;
                            return (
                                <div
                                    key={index}
                                    className="flex-1 bg-blue-500 rounded-t"
                                    style={{
                                        height: `${height}%`,
                                        backgroundColor: COLORS[lineIndex % COLORS.length],
                                        opacity: 0.8
                                    }}
                                    title={`${item.date}: ${item[line.key]}`}
                                ></div>
                            );
                        })}
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                        {data?.map((item, index) => (
                            <div key={index} className="flex-1 text-center">
                                {new Date(item.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' })}
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    </div>
);

// Metrics Card Component
const MetricsCard = ({ title, value, subtitle, color = 'blue' }) => {
    const colorClasses = {
        blue: 'bg-blue-50 border-blue-200 text-blue-600',
        green: 'bg-green-50 border-green-200 text-green-600',
        purple: 'bg-purple-50 border-purple-200 text-purple-600',
        orange: 'bg-orange-50 border-orange-200 text-orange-600',
        pink: 'bg-pink-50 border-pink-200 text-pink-600',
        teal: 'bg-teal-50 border-teal-200 text-teal-600',
        cyan: 'bg-cyan-50 border-cyan-200 text-cyan-600',
        lime: 'bg-lime-50 border-lime-200 text-lime-600',
        emerald: 'bg-emerald-50 border-emerald-200 text-emerald-600',
        violet: 'bg-violet-50 border-violet-200 text-violet-600',
        sky: 'bg-sky-50 border-sky-200 text-sky-600',
        fuchsia: 'bg-fuchsia-50 border-fuchsia-200 text-fuchsia-600',
        rose: 'bg-rose-50 border-rose-200 text-rose-600',
        amber: 'bg-amber-50 border-amber-200 text-amber-600',
        indigo: 'bg-indigo-50 border-indigo-200 text-indigo-600'
    };

    return (
        <div className={`p-3 sm:p-4 rounded-lg border ${colorClasses[color]}`}>
            <h3 className="text-xs sm:text-sm font-medium">{title}</h3>
            <p className="text-xl sm:text-2xl font-bold">{value}</p>
            <p className="text-xs">{subtitle}</p>
        </div>
    );
};

const AnalyticsPage = () => {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [period, setPeriod] = useState('week');
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState({});
    const [toast, setToast] = useState(null);

    const { user } = useProtectedRoute();

    const showToast = (message, type = 'info') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    useEffect(() => {
        loadAnalyticsData();
    }, [activeTab, period]);

    const loadAnalyticsData = async () => {
        setLoading(true);
        try {
            let endpoint = `/quiz/analytics/${activeTab}/`;
            if (period) {
                endpoint += `?period=${period}`;
            }

            const response = await fetch(getApiUrl(endpoint));
            const result = await response.json();

            if (response.ok) {
                setData(result);
            } else {
                console.error(result.error || 'Analitik veriler yüklenemedi');
                showToast(result.error || 'Analitik veriler yüklenemedi', 'error');
            }
        } catch (error) {
            console.error('Analytics loading error:', error);
            showToast('Analitik verileri yüklenirken hata oluştu', 'error');
        } finally {
            setLoading(false);
        }
    };

    const formatNumber = (num) => {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    };

    const formatPercentage = (num) => {
        return (num * 100).toFixed(1) + '%';
    };

    const DashboardTab = () => (
        <div className="space-y-4 sm:space-y-6">
            {/* Ana Metrikler */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <MetricsCard
                    title="Toplam Kullanıcı"
                    value={formatNumber(data.total_users || 0)}
                    subtitle={`${data.user_growth_rate ? '+' + formatPercentage(data.user_growth_rate) : '0%'} bu dönem`}
                    color="blue"
                />
                <MetricsCard
                    title="Aktif Kullanıcı"
                    value={formatNumber(data.active_users || 0)}
                    subtitle={`${data.active_rate ? formatPercentage(data.active_rate) : '0%'} aktivite oranı`}
                    color="green"
                />
                <MetricsCard
                    title="Tamamlanan Test"
                    value={formatNumber(data.completed_tests || 0)}
                    subtitle={`${data.test_completion_rate ? formatPercentage(data.test_completion_rate) : '0%'} tamamlanma oranı`}
                    color="purple"
                />
                <MetricsCard
                    title="Ortalama Skor"
                    value={data.average_score ? data.average_score.toFixed(1) + '%' : '0%'}
                    subtitle={`${data.score_improvement ? (data.score_improvement > 0 ? '+' : '') + formatPercentage(data.score_improvement) : '0%'} gelişim`}
                    color="orange"
                />
            </div>

            {/* Grafikler */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                {/* Kullanıcı Trendi */}
                <SimpleLineChart
                    data={data.user_trend || []}
                    title="Kullanıcı Trendi"
                    lines={[
                        { name: 'Yeni Kullanıcı', key: 'new_users' },
                        { name: 'Geri Dönen', key: 'returning_users' }
                    ]}
                />

                {/* Test Dağılımı */}
                <SimplePieChart
                    data={data.test_distribution || []}
                    title="Test Dağılımı"
                />
            </div>

            {/* Performans Metrikleri */}
            <div className="bg-white p-4 sm:p-6 rounded-lg shadow border">
                <h3 className="text-lg sm:text-xl font-semibold mb-4">Performans Metrikleri</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                    <div>
                        <p className="text-sm text-gray-500">Günlük Ortalama Test</p>
                        <p className="text-lg font-semibold">{data.daily_avg_tests?.toFixed(1) || '0'}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">En Popüler Konu</p>
                        <p className="text-lg font-semibold">{data.most_popular_subject || '-'}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">En Yüksek Skor</p>
                        <p className="text-lg font-semibold">{data.highest_score?.toFixed(1) + '%' || '0%'}</p>
                    </div>
                    <div>
                        <p className="text-sm text-gray-500">Ortalama Süre</p>
                        <p className="text-lg font-semibold">{data.average_duration?.toFixed(1) + 'dk' || '0dk'}</p>
                    </div>
                </div>
            </div>
        </div>
    );

    const UserTab = () => (
        <div className="space-y-6">
            {/* Kullanıcı İstatistikleri */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricsCard
                    title="Toplam Test"
                    value={data.total_tests || 0}
                    subtitle="Tamamlanan test sayısı"
                    color="indigo"
                />
                <MetricsCard
                    title="Ortalama Skor"
                    value={data.average_score?.toFixed(1) + '%' || '0%'}
                    subtitle="Tüm zamanlar ortalaması"
                    color="pink"
                />
                <MetricsCard
                    title="En İyi Skor"
                    value={data.best_score?.toFixed(1) + '%' || '0%'}
                    subtitle="Kişisel rekor"
                    color="teal"
                />
            </div>

            {/* Performans Grafiği */}
            <SimpleLineChart
                data={data.performance_trend || []}
                title="Performans Trendi"
                lines={[
                    { name: 'Skor', key: 'score' },
                    { name: 'Doğruluk', key: 'accuracy' }
                ]}
            />

            {/* Konu Bazlı Performans */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SimpleBarChart
                    data={data.subject_performance || []}
                    title="Ustalık Seviyesi"
                    dataKey="mastery"
                    labelKey="subject"
                />
                <SimpleBarChart
                    data={data.subject_performance || []}
                    title="İyileşim"
                    dataKey="improvement"
                    labelKey="subject"
                />
            </div>
        </div>
    );

    const ContentTab = () => (
        <div className="space-y-6">
            {/* İçerik Metrikleri */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <MetricsCard
                    title="Toplam Soru"
                    value={formatNumber(data.total_questions || 0)}
                    subtitle={`${data.question_growth ? '+' + formatPercentage(data.question_growth) : '0%'} artış`}
                    color="cyan"
                />
                <MetricsCard
                    title="Ortalama Zorluk"
                    value={data.average_difficulty?.toFixed(1) || '0'}
                    subtitle="1-5 arası ölçek"
                    color="lime"
                />
                <MetricsCard
                    title="En Popüler Konu"
                    value={data.most_popular_topic || '-'}
                    subtitle={`${data.topic_attempts || 0} deneme`}
                    color="rose"
                />
                <MetricsCard
                    title="Başarı Oranı"
                    value={formatPercentage(data.success_rate || 0)}
                    subtitle="Genel ortalama"
                    color="amber"
                />
            </div>

            {/* Konu Dağılımı */}
            <SimplePieChart
                data={data.topic_distribution || []}
                title="Konu Dağılımı"
            />

            {/* Zorluk Dağılımı */}
            <SimpleBarChart
                data={data.difficulty_distribution || []}
                title="Zorluk Seviyesi Dağılımı"
                dataKey="count"
                labelKey="level"
            />
        </div>
    );

    const EngagementTab = () => (
        <div className="space-y-6">
            {/* Etkileşim Metrikleri */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <MetricsCard
                    title="Oturum Süresi"
                    value={data.avg_session_duration?.toFixed(1) + 'dk' || '0dk'}
                    subtitle="Ortalama süre"
                    color="emerald"
                />
                <MetricsCard
                    title="Return Rate"
                    value={formatPercentage(data.return_rate || 0)}
                    subtitle="Geri dönüş oranı"
                    color="violet"
                />
                <MetricsCard
                    title="Etkileşim Skoru"
                    value={data.engagement_score?.toFixed(1) || '0'}
                    subtitle="100 üzerinden"
                    color="sky"
                />
                <MetricsCard
                    title="Stickiness"
                    value={data.stickiness_factor?.toFixed(1) || '0'}
                    subtitle="Yapışkanlık faktörü"
                    color="fuchsia"
                />
            </div>

            {/* Haftalık Etkileşim */}
            <SimpleLineChart
                data={data.weekly_engagement || []}
                title="Haftalık Etkileşim"
                lines={[
                    { name: 'Aktif Kullanıcı', key: 'active_users' },
                    { name: 'Test Sayısı', key: 'test_count' },
                    { name: 'Geçirilen Zaman', key: 'time_spent' }
                ]}
            />
        </div>
    );

    const ConversionTab = () => (
        <div className="space-y-6">
            {/* Conversion Metrikleri */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <MetricsCard
                    title="Ziyaretçi"
                    value={formatNumber(data.visitors || 0)}
                    subtitle="Toplam ziyaretçi"
                    color="blue"
                />
                <MetricsCard
                    title="Test Başlatan"
                    value={formatNumber(data.test_starters || 0)}
                    subtitle={`${formatPercentage((data.test_starters || 0) / (data.visitors || 1))} dönüşüm`}
                    color="green"
                />
                <MetricsCard
                    title="Test Bitiren"
                    value={formatNumber(data.test_finishers || 0)}
                    subtitle={`${formatPercentage((data.test_finishers || 0) / (data.test_starters || 1))} tamamlama`}
                    color="yellow"
                />
                <MetricsCard
                    title="Kayıt Olan"
                    value={formatNumber(data.signups || 0)}
                    subtitle={`${formatPercentage((data.signups || 0) / (data.visitors || 1))} kayıt oranı`}
                    color="purple"
                />
                <MetricsCard
                    title="Return User"
                    value={formatNumber(data.return_users || 0)}
                    subtitle={`${formatPercentage((data.return_users || 0) / (data.signups || 1))} geri dönüş`}
                    color="pink"
                />
            </div>

            {/* Conversion Funnel */}
            <div className="bg-white p-4 rounded-lg shadow border">
                <h3 className="text-lg font-semibold mb-4">Conversion Funnel</h3>
                <div className="space-y-4">
                    {data.funnel_steps?.map((step, index) => (
                        <div key={index} className="flex items-center space-x-4">
                            <div className="w-32 text-sm font-medium">{step.name}</div>
                            <div className="flex-1">
                                <div className="bg-gray-200 rounded-full h-8 relative">
                                    <div
                                        className="bg-gradient-to-r from-blue-400 to-blue-600 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium"
                                        style={{ width: `${step.percentage * 100}%` }}
                                    >
                                        {formatNumber(step.count)} ({formatPercentage(step.percentage)})
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Conversion Trend */}
            <SimpleLineChart
                data={data.conversion_trend || []}
                title="Conversion Trend"
                lines={[
                    { name: 'Ziyaret → Test Başlatma', key: 'visit_to_start' },
                    { name: 'Başlat → Bitir', key: 'start_to_finish' },
                    { name: 'Bitir → Kayıt', key: 'finish_to_signup' }
                ]}
            />
        </div>
    );

    const tabs = [
        { id: 'dashboard', label: 'Dashboard', component: DashboardTab },
        { id: 'user', label: 'Kullanıcı Analizi', component: UserTab },
        { id: 'content', label: 'İçerik Analizi', component: ContentTab },
        { id: 'engagement', label: 'Etkileşim', component: EngagementTab },
        { id: 'conversion_funnel', label: 'Conversion Funnel', component: ConversionTab }
    ];

    const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || DashboardTab;

    return (
        <div className="max-w-7xl mx-auto p-6">
            {/* Toast */}
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}

            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Analytics Dashboard</h1>
                <p className="text-gray-600">Kapsamlı analiz ve içgörüler</p>
            </div>

            {/* Controls */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 space-y-4 sm:space-y-0">
                {/* Period Selector */}
                <div className="flex items-center space-x-2">
                    <label className="text-sm font-medium text-gray-700">Periyot:</label>
                    <select
                        value={period}
                        onChange={(e) => setPeriod(e.target.value)}
                        className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                        <option value="day">Bugün</option>
                        <option value="week">Bu Hafta</option>
                        <option value="month">Bu Ay</option>
                        <option value="year">Bu Yıl</option>
                    </select>
                </div>

                {/* Export Button */}
                <button
                    onClick={() => {
                        const dataStr = JSON.stringify(data, null, 2);
                        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);

                        const exportFileDefaultName = `analytics_${activeTab}_${period}.json`;

                        const linkElement = document.createElement('a');
                        linkElement.setAttribute('href', dataUri);
                        linkElement.setAttribute('download', exportFileDefaultName);
                        linkElement.click();
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                    Verileri İndir
                </button>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <ActiveComponent />
            )}
        </div>
    );
};

export default AnalyticsPage;