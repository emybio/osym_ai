export const STUDENT_STATS = {
  totalExams: 24,
  avgScore: 78.5,
  totalQuestions: 960,
  correctAnswers: 753,
  weakTopics: ["Logaritma", "Trigonometri", "İntegral"],
  strongTopics: ["Denklemler", "Fonksiyonlar", "Geometri"],
  recentExams: [
    { date: "20.10.2024", subject: "Matematik", score: 85, duration: "45 dk" },
    { date: "18.10.2024", subject: "Fizik", score: 72, duration: "30 dk" },
    { date: "15.10.2024", subject: "Kimya", score: 68, duration: "28 dk" },
    { date: "12.10.2024", subject: "Matematik", score: 90, duration: "40 dk" },
  ],
};

export const AI_RECOMMENDATIONS = [
  {
    title: "Logaritma konusunu tekrar et",
    description: "Son 5 sınavda logaritma sorularında başarı oranı %45. Bu konuya öncelik vermeni öneriyorum.",
  },
  {
    title: "Trigonometri pratiği yap",
    description: "Trigonometri ifadelerinde zorlanıyorsun. 20 soru pratik yaparak pekiştirebilirsin.",
  },
  {
    title: "Çalışma tempon harika",
    description: "Son 7 gündür plana sadık kaldın. Bu tempoyu korursan hedef puanına yaklaşacaksın.",
  },
];

export const WEEKLY_ACTIVITY = [45, 60, 38, 72, 55, 68, 80];
export const WEEK_DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

export const SUBJECTS = [
  { id: "mat", name: "Matematik", badge: "40 soru", gradient: "from-blue-500 to-indigo-500" },
  { id: "fiz", name: "Fizik", badge: "14 soru", gradient: "from-emerald-500 to-emerald-600" },
  { id: "kim", name: "Kimya", badge: "13 soru", gradient: "from-rose-500 to-red-500" },
  { id: "bio", name: "Biyoloji", badge: "13 soru", gradient: "from-purple-500 to-purple-600" },
  { id: "tur", name: "Türkçe", badge: "40 soru", gradient: "from-pink-500 to-fuchsia-500" },
  { id: "sos", name: "Sosyal", badge: "20 soru", gradient: "from-amber-500 to-orange-500" },
];

export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";