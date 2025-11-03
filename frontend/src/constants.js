// API Configuration
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// App Configuration
export const APP_NAME = 'OSYM AI';
export const APP_VERSION = '1.0.0';

// Dashboard Data
export const STUDENT_STATS = {
  totalQuestions: 156,
  correctAnswers: 142,
  averageTime: 45,
  weeklyProgress: 78,
  totalExams: 23,
  avgScore: 87,
  strongTopics: ['Matematik - Cebir', 'Fizik - Mekanik', 'Türkçe - Anlam Bilgisi'],
  weakTopics: ['Geometri - Analitik', 'Kimya - Organik', 'Biyoloji - Genetik'],
  recentExams: [
    { subject: 'Matematik', date: '2 gün önce', score: 92, duration: '25 dk' },
    { subject: 'Türkçe', date: '3 gün önce', score: 85, duration: '20 dk' },
    { subject: 'Fizik', date: '5 gün önce', score: 88, duration: '30 dk' },
    { subject: 'Kimya', date: '1 hafta önce', score: 79, duration: '22 dk' },
    { subject: 'Biyoloji', date: '1 hafta önce', score: 91, duration: '18 dk' }
  ]
};

export const WEEKLY_ACTIVITY = [65, 55, 85, 70, 90, 60, 45];

export const WEEK_DAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

export const AI_RECOMMENDATIONS = [
  {
    id: 1,
    title: 'Geometri Konularını Tekrar Et',
    description: 'Analitik geometride temel konuları gözden geçir',
    type: 'subject',
    priority: 'high'
  },
  {
    id: 2,
    title: 'Orta Seviye Cebir Soruları',
    description: 'Denklem çözme ve faktörizasyon练习',
    type: 'practice',
    priority: 'medium'
  },
  {
    id: 3,
    title: 'Zaman Yönetimi Egzersizi',
    description: 'Soru başına harcanan süreyi optimize et',
    type: 'technique',
    priority: 'low'
  }
];

export const SUBJECTS = [
  { id: 1, name: 'Matematik', icon: '📐', progress: 75, totalQuestions: 45 },
  { id: 2, name: 'Türkçe', icon: '📚', progress: 82, totalQuestions: 38 },
  { id: 3, name: 'Fizik', icon: '⚡', progress: 60, totalQuestions: 25 },
  { id: 4, name: 'Kimya', icon: '🧪', progress: 68, totalQuestions: 22 },
  { id: 5, name: 'Biyoloji', icon: '🧬', progress: 90, totalQuestions: 18 }
];