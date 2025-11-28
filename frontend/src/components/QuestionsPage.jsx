import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Calendar,
  Hash,
  Brain,
  Trash2,
  Loader2,
  Search,
  Filter,
} from 'lucide-react';
import { apiClient } from '../services/api';

const QuestionsPage = () => {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSubject, setFilterSubject] = useState('all');
  const [filterDifficulty, setFilterDifficulty] = useState('all');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [questionToDelete, setQuestionToDelete] = useState(null);

  // Subject options
  const subjectOptions = [
    { value: 'all', label: 'Tüm Dersler' },
    { value: 'MAT', label: 'Matematik' },
    { value: 'FIZ', label: 'Fizik' },
    { value: 'KIM', label: 'Kimya' },
    { value: 'BIO', label: 'Biyoloji' },
    { value: 'GEO', label: 'Geometri' },
  ];

  // Difficulty options
  const difficultyOptions = [
    { value: 'all', label: 'Tüm Seviyeler' },
    { value: 'E', label: 'Kolay' },
    { value: 'M', label: 'Orta' },
    { value: 'H', label: 'Zor' },
  ];

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      const response = await apiClient.request('/api/v1/questions/');
      setQuestions(response);
      setError(null);
    } catch (err) {
      setError('Sorular yüklenemedi: ' + (err.message || 'Bilinmeyen hata'));
      console.error('Error fetching questions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteQuestion = async (questionId) => {
    try {
      await apiClient.request(`/api/v1/questions/${questionId}/`, {
        method: 'DELETE',
      });
      setQuestions(questions.filter(q => q.id !== questionId));
      setShowDeleteModal(false);
      setQuestionToDelete(null);
    } catch (err) {
      console.error('Error deleting question:', err);
      alert('Soru silinemedi: ' + (err.message || 'Bilinmeyen hata'));
    }
  };

  // Filter questions based on search and filters
  const filteredQuestions = questions.filter(question => {
    const matchesSearch =
      question.stem?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      question.topic?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      question.rubric?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesSubject = filterSubject === 'all' || question.subject === filterSubject;
    const matchesDifficulty = filterDifficulty === 'all' || question.difficulty === filterDifficulty;

    return matchesSearch && matchesSubject && matchesDifficulty;
  });

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case 'E': return 'text-green-600 bg-green-50';
      case 'M': return 'text-yellow-600 bg-yellow-50';
      case 'H': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getDifficultyLabel = (difficulty) => {
    switch (difficulty) {
      case 'E': return 'Kolay';
      case 'M': return 'Orta';
      case 'H': return 'Zor';
      default: return 'Bilinmeyen';
    }
  };

  const getSourceIcon = (source) => {
    if (source === 'claude') {
      return <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">Claude</span>;
    } else if (source === 'deepseek') {
      return <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">DeepSeek</span>;
    } else if (source === 'openai') {
      return <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">OpenAI</span>;
    }
    return <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">{source}</span>;
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Sorular yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">Hata</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchQuestions}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" />
              Veritabanı Soruları
            </h1>
            <p className="text-gray-600 mt-1">
              Toplam {filteredQuestions.length} soru bulundu
            </p>
          </div>
          <button
            onClick={fetchQuestions}
            className="px-3 py-2 sm:px-4 sm:py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm sm:text-base"
          >
            Yenile
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Soru ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Subject Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <select
              value={filterSubject}
              onChange={(e) => setFilterSubject(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
            >
              {subjectOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Difficulty Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <select
              value={filterDifficulty}
              onChange={(e) => setFilterDifficulty(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
            >
              {difficultyOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        {filteredQuestions.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
            <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">Hiç soru bulunamadı</p>
          </div>
        ) : (
          filteredQuestions.map((question) => (
            <div
              key={question.id}
              className="bg-white border border-gray-200 rounded-xl p-4 sm:p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Question Header */}
                  <div className="flex flex-wrap items-center gap-1 sm:gap-2 mb-3">
                    <span className="text-xs sm:text-sm font-medium text-gray-500 flex items-center gap-1">
                      <Hash className="w-3 h-3 sm:w-4 sm:h-4" />
                      #{question.id}
                    </span>
                    <span className="text-xs sm:text-sm text-gray-500 flex items-center gap-1">
                      <Calendar className="w-3 h-3 sm:w-4 sm:h-4" />
                      {new Date(question.created_at).toLocaleDateString('tr-TR')}
                    </span>
                    {getSourceIcon(question.source)}
                    <span className={`text-xs px-1 sm:px-2 py-1 rounded-full ${getDifficultyColor(question.difficulty)}`}>
                      {getDifficultyLabel(question.difficulty)}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-700 px-1 sm:px-2 py-1 rounded-full">
                      {question.subject_display || question.subject}
                    </span>
                  </div>

                  {/* Question Content */}
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">
                    {question.stem}
                  </h3>

                  {/* Choices */}
                  <div className="grid sm:grid-cols-2 gap-2 mb-3">
                    {question.choices_display?.map((choice, index) => {
                      if (!choice || !question.answer) return null;
                      const isCorrect = choice.startsWith(String.fromCharCode(65 + question.answer.charCodeAt(0) - 65));
                      return (
                        <div
                          key={index}
                          className={`p-2 rounded-lg text-sm ${
                            isCorrect
                              ? 'bg-green-50 text-green-800 font-medium'
                              : 'bg-gray-50 text-gray-600'
                          }`}
                        >
                          {choice}
                        </div>
                      );
                    })}
                  </div>

                  {/* Rubric */}
                  {question.rubric && (
                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                      <p className="text-sm font-medium text-blue-900 mb-1">Çözüm:</p>
                      <p className="text-sm text-blue-800">{question.rubric}</p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setQuestionToDelete(question);
                      setShowDeleteModal(true);
                    }}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Soruyu Sil"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && questionToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-4 sm:p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Soru Silme Onayı
            </h3>
            <p className="text-gray-600 mb-6">
              #{questionToDelete.id} ID'li "{questionToDelete.stem.substring(0, 50)}..."
              sorusunu silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setQuestionToDelete(null);
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                İptal
              </button>
              <button
                onClick={() => handleDeleteQuestion(questionToDelete.id)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Sil
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionsPage;