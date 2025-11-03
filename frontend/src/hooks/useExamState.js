import { useState, useCallback } from 'react';
import { questionService, ApiError } from '../services/api';

export const useExamState = () => {
  const [examStarted, setExamStarted] = useState(false);
  const [question, setQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [selectedApi, setSelectedApi] = useState('openai');
  const [introShown, setIntroShown] = useState(true);

  const startExam = useCallback(async () => {
    console.log('=== START EXAM CALLED ===');
    console.log('Selected API:', selectedApi);
    console.log('Setting loading to true...');
    console.log('Hiding intro elements...');

    setLoadingQuestion(true);
    setErrorMessage('');
    setExplanation(null);
    setSelectedOption(null);
    setExamStarted(true);
    setIntroShown(false); // ← YENİ EKLENDİ

    try {
      console.log('Calling questionService.generate...');
      const data = await questionService.generate({
        subject: 'Matematik',
        topic: 'Temel Kavramlar',
        difficulty: 'Orta',
        provider: selectedApi,
      });

      console.log('Success! Received data:', data);
      setQuestion(data);
    } catch (error) {
      console.error('Error in startExam:', error);
      if (error instanceof ApiError) {
        console.log('API Error:', error.message);
        setErrorMessage(error.message);
      } else {
        console.log('Unknown error:', error);
        setErrorMessage('Soru oluşturulurken beklenmedik bir hata oluştu.');
      }
    } finally {
      console.log('Finally block - setting loading to false');
      setLoadingQuestion(false);
    }
  }, [selectedApi]);

  const explainAnswer = useCallback(async () => {
    if (!question) return;

    setLoadingExplanation(true);
    setErrorMessage('');

    try {
      console.log('Requesting explanation for question:', question.id);
      const data = await questionService.explain(question.id, selectedApi);
      console.log('Explanation received:', data);
      setExplanation(data.explanation || 'Açıklama alınamadı.');
    } catch (error) {
      console.error('Explanation error:', error);
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage('Çözüm alınırken beklenmedik bir hata oluştu.');
      }
    } finally {
      setLoadingExplanation(false);
    }
  }, [question, selectedApi]);

  const resetExamState = useCallback(() => {
    console.log('=== RESET EXAM STATE CALLED ===');
    console.log('Before reset:');
    console.log('  examStarted:', examStarted);
    console.log('  question:', question);
    console.log('  selectedOption:', selectedOption);
    console.log('  explanation:', explanation);
    console.log('  errorMessage:', errorMessage);
    console.log('  introShown:', introShown);

    setExamStarted(false);
    setQuestion(null);
    setSelectedOption(null);
    setExplanation(null);
    setErrorMessage('');
    setIntroShown(true); // ← YENİ EKLENDİ - intro'yu geri göster

    console.log('After reset - all states cleared, intro shown again');
  }, []);

  return {
    // State
    examStarted,
    question,
    selectedOption,
    setSelectedOption,
    explanation,
    loadingQuestion,
    loadingExplanation,
    errorMessage,
    selectedApi,
    setSelectedApi,
    introShown,

    // Actions (with expected prop names)
    onStart: startExam,
    onExplain: explainAnswer,
    onReset: resetExamState,

    // Keep original names too for backward compatibility
    startExam,
    explainAnswer,
    resetExamState,
  };
};