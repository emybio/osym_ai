import React, { useState, useEffect, useCallback } from 'react';
import { Clock, ChevronRight, ChevronLeft, AlertCircle } from 'lucide-react';
import AnimatedTransition from './AnimatedTransition';
import { apiCall } from '../config/api';

const QuickTestExam = ({ sessionData, onComplete, onBack }) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeLeft, setTimeLeft] = useState(sessionData.duration_minutes * 60);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const questions = sessionData.questions || [];

  // Timer effect
  useEffect(() => {
    if (timeLeft <= 0) {
      handleSubmit();
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  // Format time
  const formatTime = useCallback((seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Handle answer selection
  const handleAnswerSelect = (questionId, option) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: option
    }));
  };

  // Navigation
  const nextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    }
  };

  const prevQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1);
    }
  };

  // Go to specific question
  const goToQuestion = (index) => {
    setCurrentQuestion(index);
  };

  // Calculate progress
  const answeredCount = Object.keys(answers).length;
  const progress = (answeredCount / questions.length) * 100;

  // Submit exam
  const handleSubmit = async () => {
    if (answeredCount === 0) {
      alert('Lütfen en az bir soru cevaplayın');
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await apiCall('/quicktest/save/', {
        method: 'POST',
        body: JSON.stringify({
          uuid: sessionData.uuid,
          answers: answers
        }),
      });

      // apiCall zaten JSON döndürür ve hata kontrolü yapar
      onComplete(result);

    } catch (error) {
      console.error('Error submitting exam:', error);
      alert('Test kaydedilemedi. Lütfen tekrar deneyin.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!questions.length) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Sorular yükleniyor...</p>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentQuestion];

  return (
    <AnimatedTransition>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <button
                  onClick={onBack}
                  className="p-2 hover:bg-gray-100 rounded-lg border border-gray-200"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div>
                  <h1 className="font-semibold text-gray-900">
                    {sessionData.exam_type} {sessionData.branch} Hızlı Test
                  </h1>
                  <p className="text-sm text-gray-600">
                    Soru {currentQuestion + 1} / {questions.length}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6">
                {/* Progress */}
                <div className="hidden md:block">
                  <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-600 transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {answeredCount}/{questions.length} cevaplandı
                  </p>
                </div>

                {/* Timer */}
                <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${
                  timeLeft < 60 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-700'
                }`}>
                  <Clock className="w-4 h-4" />
                  <span className="font-mono font-medium">{formatTime(timeLeft)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-6">
          {/* Question Navigation */}
          <div className="mb-6 overflow-x-auto">
            <div className="flex gap-2 pb-2">
              {questions.map((q, index) => (
                <button
                  key={q.id}
                  onClick={() => goToQuestion(index)}
                  className={`flex-shrink-0 w-10 h-10 rounded-lg border-2 text-sm font-medium transition-all ${
                    answers[q.id]
                      ? 'border-green-500 bg-green-50 text-green-700'
                      : index === currentQuestion
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  {index + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Question Card */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            {/* Question Header */}
            <div className="flex items-start justify-between mb-4">
              <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium">
                {currentQ.subject}
              </span>
              {currentQ.topic && (
                <span className="text-sm text-gray-500">
                  {currentQ.topic}
                </span>
              )}
            </div>

            {/* Question Text */}
            <div className="mb-6">
              <p className="text-gray-900 leading-relaxed whitespace-pre-wrap">
                {currentQ.question_text}
              </p>
            </div>

            {/* Options */}
            <div className="space-y-3">
              {Object.entries(currentQ.options).map(([label, text]) => (
                <button
                  key={label}
                  onClick={() => handleAnswerSelect(currentQ.id, label)}
                  className={`w-full p-4 text-left rounded-lg border-2 transition-all ${
                    answers[currentQ.id] === label
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                      answers[currentQ.id] === label
                        ? 'border-blue-500 bg-blue-500 text-white'
                        : 'border-gray-300'
                    }`}>
                      {answers[currentQ.id] === label && (
                        <span className="text-sm font-medium">{label}</span>
                      )}
                    </div>
                    <p className="text-gray-900 leading-relaxed">{text}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between">
            <button
              onClick={prevQuestion}
              disabled={currentQuestion === 0}
              className={`px-6 py-3 rounded-lg font-medium transition-all ${
                currentQuestion === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Önceki
            </button>

            <div className="text-sm text-gray-500">
              {answeredCount} / {questions.length} soru cevaplandı
            </div>

            {currentQuestion < questions.length - 1 ? (
              <button
                onClick={nextQuestion}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all flex items-center gap-2"
              >
                Sonraki
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={answeredCount === 0 || isSubmitting}
                className={`px-6 py-3 rounded-lg font-medium transition-all ${
                  answeredCount === 0 || isSubmitting
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {isSubmitting ? 'Gönderiliyor...' : 'Testi Bitir'}
              </button>
            )}
          </div>

          {/* Warning for time */}
          {timeLeft < 60 && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-red-700">
                Süre dolmak üzere! Son {timeLeft} saniye
              </p>
            </div>
          )}
        </div>
      </div>
    </AnimatedTransition>
  );
};

export default QuickTestExam;