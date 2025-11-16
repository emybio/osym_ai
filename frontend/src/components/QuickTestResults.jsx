import React, { useState } from 'react';
import { Trophy, Target, BookOpen, TrendingUp, CheckCircle, XCircle, Star, ChevronRight } from 'lucide-react';
import AnimatedTransition from './AnimatedTransition';

const QuickTestResults = ({ resultData, onStartNewTest, onCreateAccount }) => {
  const [showRegisterForm, setShowRegisterForm] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  });
  const [isRegistering, setIsRegistering] = useState(false);

  const percentage = resultData.percentage || 0;
  const correctCount = resultData.correct_count || 0;
  const totalCount = resultData.total_questions || 0;
  const subjectBreakdown = resultData.subject_breakdown || {};

  // Performance message
  const getPerformanceMessage = () => {
    if (percentage >= 85) return { text: "Mükemmel! 🎉", color: "text-green-600" };
    if (percentage >= 70) return { text: "Harika! 👏", color: "text-blue-600" };
    if (percentage >= 55) return { text: "İyi gidiyorsun! 💪", color: "text-yellow-600" };
    return { text: "Devam et! 📈", color: "text-gray-600" };
  };

  const performance = getPerformanceMessage();

  // Handle registration
  const handleRegister = async (e) => {
    e.preventDefault();

    if (!formData.username || !formData.email || !formData.password) {
      return; // Form HTML5 validation ile handle ediliyor
    }

    setIsRegistering(true);

    try {
      const response = await fetch('/api/quiz/quicktest/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          temp_result_uuid: resultData.uuid,
          username: formData.username,
          email: formData.email,
          password: formData.password
        }),
        credentials: 'same-origin'
      });

      const data = await response.json();

      if (response.ok) {
        alert('Hesabınız başarıyla oluşturuldu! Sonuçlar profilinize eklendi.');
        onCreateAccount(data);
      } else {
        alert(data.error || 'Kayıt işlemi başarısız');
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert('Kayıt işlemi başarısız. Lütfen tekrar deneyin.');
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <AnimatedTransition>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900">Test Sonuçları</h1>
              <p className="text-gray-600 mt-1">{resultData.session_info?.exam_type} {resultData.session_info?.branch}</p>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Ana Sonuç Kartı */}
          <div className="bg-white rounded-2xl border border-gray-200 p-8 mb-8">
            <div className="text-center">
              {/* Skor Dairesi */}
              <div className="relative inline-flex items-center justify-center mb-6">
                <div className="w-32 h-32 rounded-full border-8 border-gray-200"></div>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-3xl font-bold ${performance.color}`}>
                    {percentage.toFixed(1)}%
                  </span>
                  <span className="text-sm text-gray-500">Başarı</span>
                </div>
              </div>

              {/* Başarı Mesajı */}
              <h2 className={`text-xl font-semibold mb-2 ${performance.color}`}>
                {performance.text}
              </h2>

              {/* Detaylar */}
              <div className="flex items-center justify-center gap-8 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span>{correctCount} Doğru</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span>{totalCount - correctCount} Yanlış</span>
                </div>
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-blue-600" />
                  <span>{totalCount} Soru</span>
                </div>
              </div>
            </div>
          </div>

          {/* Konu Bazında Sonuçlar */}
          {Object.keys(subjectBreakdown).length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Konu Bazında Performans
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                {Object.entries(subjectBreakdown).map(([subject, data]) => {
                  const subjectPercentage = (data.correct / data.total) * 100;
                  return (
                    <div key={subject} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{subject}</h4>
                        <span className="text-sm text-gray-600">
                          {data.correct}/{data.total}
                        </span>
                      </div>
                      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-600 transition-all duration-300"
                          style={{ width: `${subjectPercentage}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        %{subjectPercentage.toFixed(1)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Call-to-Action */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-8 mb-8 text-white">
            <div className="text-center">
              <Star className="w-12 h-12 mx-auto mb-4" />
              <h3 className="text-xl font-bold mb-2">
                Sonuçlarını Kaydet ve Gelişimini Takip Et!
              </h3>
              <p className="mb-6 opacity-90">
                Ücretsiz hesap oluşturarak tüm test sonuçlarını bir arada görüntüleyebilir ve ilerlemeni takip edebilirsin.
              </p>

              {!showRegisterForm ? (
                <div className="flex items-center justify-center gap-4">
                  <button
                    onClick={() => setShowRegisterForm(true)}
                    className="px-6 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition-all"
                  >
                    Ücretsiz Hesap Oluştur
                  </button>
                  <button
                    onClick={onStartNewTest}
                    className="px-6 py-3 bg-white/20 text-white rounded-lg font-semibold hover:bg-white/30 transition-all border border-white/30"
                  >
                    Yeni Test Çöz
                  </button>
                </div>
              ) : (
                /* Registration Form */
                <form onSubmit={handleRegister} className="max-w-md mx-auto">
                  <div className="grid md:grid-cols-3 gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="Kullanıcı Adı"
                      value={formData.username}
                      onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                      className="px-4 py-2 rounded-lg text-gray-900 placeholder-gray-500 bg-white/90"
                      required
                    />
                    <input
                      type="email"
                      placeholder="E-posta"
                      value={formData.email}
                      onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                      className="px-4 py-2 rounded-lg text-gray-900 placeholder-gray-500 bg-white/90"
                      required
                    />
                    <input
                      type="password"
                      placeholder="Şifre"
                      value={formData.password}
                      onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                      className="px-4 py-2 rounded-lg text-gray-900 placeholder-gray-500 bg-white/90"
                      minLength="8"
                      required
                    />
                  </div>
                  <div className="flex items-center justify-center gap-4">
                    <button
                      type="submit"
                      disabled={isRegistering}
                      className="px-6 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isRegistering ? 'Kaydediliyor...' : 'Hesabı Oluştur'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowRegisterForm(false)}
                      className="px-6 py-3 bg-transparent text-white rounded-lg font-semibold hover:bg-white/20 transition-all border border-white/30"
                    >
                      İptal
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          {!showRegisterForm && (
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={onStartNewTest}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all flex items-center gap-2"
              >
                <TrendingUp className="w-4 h-4" />
                Yeni Test Başlat
              </button>
              <button
                onClick={() => window.history.back()}
                className="px-6 py-3 bg-white border border-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-all"
              >
                Ana Sayfaya Dön
              </button>
            </div>
          )}
        </div>
      </div>
    </AnimatedTransition>
  );
};

export default QuickTestResults;