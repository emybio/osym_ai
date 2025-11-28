import React, { useState, useEffect } from 'react';
import {
  Trophy,
  Star,
  Award,
  Target,
  TrendingUp,
  Users,
  Calendar,
  Zap,
  Crown,
  Medal,
  Lock,
  CheckCircle,
  Gift,
  BarChart3,
  Flame,
  Clock,
  Flag,
  Gem,
  ChevronRight,
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';
import Toast from './Toast';

const GamificationProfilePage = () => {
  const [profile, setProfile] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [achievements, setAchievements] = useState(null);
  const [dailyChallenge, setDailyChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('profile');
  const [leaderboardPeriod, setLeaderboardPeriod] = useState('all_time');
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    fetchGamificationData();
  }, []);

  useEffect(() => {
    if (activeTab === 'leaderboard') {
      fetchLeaderboard();
    }
  }, [leaderboardPeriod, activeTab]);

  const fetchGamificationData = async () => {
    try {
      setLoading(true);

      const [profileRes, achievementsRes, challengeRes] = await Promise.all([
        fetch('/api/v1/gamification/profile/'),
        fetch('/api/v1/gamification/achievements/'),
        fetch('/api/v1/gamification/daily-challenge/')
      ]);

      const [profileData, achievementsData, challengeData] = await Promise.all([
        profileRes.json(),
        achievementsRes.json(),
        challengeRes.json()
      ]);

      setProfile(profileData);
      setAchievements(achievementsData);
      setDailyChallenge(challengeData);

    } catch (error) {
      console.error('Gamification data fetch error:', error);
      showToast('Oyunlaştırma verileri yüklenirken bir hata oluştu', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const response = await fetch(`/api/v1/gamification/leaderboard/?period=${leaderboardPeriod}&limit=20`);
      const data = await response.json();
      setLeaderboard(data.leaderboard || []);
    } catch (error) {
      console.error('Leaderboard fetch error:', error);
      showToast('Lider tablosu yüklenirken bir hata oluştu', 'error');
    }
  };

  const getBadgeColor = (level) => {
    const colors = {
      bronze: 'bg-amber-100 text-amber-800 border-amber-300',
      silver: 'bg-gray-100 text-gray-800 border-gray-300',
      gold: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      platinum: 'bg-slate-100 text-slate-800 border-slate-300',
      diamond: 'bg-blue-50 text-blue-800 border-blue-300'
    };
    return colors[level] || colors.bronze;
  };

  const getLevelIcon = (level) => {
    switch (level) {
      case 'bronze': return <Medal className="w-6 h-6" />;
      case 'silver': return <Award className="w-6 h-6" />;
      case 'gold': return <Trophy className="w-6 h-6" />;
      case 'platinum': return <Crown className="w-6 h-6" />;
      case 'diamond': return <Gem className="w-6 h-6" />;
      default: return <Star className="w-6 h-6" />;
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

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-1 sm:flex-nowrap sm:space-x-1 bg-gray-100 p-1 rounded-lg">
        {['profile', 'achievements', 'leaderboard', 'challenges'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 px-2 sm:px-4 rounded-md text-xs sm:text-sm font-medium transition-colors min-w-0 ${
              activeTab === tab
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <span className="truncate block">{tab === 'profile' && 'Profil'}</span>
            <span className="truncate block">{tab === 'achievements' && 'Başarılar'}</span>
            <span className="truncate block">{tab === 'leaderboard' && 'Liderlik'}</span>
            <span className="truncate block">{tab === 'challenges' && 'Meydan Oku'}</span>
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && profile && (
        <div className="space-y-6">
          {/* User Profile Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
              <div className="flex items-center space-x-3 sm:space-x-4">
                <div className={`w-12 h-12 sm:w-16 sm:h-16 rounded-full flex items-center justify-center ${getBadgeColor(profile.level)}`}>
                  {getLevelIcon(profile.level)}
                </div>
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
                    {profile.level_info.name} Seviye
                  </h2>
                  <p className="text-gray-500">{profile.points} Puan</p>
                </div>
              </div>

              <div className="text-center sm:text-right">
                <div className="text-2xl sm:text-3xl font-bold text-blue-600">
                  #{profile.rank?.rank || '-'}
                </div>
                <p className="text-xs sm:text-sm text-gray-500">
                  {profile.rank?.total_users ? `Toplam ${profile.rank.total_users} kullanıcı` : 'Sıralama yok'}
                </p>
              </div>
            </div>

            {/* Level Progress */}
            <div className="mb-6">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Sıradaki Seviye: {profile.level_progress.next_level?.name || 'Maksimum'}</span>
                <span>{profile.level_progress.progress_percentage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${profile.level_progress.progress_percentage}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{profile.level_progress.current_points} puan</span>
                <span>{profile.level_progress.next_level_points ? `${profile.level_progress.points_needed} puan kaldı` : 'Maksimum seviye'}</span>
              </div>
            </div>

            {/* Motivational Message */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4">
              <p className="text-purple-800 font-medium">{profile.motivational_message}</p>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-3">
            <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <Trophy className="w-6 h-6 sm:w-8 sm:h-8 text-yellow-500" />
                <span className="text-xl sm:text-2xl font-bold text-gray-900">{profile.achievements_count}</span>
              </div>
              <p className="text-sm text-gray-600">Kazanılan Başarı</p>
              <p className="text-xs text-gray-500">
                Toplam {profile.total_possible_achievements} başarıdan
              </p>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <Target className="w-6 h-6 sm:w-8 sm:h-8 text-blue-500" />
                <span className="text-xl sm:text-2xl font-bold text-gray-900">
                  {Math.round((profile.achievements_count / profile.total_possible_achievements) * 100)}%
                </span>
              </div>
              <p className="text-sm text-gray-600">Tamamlanma Oranı</p>
              <p className="text-xs text-gray-500">Başarı ilerlemesi</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <TrendingUp className="w-6 h-6 sm:w-8 sm:h-8 text-green-500" />
                <span className="text-xl sm:text-2xl font-bold text-gray-900">
                  {profile.rank?.top_percentage ? `Top %${profile.rank.top_percentage}` : '-'}
                </span>
              </div>
              <p className="text-sm text-gray-600">Genel Sıralama</p>
              <p className="text-xs text-gray-500">Tüm kullanıcı arası</p>
            </div>
          </div>
        </div>
      )}

      {/* Achievements Tab */}
      {activeTab === 'achievements' && achievements && (
        <div className="space-y-6">
          {/* Achievement Stats */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4">Başarı İstatistikleri</h3>
            <div className="grid gap-3 sm:gap-4 grid-cols-2 sm:grid-cols-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">{achievements.stats.earned_achievements}</div>
                <p className="text-sm text-gray-600">Kazanılan</p>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-400">{achievements.stats.total_achievements - achievements.stats.earned_achievements}</div>
                <p className="text-sm text-gray-600">Kalan</p>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">{achievements.stats.completion_percentage}%</div>
                <p className="text-sm text-gray-600">Tamamlanma</p>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-purple-600">{achievements.stats.total_points}</div>
                <p className="text-sm text-gray-600">Toplam Puan</p>
              </div>
            </div>
          </div>

          {/* Recent Achievements */}
          {achievements.recent_achievements.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Son Kazanılan Başarılar</h3>
              <div className="space-y-3">
                {achievements.recent_achievements.map((achievement, index) => (
                  <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-green-50 border border-green-200">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{achievement.icon}</span>
                      <div>
                        <p className="font-medium text-green-900">{achievement.name}</p>
                        <p className="text-xs text-green-700">
                          {new Date(achievement.earned_at).toLocaleDateString('tr-TR')}
                        </p>
                      </div>
                    </div>
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Achievement Categories */}
          <div className="space-y-3 sm:space-y-4">
            {Object.entries(achievements.categories).map(([category, categoryAchievements]) => (
              <div key={category} className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4 capitalize">
                  {category === 'streak' && 'Seri Başarıları'}
                  {category === 'score' && 'Skor Başarıları'}
                  {category === 'milestone' && 'Kilometre Taşları'}
                  {category === 'time' && 'Zaman Başarıları'}
                  {category === 'performance' && 'Performans Başarıları'}
                  {category === 'special' && 'Özel Başarılar'}
                </h3>
                <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
                  {categoryAchievements.map((achievement, index) => (
                    <div
                      key={index}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        achievement.earned
                          ? 'bg-green-50 border-green-200'
                          : 'bg-gray-50 border-gray-200 opacity-60'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <span className="text-2xl">{achievement.icon}</span>
                        <div>
                          <p className={`font-medium ${achievement.earned ? 'text-green-900' : 'text-gray-600'}`}>
                            {achievement.name}
                          </p>
                          <p className="text-xs text-gray-500">{achievement.points} puan</p>
                        </div>
                      </div>
                      {achievement.earned ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <Lock className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-6">
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            {/* Period Selector */}
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Lider Tablosu</h3>
              <div className="flex space-x-2">
                {['all_time', 'weekly', 'monthly'].map((period) => (
                  <button
                    key={period}
                    onClick={() => setLeaderboardPeriod(period)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      leaderboardPeriod === period
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {period === 'all_time' && 'Tüm Zamanlar'}
                    {period === 'weekly' && 'Haftalık'}
                    {period === 'monthly' && 'Aylık'}
                  </button>
                ))}
              </div>
            </div>

            {/* Leaderboard List */}
            {leaderboard.length > 0 ? (
              <div className="space-y-2">
                {leaderboard.map((user, index) => (
                  <div
                    key={user.rank}
                    className={`flex items-center justify-between p-4 rounded-lg ${
                      user.is_current_user
                        ? 'bg-blue-50 border-2 border-blue-300'
                        : index === 0
                        ? 'bg-yellow-50 border border-yellow-200'
                        : index === 1
                        ? 'bg-gray-50 border border-gray-200'
                        : index === 2
                        ? 'bg-amber-50 border border-amber-200'
                        : 'bg-white border border-gray-100'
                    }`}
                  >
                    <div className="flex items-center space-x-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        index === 0 ? 'bg-yellow-500 text-white' :
                        index === 1 ? 'bg-gray-500 text-white' :
                        index === 2 ? 'bg-amber-600 text-white' :
                        'bg-gray-200 text-gray-700'
                      }`}>
                        {user.rank}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {user.display_name}
                          {user.is_current_user && ' (Siz)'}
                        </p>
                        <p className="text-sm text-gray-500">
                          {user.level} • {user.total_tests} test
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg text-gray-900">{user.points}</p>
                      <p className="text-xs text-gray-500">puan</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p>Henüz liderlik verisi bulunmuyor</p>
                <p className="text-sm">Test çözerek lider tablosunda yerinizi alın!</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Challenges Tab */}
      {activeTab === 'challenges' && (
        <div className="space-y-6">
          {/* Daily Challenge */}
          {dailyChallenge && (
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Günlük Meydan Okuma</h3>
                <Calendar className="w-6 h-6 text-blue-600" />
              </div>

              <div className={`rounded-lg p-4 mb-4 ${
                dailyChallenge.completed
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-blue-50 border border-blue-200'
              }`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 mb-2">{dailyChallenge.title}</h4>
                    <p className="text-gray-600 mb-3">{dailyChallenge.description}</p>
                    <div className="flex items-center space-x-4 text-sm">
                      <div className="flex items-center space-x-1">
                        <Gift className="w-4 h-4 text-yellow-500" />
                        <span className="font-medium">{dailyChallenge.reward_points} puan</span>
                      </div>
                      {dailyChallenge.completed && (
                        <div className="flex items-center space-x-1 text-green-600">
                          <CheckCircle className="w-4 h-4" />
                          <span>Tamamlandı</span>
                        </div>
                      )}
                    </div>
                  </div>
                  {!dailyChallenge.completed && (
                    <button
                      onClick={() => window.location.href = '/quick-test'}
                      className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                    >
                      Başla
                    </button>
                  )}
                </div>
              </div>

              {!dailyChallenge.completed && (
                <div className="text-center text-sm text-gray-500">
                  <Clock className="w-4 h-4 inline mr-1" />
                  Yarın yeni meydan okuma yayınlanacak
                </div>
              )}
            </div>
          )}

          {/* Challenge Tips */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Nasıl Daha Fazla Puan Kazanılır?</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <Zap className="w-5 h-5 text-yellow-500 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">Seri Bozma</p>
                  <p className="text-sm text-gray-600">Her gün test çözerek serini devam ettir ve bonus puanlar kazan</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Target className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">Yüksek Skorlar</p>
                  <p className="text-sm text-gray-600">%90+ skorlar ve mükemmel testler için ekstra puanlar kazan</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Flame className="w-5 h-5 text-orange-500 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">Hızlı Çözüm</p>
                  <p className="text-sm text-gray-600">Normal hızından daha hızlı test tamamla</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <Flag className="w-5 h-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium text-gray-900">Günlük Meydan Okumalar</p>
                  <p className="text-sm text-gray-600">Her gün özel meydan okumaları tamamla</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GamificationProfilePage;