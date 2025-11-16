import React, { useState, useEffect } from 'react';
import { Clock, Target, BookOpen, Users, ChevronRight, ArrowLeft, Play, Wifi, WifiOff } from 'lucide-react';
import AnimatedTransition from './AnimatedTransition';
import Toast, { useToast } from './Toast';
import { usePWA } from '../hooks/usePWA';
import offlineManager from '../utils/offlineApi';

const QuickTestPage = ({ onStartQuickTest, onBack }) => {
  const [selectedExam, setSelectedExam] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('');
  const [questionCount, setQuestionCount] = useState(12);
  const [duration, setDuration] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasOfflineQuestions, setHasOfflineQuestions] = useState(false);

  // Hooks
  const { isOnline, getCachedData } = usePWA();
  const toast = useToast();

  // Check for offline questions
  useEffect(() => {
    const checkOfflineQuestions = () => {
      for (const branch of ['SAY', 'EA', 'SOZ']) {
        const cachedQuestions = offlineManager.getCachedQuestions(branch);
        if (cachedQuestions && cachedQuestions.length > 0) {
          setHasOfflineQuestions(true);
          return;
        }
      }
      setHasOfflineQuestions(false);
    };

    checkOfflineQuestions();
    window.addEventListener('storage', checkOfflineQuestions);
    return () => window.removeEventListener('storage', checkOfflineQuestions);
  }, []);

  
  const examTypes = [
    {
      id: 'TYT',
      name: 'Temel Yeterlilik Testi',
      description: '2 oturumlu temel sınav',
      icon: <Target className="w-5 h-5" />,
      color: 'bg-blue-50 text-blue-600 border-blue-200'
    },
    {
      id: 'AYT',
      name: 'Alan Yeterlilik Testi',
      description: 'Alan bazında detaylı sınav',
      icon: <BookOpen className="w-5 h-5" />,
      color: 'bg-purple-50 text-purple-600 border-purple-200'
    }
  ];

  const branches = [
    { id: 'SAY', name: 'Sayısal', description: 'Matematik, Fen Bilimleri' },
    { id: 'EA', name: 'Eşit Ağırlık', description: 'Matematik, Türkçe, Sosyal Bilimler' },
    { id: 'SOZ', name: 'Sözel', description: 'Türkçe, Sosyal Bilimler' }
  ];

  const questionOptions = [8, 10, 12, 15, 20];
  const durationOptions = [5, 10, 15, 20, 30];

  const handleStart = async () => {
    if (!selectedExam || !selectedBranch) {
      if (toast) {
        toast.warning('Lütfen sınav türü ve branş seçin');
      }
      return;
    }
    setIsSubmitting(true);

    try {
      await onStartQuickTest({
        exam_type: selectedExam,
        branch: selectedBranch,
        question_count: questionCount,
        duration_minutes: duration
      });

      // Başarılı mesajı
      if (toast) {
        toast.info(`${selectedExam} ${branches.find(b => b.id === selectedBranch)?.name} testiniz hazırlanıyor...`);
      }

    } catch (err) {
      const errorMessage = err.message || 'Test başlatılamadı. Lütfen tekrar deneyin.';
      if (toast) {
        toast.error(errorMessage, 5000);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = selectedExam && selectedBranch;

  return (
    <AnimatedTransition>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={onBack}
                  className="p-2 hover:bg-gray-100 rounded-lg border border-gray-200"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Hızlı Test</h1>
                  <p className="text-gray-600">Kayıtsız test çözerek seviyeni ölç</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Users className="w-4 h-4" />
                <span>3,452 Bugün Çözdü</span>
              </div>
            </div>
          </div>
        </div>

        {/* Offline Status Indicator */}
        {!isOnline && (
          <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mx-4 mt-4">
            <div className="flex items-center">
              <WifiOff className="w-5 h-5 text-amber-600 mr-3" />
              <div>
                <p className="font-medium text-amber-800">Çevrimdışı moddasınız</p>
                <p className="text-sm text-amber-700">
                  {hasOfflineQuestions
                    ? 'Önbelleğe alınmış sorularla test çözebilirsiniz. Sonuçlar bağlantı geldiğinde gönderilecektir.'
                    : 'İnternet bağlantısı gereklidir. Önbelleğe alınmış soru bulunmuyor.'
                  }
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Online Status with Cache Info */}
        {isOnline && hasOfflineQuestions && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4 mx-4 mt-4">
            <div className="flex items-center">
              <Wifi className="w-5 h-5 text-green-600 mr-3" />
              <div>
                <p className="font-medium text-green-800">Çevrimiçi ve hazır</p>
                <p className="text-sm text-green-700">
                  Çevrimdışı kullanım için {selectedBranch ? 'bu branşa ait' : 'branşlara ait'} sorular önbelleğe alınmış.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Sınav Türü Seçimi */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Sınav Türü Seçin</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {examTypes.map((exam) => (
                <button
                  key={exam.id}
                  onClick={() => setSelectedExam(exam.id)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    selectedExam === exam.id
                      ? exam.color + ' border-current'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={selectedExam === exam.id ? '' : 'text-gray-500'}>
                      {exam.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold">{exam.name}</h3>
                      <p className="text-sm text-gray-600">{exam.description}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Branş Seçimi */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Branş Seçin</h2>
            <div className="grid md:grid-cols-3 gap-4">
              {branches.map((branch) => (
                <button
                  key={branch.id}
                  onClick={() => setSelectedBranch(branch.id)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    selectedBranch === branch.id
                      ? 'border-blue-500 bg-blue-50 text-blue-600'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <h3 className="font-semibold">{branch.name}</h3>
                  <p className="text-sm text-gray-600 mt-1">{branch.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Test Ayarları */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Soru Sayısı</h3>
              <div className="flex flex-wrap gap-2">
                {questionOptions.map((count) => (
                  <button
                    key={count}
                    onClick={() => setQuestionCount(count)}
                    className={`px-4 py-2 rounded-lg border transition-all ${
                      questionCount === count
                        ? 'border-blue-500 bg-blue-50 text-blue-600'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {count} Soru
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Süre</h3>
              <div className="flex flex-wrap gap-2">
                {durationOptions.map((min) => (
                  <button
                    key={min}
                    onClick={() => setDuration(min)}
                    className={`px-4 py-2 rounded-lg border transition-all flex items-center gap-2 ${
                      duration === min
                        ? 'border-blue-500 bg-blue-50 text-blue-600'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Clock className="w-4 h-4" />
                    {min} dk
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Test Özeti */}
          {isFormValid && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
              <h3 className="font-semibold text-blue-900 mb-2">Test Özeti</h3>
              <div className="grid md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-blue-600">Sınav:</span>
                  <span className="ml-2 font-medium">{selectedExam}</span>
                </div>
                <div>
                  <span className="text-blue-600">Branş:</span>
                  <span className="ml-2 font-medium">{branches.find(b => b.id === selectedBranch)?.name}</span>
                </div>
                <div>
                  <span className="text-blue-600">Soru:</span>
                  <span className="ml-2 font-medium">{questionCount} adet</span>
                </div>
                <div>
                  <span className="text-blue-600">Süre:</span>
                  <span className="ml-2 font-medium">{duration} dakika</span>
                </div>
              </div>
            </div>
          )}

          {/* Başlat Butonu */}
  
        <div className="flex justify-center">
            <button
              onClick={handleStart}
              disabled={!isFormValid || isSubmitting}
              className={`flex items-center gap-3 px-8 py-4 rounded-xl font-semibold transition-all ${
                !isFormValid || isSubmitting
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700 shadow-lg hover:shadow-xl'
              }`}
            >
              <Play className="w-5 h-5" />
              {isSubmitting ? 'Başlatılıyor...' : 'Testi Başlat'}
            </button>
          </div>

  
          {/* Bilgilendirme */}
          <div className="mt-8 text-center text-sm text-gray-500">
            <p>Test sonuçlarınız kaydedilecektir. İsterseniz sonrasında ücretsiz hesap oluşturabilirsiniz.</p>
          </div>
        </div>
      </div>

      {/* Toast Notifications from Global Provider */}
      {/* Toast component'leri ToastProvider tarafından App.jsx'de render ediliyor */}
    </AnimatedTransition>
  );
};

export default QuickTestPage;