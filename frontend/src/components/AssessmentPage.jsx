import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../api/config';
import {
  Brain,
  Target,
  Clock,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Loader2,
  TrendingUp,
  BookOpen,
  Award
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';
import SkeletonLoader from './SkeletonLoader';

const AssessmentPage = ({ onComplete, onBack }) => {
  const [currentStep, setCurrentStep] = useState('welcome');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [questionStartTime, setQuestionStartTime] = useState(null);
  const [timePerQuestion, setTimePerQuestion] = useState(60);
  const [timeRemaining, setTimeRemaining] = useState(60);

  useEffect(() => {
    let interval;
    if (currentStep === 'quiz' && currentQuestion >= 0 && !isTransitioning) {
      interval = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            handleTimeUp();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [currentStep, currentQuestion, isTransitioning]);

  useEffect(() => {
    let interval;
    if (currentStep === 'quiz') {
      interval = setInterval(() => {
        setTimeElapsed(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [currentStep]);

  useEffect(() => {
    if (currentStep === 'quiz') {
      setTimeRemaining(timePerQuestion);
      setQuestionStartTime(Date.now());
    }
  }, [currentQuestion, currentStep]);

  const subjects = [
    { id: 'MAT', name: 'Matematik', icon: '📐', color: 'blue' },
    { id: 'FIZ', name: 'Fizik', icon: '⚡', color: 'purple' },
    { id: 'KIM', name: 'Kimya', icon: '🧪', color: 'green' }
  ];

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const generateQuestions = async (subject) => {
    setIsLoading(true);
    try {
      const response = await fetch(getApiUrl('/questions/generate/'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subject: subjects.find(s => s.id === subject)?.name || 'Matematik',
          topic: 'Genel Değerlendirme',
          difficulty: 'Orta',
          provider: 'zai'
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.choices && data.choices.length >= 3) {
          const assessmentQuestions = [];
          for (let i = 0; i < 3; i++) {
            const question = {
              id: i,
              stem: data.stem,
              choices: data.choices,
              answer: data.answer,
              rubric: data.rubric,
              subject: data.subject
            };
            assessmentQuestions.push(question);
          }
          setQuestions(assessmentQuestions);
          setCurrentStep('quiz');
        } else {
          throw new Error('API failed, using database fallback');
        }
      } else {
        throw new Error('API request failed');
      }
    } catch (error) {
      console.error('Error generating questions:', error);
      const fallbackQuestions = [
        {
          id: 0,
          stem: "2 + 2 = ?",
          choices: ["A) 3", "B) 4", "C) 5", "D) 6"],
          answer: "B",
          rubric: "Temel aritmetik işlemi",
          subject: "Matematik"
        },
        {
          id: 1,
          stem: "Bir araba 10 m/s hızla hareket ediyor. 20 saniyede ne kadar yol alır?",
          choices: ["A) 100 m", "B) 150 m", "C) 200 m", "D) 250 m"],
          answer: "C",
          rubric: "Mesafe = hız × zaman",
          subject: "Fizik"
        },
        {
          id: 2,
          stem: "H2O'nun kimyasal adı nedir?",
          choices: ["A) Karbondioksit", "B) Oksijen", "C) Su", "D) Azot"],
          answer: "C",
          rubric: "Bileşik adlandırma",
          subject: "Kimya"
        }
      ];
      setQuestions(fallbackQuestions);
      setCurrentStep('quiz');
    }
    setIsLoading(false);
  };

  const handleTimeUp = () => {
    const newAnswers = [...answers];
    newAnswers[currentQuestion] = 'TIME_UP';
    setAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentQuestion(currentQuestion + 1);
        setIsTransitioning(false);
      }, 300);
    } else {
      calculateResults(newAnswers);
    }
  };

  const handleAnswer = (answer) => {
    const timeSpent = questionStartTime ? Math.floor((Date.now() - questionStartTime) / 1000) : 0;

    const newAnswers = [...answers];
    newAnswers[currentQuestion] = {
      answer: answer,
      timeSpent: timeSpent
    };
    setAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setIsTransitioning(true);
      setTimeout(() => {
        setCurrentQuestion(currentQuestion + 1);
        setIsTransitioning(false);
      }, 300);
    } else {
      calculateResults(newAnswers);
    }
  };

  const calculateResults = (userAnswers) => {
    let correctCount = 0;
    let totalTimeSpent = 0;
    let averageTimePerQuestion = 0;

    const questionResults = questions.map((question, idx) => {
      const userAnswerObj = userAnswers[idx];
      const isTimeUp = userAnswerObj === 'TIME_UP';
      const userAnswer = isTimeUp ? null : userAnswerObj.answer;
      const timeSpent = isTimeUp ? timePerQuestion : (userAnswerObj.timeSpent || 0);

      const isCorrect = !isTimeUp && userAnswer === question.answer;
      if (isCorrect) correctCount++;

      totalTimeSpent += timeSpent;

      return {
        question: question.stem,
        userAnswer: isTimeUp ? 'Süre Doldu' : userAnswer,
        correctAnswer: question.answer,
        isCorrect,
        timeSpent,
        isTimeUp
      };
    });

    averageTimePerQuestion = Math.round(totalTimeSpent / questions.length);

    const percentage = (correctCount / questions.length) * 100;
    let level, recommendation, color;

    if (percentage >= 80) {
      level = "İleri Düzey";
      recommendation = "Zor sorularla çalışmaya devam etmelisin";
      color = "purple";
    } else if (percentage >= 50) {
      level = "Orta Düzey";
      recommendation = "Temel konuları pekiştirip zor seviyeye geçmelisin";
      color = "blue";
    } else {
      level = "Başlangıç Düzey";
      recommendation = "Temel konularla başlayıp kademeli ilerlemelisin";
      color = "green";
    }

    const timePerformance = {
      totalTime: formatTime(timeElapsed),
      averageTime: `${averageTimePerQuestion}s`,
      timePerQuestion: timePerQuestion,
      totalTimeSpent
    };

    setResults({
      score: percentage,
      correctCount,
      totalQuestions: questions.length,
      level,
      recommendation,
      color,
      questionResults,
      timePerformance,
      subject: subjects.find(s => s.id === selectedSubject)?.name
    });

    setCurrentStep('results');
  };

  const restartAssessment = () => {
    setCurrentStep('welcome');
    setSelectedSubject('');
    setCurrentQuestion(0);
    setQuestions([]);
    setAnswers([]);
    setResults(null);
    setTimeElapsed(0);
  };

  if (currentStep === 'welcome') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center px-4">
        <div className="max-w-4xl w-full">
          {isLoading && (
            <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center">
              <LoadingSpinner size="large" text="Sorular hazırlanıyor..." />
            </div>
          )}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
              <Target className="w-4 h-4" />
              Seviye Belirleme Testi
            </div>
            <h1 className="text-4xl font-bold text-gray-900 mb-6">
              Hangi Düzeyde
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                Başlamalısın?
              </span>
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              3 soruluk hızlı test ile seviyenizi öğrenin ve kişiselleştirilmiş çalışma planı alın
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                onClick={() => setSelectedSubject(subject.id)}
                className={`group relative p-8 rounded-2xl border-2 transition-all duration-300 ${
                  selectedSubject === subject.id
                    ? 'border-blue-500 bg-blue-50 shadow-lg'
                    : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
                }`}
              >
                <div className="text-4xl mb-4">{subject.icon}</div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">{subject.name}</h3>
                <p className="text-gray-600 text-sm">
                  {subject.name} seviyenizi ölçün
                </p>
                {selectedSubject === subject.id && (
                  <div className="absolute top-4 right-4">
                    <CheckCircle className="w-6 h-6 text-blue-600" />
                  </div>
                )}
              </button>
            ))}
          </div>

          <div className="flex justify-center gap-4">
            <button
              onClick={onBack}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-colors"
            >
              Ana Sayfaya Dön
            </button>
            <button
              onClick={() => selectedSubject && generateQuestions(selectedSubject)}
              disabled={!selectedSubject || isLoading}
              className={`inline-flex items-center gap-2 px-8 py-3 rounded-xl font-semibold transition-all ${
                selectedSubject && !isLoading
                  ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:shadow-lg transform hover:-translate-y-0.5'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Sorular hazırlanıyor...
                </>
              ) : (
                <>
                  Teste Başla
                  <ChevronRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 'quiz') {
    const question = questions[currentQuestion];
    const progress = ((currentQuestion + 1) / questions.length) * 100;
    const timePercentage = (timeRemaining / timePerQuestion) * 100;
    const timerColor = timeRemaining <= 10 ? 'text-red-600' : timeRemaining <= 20 ? 'text-orange-500' : 'text-blue-600';

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center px-4">
        <div className="max-w-3xl w-full">
          {isTransitioning && (
            <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center">
              <LoadingSpinner size="medium" text="Sonraki soru..." showText={false} />
            </div>
          )}

          <div className="mb-8">
            <div className="flex justify-between items-center mb-4">
              <span className="text-sm font-medium text-gray-600">
                Soru {currentQuestion + 1} / {questions.length}
              </span>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Clock className="w-4 h-4" />
                Toplam: {formatTime(timeElapsed)}
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div
                className="bg-gradient-to-r from-blue-600 to-indigo-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className={`w-5 h-5 ${timerColor}`} />
                  <span className="font-medium text-gray-900">Bu soru için kalan süre:</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-2xl font-bold ${timerColor}`}>
                    {timeRemaining}s
                  </span>
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-1000 ${
                        timeRemaining <= 10 ? 'bg-red-500' :
                        timeRemaining <= 20 ? 'bg-orange-500' :
                        'bg-green-500'
                      }`}
                      style={{ width: `${timePercentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm font-medium mb-4">
                <Brain className="w-4 h-4" />
                {question.subject}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                {question.stem}
              </h2>
            </div>

            <div className="grid gap-3">
              {question.choices.map((choice, idx) => {
                const letter = choice.split(')')[0];
                return (
                  <button
                    key={idx}
                    onClick={() => handleAnswer(letter)}
                    className="group w-full text-left p-4 rounded-xl border-2 border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-all duration-200"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{choice}</span>
                      <div className="w-6 h-6 rounded-full border-2 border-gray-300 group-hover:border-blue-400" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 'results') {
    const subjectColor = subjects.find(s => s.id === selectedSubject)?.color || 'blue';
    const colorMap = {
      'blue': 'bg-blue-100 text-blue-700',
      'green': 'bg-green-100 text-green-700',
      'red': 'bg-red-100 text-red-700',
      'yellow': 'bg-yellow-100 text-yellow-700',
      'purple': 'bg-purple-100 text-purple-700',
      'indigo': 'bg-indigo-100 text-indigo-700',
      'pink': 'bg-pink-100 text-pink-700',
      'orange': 'bg-orange-100 text-orange-700'
    };
    const subjectColorClass = colorMap[subjectColor] || colorMap.blue;

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center px-4">
        <div className="max-w-4xl w-full">
          <div className="text-center mb-12">
            <div className={`inline-flex items-center gap-2 ${subjectColorClass} px-4 py-2 rounded-full text-sm font-medium mb-6`}>
              <Award className="w-4 h-4" />
              Test Tamamlandı!
            </div>
            <h1 className="text-4xl font-bold text-gray-900 mb-6">
              Seviyeniz: <span className={`text-${subjectColor}-600`}>{results.level}</span>
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              {results.subject} testinde {results.correctCount}/{results.totalQuestions} soruya doğru cevap verdiniz
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6 mb-12">
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Test Özeti</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Doğru Cevap</span>
                  <span className="font-bold text-green-600">{results.correctCount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Yanlış Cevap</span>
                  <span className="font-bold text-red-600">{results.totalQuestions - results.correctCount}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Başarı Oranı</span>
                  <span className="font-bold text-blue-600">{Math.round(results.score)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Toplam Süre</span>
                  <span className="font-bold text-gray-900">{results.timePerformance.totalTime}</span>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-orange-500 to-red-600 rounded-2xl shadow-xl p-8 text-white">
              <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Zaman Performansı
              </h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-orange-100">Ortalama Süre</span>
                  <span className="font-bold text-2xl">{results.timePerformance.averageTime}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-orange-100">Hedef Süre</span>
                  <span className="font-bold">{results.timePerformance.timePerQuestion}s/soru</span>
                </div>
                <div className="bg-white/20 backdrop-blur rounded-lg p-3">
                  <p className="text-sm text-orange-100">
                    {results.timePerformance.averageTime <= results.timePerformance.timePerQuestion
                      ? "Harika zaman yönetimi! YKS sınavında başarılı olacaksın."
                      : "Zaman yönetimini iyileştirmen gerekiyor. Daha hızlı düşünmelisin."
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl shadow-xl p-8 text-white mb-8">
            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Önerilerimiz
            </h3>
            <p className="text-blue-100 mb-4">{results.recommendation}</p>
            <div className="bg-white/20 backdrop-blur rounded-lg p-4">
              <p className="font-medium">Bu sonuçlara göre kişiselleştirilmiş çalışma planı oluşturmak ister misiniz?</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Detaylı Sonuçlar</h3>
            <div className="space-y-3">
              {results.questionResults.map((result, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    result.isCorrect
                      ? 'border-green-200 bg-green-50'
                      : result.isTimeUp
                      ? 'border-orange-200 bg-orange-50'
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900">Soru {idx + 1}</span>
                      {result.isTimeUp && (
                        <span className="text-xs bg-orange-200 text-orange-700 px-2 py-1 rounded-full">Süre Doldu</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{result.question}</p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-600">Cevabınız: {result.userAnswer}</span>
                      <span className="text-gray-600">Doğru: {result.correctAnswer}</span>
                      {!result.isTimeUp && (
                        <span className={`font-medium ${
                          result.timeSpent <= 30 ? 'text-green-600' :
                          result.timeSpent <= 45 ? 'text-orange-600' :
                          'text-red-600'
                        }`}>
                          Süre: {result.timeSpent}s
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    {result.isCorrect ? (
                      <CheckCircle className="w-6 h-6 text-green-600" />
                    ) : result.isTimeUp ? (
                      <Clock className="w-6 h-6 text-orange-600" />
                    ) : (
                      <AlertCircle className="w-6 h-6 text-red-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-center gap-4">
            <button
              onClick={restartAssessment}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-colors"
            >
              Tekrar Test Yap
            </button>
            <button
              onClick={() => onComplete(results)}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all"
            >
              <BookOpen className="w-5 h-5" />
              Çalışmaya Başla
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default AssessmentPage;