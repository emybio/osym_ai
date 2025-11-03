import React, { useMemo, useState } from "react";
import {
  AlertCircle,
  Award,
  BarChart3,
  BookOpen,
  Brain,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  Clock,
  FileText,
  Home,
  Loader2,
  Menu,
  TrendingUp,
  User,
  X,
} from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"
const NAV_ITEMS = [
  { id: "home", label: "Anasayfa", icon: Home },
  { id: "dashboard", label: "Öğrenci Paneli", icon: BarChart3 },
  { id: "exams", label: "AI Sınavı", icon: FileText },
  {
    id: "progress",
    label: "İlerleme",
    icon: TrendingUp,
    submenu: [
      { id: "progress-overview", label: "Genel Bakış" },
      { id: "subjects", label: "Dersler" }
    ]
  },
];

const SUBJECTS = [
  { id: "mat", name: "Matematik", badge: "40 soru", gradient: "from-blue-500 to-indigo-500" },
  { id: "fiz", name: "Fizik", badge: "14 soru", gradient: "from-emerald-500 to-emerald-600" },
  { id: "kim", name: "Kimya", badge: "13 soru", gradient: "from-rose-500 to-red-500" },
  { id: "bio", name: "Biyoloji", badge: "13 soru", gradient: "from-purple-500 to-purple-600" },
  { id: "tur", name: "Türkçe", badge: "40 soru", gradient: "from-pink-500 to-fuchsia-500" },
  { id: "sos", name: "Sosyal", badge: "20 soru", gradient: "from-amber-500 to-orange-500" },
];

const STUDENT_STATS = {
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

const AI_RECOMMENDATIONS = [
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

const WEEKLY_ACTIVITY = [45, 60, 38, 72, 55, 68, 80];
const WEEK_DAYS = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

const Sidebar = ({ currentPage, onNavigate, mobileMenuOpen, onToggleMobile, expandedSubmenu, onToggleSubmenu }) => (
  <aside
    className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transform transition-transform duration-300 ease-in-out ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      }`}
  >
    <div className="p-4 border-b border-gray-200">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg flex items-center justify-center text-white font-bold">
          AI
        </div>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">OSYM Study</h1>
          <p className="text-sm text-gray-500">AI destekli sınav hazırlığı</p>
        </div>
      </div>
    </div>

    <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Navigasyon</p>
        <div className="space-y-1.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id || (item.submenu && expandedSubmenu === item.id);
            const hasSubmenu = item.submenu && item.submenu.length > 0;

            return (
              <div key={item.id}>
                <button
                  onClick={() => {
                    if (hasSubmenu) {
                      onToggleSubmenu(expandedSubmenu === item.id ? null : item.id);
                    } else {
                      onNavigate(item.id);
                      if (mobileMenuOpen) onToggleMobile(false);
                    }
                  }}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="flex-1 text-left">{item.label}</span>
                  {hasSubmenu && (
                    expandedSubmenu === item.id ?
                      <ChevronDown className="w-4 h-4" /> :
                      <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                {hasSubmenu && expandedSubmenu === item.id && (
                  <div className="ml-4 mt-1 space-y-1">
                    {item.submenu.map((subitem) => (
                      <button
                        key={subitem.id}
                        onClick={() => {
                          onNavigate(subitem.id);
                          if (mobileMenuOpen) onToggleMobile(false);
                        }}
                        className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          currentPage === subitem.id
                            ? "bg-blue-100 text-blue-700"
                            : "text-gray-600 hover:bg-gray-100"
                        }`}
                      >
                        {subitem.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>


      <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <Brain className="w-10 h-10 text-blue-600" />
          <div>
            <p className="text-sm font-semibold text-blue-900">AI Önerisi</p>
            <p className="text-xs text-blue-700">Çalışma planını yapay zeka ile kişiselleştir.</p>
          </div>
        </div>
        <button className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
          Plan Oluştur
        </button>
      </div>
    </nav>

    <div className="p-4 border-t border-gray-200">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
          <User className="w-5 h-5 text-gray-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">Zeynep Arslan</p>
          <p className="text-xs text-gray-500">TYT Adayı</p>
        </div>
      </div>
    </div>
  </aside>
);

const HomePage = ({ onStartExam }) => (
  <div className="grid gap-6 lg:grid-cols-3">
    <div className="lg:col-span-2 space-y-6">
      <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl p-8 text-white shadow-lg">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="text-blue-100 uppercase text-xs tracking-[0.3em]">AI Destekli Sınav</p>
            <h2 className="text-3xl font-semibold mt-2 mb-3">Bugün tek bir soru ile başla</h2>
            <p className="text-blue-100 max-w-xl">
              Yapay zeka seviyene uygun özgün sorular üretir, yanıtını analiz eder ve eksik olduğun konular için öneriler sunar.
            </p>
          </div>
          <button
            onClick={onStartExam}
            className="px-6 py-3 bg-white text-blue-700 font-semibold rounded-xl shadow hover:bg-blue-50 transition-colors"
          >
            AI Sorusu Oluştur
          </button>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <Award className="w-10 h-10 text-yellow-500" />
            <div>
              <p className="text-sm text-gray-500">Ortalama başarı</p>
              <p className="text-2xl font-semibold text-gray-900">{STUDENT_STATS.avgScore}%</p>
            </div>
          </div>
          <p className="text-sm text-gray-500">Son 5 sınavda ortalama başarı oranı.</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="w-10 h-10 text-blue-500" />
            <div>
              <p className="text-sm text-gray-500">Çalışma serisi</p>
              <p className="text-2xl font-semibold text-gray-900">7 gün</p>
            </div>
          </div>
          <p className="text-sm text-gray-500">Planına sadık kalmaya devam et!</p>
        </div>
      </div>
    </div>

    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          Son Sınavlar
        </h3>
        <div className="space-y-3">
          {STUDENT_STATS.recentExams.map((exam, idx) => (
            <div key={idx} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2.5">
              <div>
                <p className="text-sm font-medium text-gray-900">{exam.subject}</p>
                <p className="text-xs text-gray-500">{exam.date}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-green-600">%{exam.score}</p>
                <p className="text-xs text-gray-500">{exam.duration}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
          <Brain className="w-5 h-5 text-purple-600" />
          AI Önerileri
        </h3>
        <div className="space-y-3">
          {AI_RECOMMENDATIONS.map((item, idx) => (
            <div key={idx} className="border border-gray-100 rounded-lg p-3 bg-gray-50">
              <p className="text-sm font-semibold text-gray-900">{item.title}</p>
              <p className="text-xs text-gray-500">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const DashboardPage = () => (
  <div className="space-y-6">
    <div className="grid gap-4 md:grid-cols-3">
      <StatisticCard title="Toplam Çözülen Soru" value={STUDENT_STATS.totalQuestions} icon={FileText} accent="bg-blue-500/10 text-blue-600" />
      <StatisticCard title="Doğru Cevap" value={STUDENT_STATS.correctAnswers} icon={CheckCircle} accent="bg-emerald-500/10 text-emerald-600" />
      <StatisticCard title="Sınav Sayısı" value={STUDENT_STATS.totalExams} icon={Award} accent="bg-purple-500/10 text-purple-600" />
    </div>

    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Haftalık çalışma grafiği</h3>
        <div className="flex items-end gap-3 h-48">
          {WEEKLY_ACTIVITY.map((value, idx) => (
            <div key={idx} className="flex-1 flex flex-col items-center gap-2">
              <div className="w-full bg-gray-100 rounded-t-xl overflow-hidden h-full relative">
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-blue-600 to-blue-400" style={{ height: `${value}%` }} />
              </div>
              <span className="text-xs text-gray-500 font-medium">{WEEK_DAYS[idx]}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-3">
            <TrendingUp className="w-5 h-5 text-emerald-600" />
            Güçlü konular
          </h3>
          <div className="space-y-2">
            {STUDENT_STATS.strongTopics.map((topic, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-lg bg-emerald-50 text-emerald-700 text-sm font-medium">
                <span>{topic}</span>
                <span>%{85 + idx * 3}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-3">
            <BookOpen className="w-5 h-5 text-rose-600" />
            Çalışılması gereken
          </h3>
          <div className="space-y-2">
            {STUDENT_STATS.weakTopics.map((topic, idx) => (
              <div key={idx} className="flex items-center justify-between px-3 py-2 rounded-lg bg-rose-50 text-rose-600 text-sm font-medium">
                <span>{topic}</span>
                <span>%{45 + idx * 5}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

const StatisticCard = ({ title, value, icon: Icon, accent }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4 shadow-sm">
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${accent}`}>
      <Icon className="w-6 h-6" />
    </div>
    <div>
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  </div>
);

const formatExplanation = (raw) => {
  if (!raw) return [];
  try {
    const normalized = raw.replace(/\\n/g, "\n").replace(/\\'/g, "'").replace(/'/g, '"');
    const parsed = JSON.parse(normalized);
    if (Array.isArray(parsed)) {
      return parsed;
    }
  } catch {
    // ignore parsing failure
  }
  return raw.split(/\n+/).map((line) => line.trim()).filter(Boolean);
};

const ExamPage = ({
  onStart,
  onExplain,
  onReset,
  examStarted,
  question,
  selectedOption,
  setSelectedOption,
  explanation,
  loadingQuestion,
  loadingExplanation,
  errorMessage,
  selectedApi,        // 🔹 eksik prop eklendi
  setSelectedApi,     // 🔹 eksik prop eklendi
}) => {
  const correctIndex = useMemo(() => {
    if (!question?.answer) return null;
    const letter = question.answer.trim().charAt(0).toUpperCase();
    const code = letter.charCodeAt(0);
    if (code < 65 || code > 69) return null;
    return code - 65;
  }, [question]);

  const explanationSteps = useMemo(() => (explanation ? formatExplanation(explanation) : []), [explanation]);

  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 px-5 py-4 bg-gray-50">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">AI Exam Mode</p>
            <h2 className="text-xl font-semibold text-gray-900">Yapay Zeka ile Soru Çözümü</h2>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-50 text-blue-700 font-medium">
              <Award className="w-4 h-4" />
              Seviyene uygun dinamik sorular
            </div>
            <button
              onClick={onReset}
              className="px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-100 text-sm font-medium"
            >
              Sıfırla
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {errorMessage && (
            <div className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <div>
                {errorMessage}
                <button onClick={onStart} className="block text-rose-600 font-medium mt-2 hover:underline">
                  Tekrar dene
                </button>
              </div>
            </div>
          )}

          {!examStarted && (
            <div className="flex flex-col items-center justify-center text-center py-16 px-6 rounded-2xl border border-dashed border-gray-200">
              <div className="w-16 h-16 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
                <Brain className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-2">Hazırsan başlayalım</h3>
              <p className="text-sm text-gray-500 max-w-md mb-6">
                Yapay zeka seviyene uygun matematik sorusu üretsin, birlikte çözelim ve adım adım açıklamasını dinleyelim.
              </p>
              <div className="flex items-center gap-4 text-sm">
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="radio"
                name="apiSelect"
                value="openai"
                checked={selectedApi === "openai"}
                onChange={(e) => setSelectedApi(e.target.value)}
              />
              OpenAI
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="radio"
                name="apiSelect"
                value="zai"
                checked={selectedApi === "zai"}
                onChange={(e) => setSelectedApi(e.target.value)}
              />
              Z.ai
            </label>
          </div>
              <button
                onClick={onStart}
                disabled={loadingQuestion}
                className="px-6 py-3 rounded-xl bg-blue-600 text-white font-semibold shadow hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loadingQuestion && <Loader2 className="w-4 h-4 animate-spin" />}
                {loadingQuestion ? "Hazırlanıyor..." : "AI Sorusu Oluştur"}
              </button>
            </div>
          )}

          {examStarted && question && (
            <div className="grid lg:grid-cols-[2fr,1fr] gap-6">
              <div className="space-y-5">
                <div className="p-5 border border-gray-200 rounded-xl bg-white shadow-sm">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <p className="text-xs font-medium text-blue-600 uppercase tracking-[0.3em]">Soru Metni</p>
                      <h3 className="text-lg font-semibold text-gray-900 mt-1 mb-2">{question.topic || "Matematik"}</h3>
                      <p className="text-gray-800 leading-relaxed">{question.stem}</p>
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      <p>Seviye: {question.difficulty || "Orta"}</p>
                    </div>
                  </div>

                  <div className="grid gap-3">
                    {(question.choices || []).map((choice, index) => {
                      const isSelected = selectedOption === index;
                      const isCorrect = correctIndex === index;
                      const showAnswer = Boolean(explanation);

                      let border = "border-gray-200";
                      let background = "bg-white";
                      let text = "text-gray-700";
                      if (showAnswer && isSelected) {
                        if (isCorrect) {
                          border = "border-emerald-500";
                          background = "bg-emerald-50";
                          text = "text-emerald-700";
                        } else {
                          border = "border-rose-400";
                          background = "bg-rose-50";
                          text = "text-rose-700";
                        }
                      } else if (showAnswer && isCorrect) {
                        border = "border-emerald-400";
                        background = "bg-emerald-50/80";
                        text = "text-emerald-700";
                      } else if (!showAnswer && isSelected) {
                        border = "border-blue-500";
                        background = "bg-blue-50";
                        text = "text-blue-700";
                      }

                      return (
                        <button
                          key={index}
                          onClick={() => setSelectedOption(index)}
                          disabled={Boolean(explanation)}
                          className={`w-full text-left px-4 py-3 rounded-xl border ${border} ${background} ${text} font-medium transition hover:border-blue-500 disabled:cursor-not-allowed`}
                        >
                          {choice}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={onExplain}
                    disabled={selectedOption === null || loadingExplanation}
                    className="flex items-center gap-2 px-5 py-3 rounded-xl bg-green-600 text-white font-semibold shadow hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {loadingExplanation && <Loader2 className="w-4 h-4 animate-spin" />}
                    Çözümü Göster
                  </button>
                  <button
                    onClick={onStart}
                    disabled={loadingQuestion}
                    className="px-5 py-3 rounded-xl border border-gray-200 text-gray-700 font-semibold hover:bg-gray-100 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    Yeni Soru
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                <div className="border border-gray-200 bg-white rounded-xl p-4 shadow-sm">
                  <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4 text-blue-600" />
                    Soru bilgileri
                  </h4>
                  <ul className="text-sm text-gray-600 space-y-1.5">
                    <li>Branş: Matematik</li>
                    <li>Zorluk: {question.difficulty || "Orta"}</li>
                    <li>Kaynak: Yapay zeka</li>
                    <li>Yanıtlanan: {selectedOption !== null ? "Evet" : "Hayır"}</li>
                  </ul>
                </div>

                {explanation && (
                  <div className="border border-emerald-200 bg-emerald-50 rounded-xl p-5 text-sm text-emerald-700 space-y-3">
                    <div className="flex items-center gap-2 font-semibold">
                      <CheckCircle className="w-4 h-4" />
                      Yapay zeka açıklaması
                    </div>
                    <div className="space-y-2 text-emerald-800">
                      {explanationSteps.map((step, idx) => (
                        <div key={idx} className="flex gap-2">
                          <span className="font-semibold">{idx + 1}.</span>
                          <span>{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ProgressPage = () => (
  <div className="grid gap-6 md:grid-cols-2">
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
        <TrendingUp className="w-5 h-5 text-blue-600" />
        Sınav performansı
      </h3>
      <p className="text-sm text-gray-500 mb-5">
        Son 6 sınavda performansındaki değişim. Yapay zeka, düzenli pratik ile başarı oranını %15 artırabileceğini öngörüyor.
      </p>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div className="p-4 rounded-xl bg-blue-50 text-blue-700 font-medium text-center">
          <p className="text-2xl font-semibold text-blue-900 mb-1">78%</p>
          Ortalama
        </div>
        <div className="p-4 rounded-xl bg-emerald-50 text-emerald-700 font-medium text-center">
          <p className="text-2xl font-semibold text-emerald-900 mb-1">+6%</p>
          Haftalık artış
        </div>
        <div className="p-4 rounded-xl bg-purple-50 text-purple-700 font-medium text-center">
          <p className="text-2xl font-semibold text-purple-900 mb-1">320 dk</p>
          Haftalık hedef
        </div>
      </div>
    </div>

    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="flex items-center gap-2 text-gray-900 font-semibold mb-4">
        <BookOpen className="w-5 h-5 text-indigo-600" />
        Çalışma planı
      </h3>
      <div className="space-y-3 text-sm text-gray-600">
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Pazartesi - Çarşamba: 45 dk Matematik, 30 dk Türkçe
        </div>
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Perşembe - Cuma: 40 dk Fen Bilimleri, 20 dk Sosyal Bilimler
        </div>
        <div className="p-3 rounded-lg bg-gray-50 border border-gray-100">
          Hafta sonu: 2 deneme sınavı + analiz
        </div>
      </div>
    </div>
  </div>
);

const SubjectsPage = () => (
  <div className="space-y-6">
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-4">Dersler</h2>
      <p className="text-gray-600 mb-6">
        Tüm derslerinizdeki ilerlemeyi detaylı şekilde takip edin. Her ders için çalışma istatistikleri, zayıf ve güçlü konular hakkında analizler.
      </p>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {SUBJECTS.map((subject) => (
          <div key={subject.id} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-4 mb-4">
              <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${subject.gradient} text-white flex items-center justify-center text-lg font-semibold`}>
                {subject.name.slice(0, 2)}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{subject.name}</h3>
                <p className="text-sm text-gray-500">{subject.badge}</p>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Başarı Oranı</span>
                <span className="text-sm font-semibold text-green-600">{75 + Math.floor(Math.random() * 20)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Çalışılan Süre</span>
                <span className="text-sm font-semibold text-blue-600">{Math.floor(Math.random() * 100 + 50)} saat</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Son Çalışma</span>
                <span className="text-sm font-semibold text-gray-600">{Math.floor(Math.random() * 7 + 1)} gün önce</span>
              </div>

              <div className="pt-3 border-t border-gray-100">
                <div className="text-xs text-gray-500 mb-2">Güçlü konular:</div>
                <div className="flex flex-wrap gap-1">
                  {["Temel Kavramlar", "Denklemler", "Problemler"].slice(0, Math.floor(Math.random() * 3) + 1).map((topic, idx) => (
                    <span key={idx} className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded-full">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>

              <button className="w-full mt-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
                Detayları Gör
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default function App() {
  const [currentPage, setCurrentPage] = useState("exams");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);
  const [selectedApi, setSelectedApi] = useState("openai"); // 🔹 yeni state
  const [examStarted, setExamStarted] = useState(false);
  const [question, setQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const startExam = async () => {
    setLoadingQuestion(true);
    setErrorMessage("");
    setExplanation(null);
    setSelectedOption(null);
    setCurrentPage("exams");
    try {
      const res = await fetch(`${API_URL}/api/v1/questions/generate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: "MAT",
          topic: "Temel Kavramlar",
          difficulty: "M",
          provider: selectedApi, // 🔹 eklendi
        }),
      });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || payload.error || "Soru alınamadı.");
      }
      const data = await res.json();
      setQuestion(data);
      setExamStarted(true);
    } catch (error) {
      setErrorMessage(error.message || "Soru oluşturulurken hata oluştu.");
    } finally {
      setLoadingQuestion(false);
    }
  };

  const explainAnswer = async () => {
    if (!question) return;
    setLoadingExplanation(true);
    setErrorMessage("");
    try {
      const res = await fetch(`${API_URL}/api/v1/questions/${question.id}/explain/`, { method: "POST" });
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || payload.error || "Çözüm alınamadı.");
      }
      const data = await res.json();
      setExplanation(data.explanation || "");
    } catch (error) {
      setErrorMessage(error.message || "Çözüm alınırken hata oluştu.");
    } finally {
      setLoadingExplanation(false);
    }
  };

  const resetExamState = () => {
    setExamStarted(false);
    setQuestion(null);
    setSelectedOption(null);
    setExplanation(null);
    setErrorMessage("");
  };

  return (
    <div className="min-h-screen bg-gray-50 lg:pl-64">
      <Sidebar
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobile={setMobileMenuOpen}
        expandedSubmenu={expandedSubmenu}
        onToggleSubmenu={setExpandedSubmenu}
      />

      {mobileMenuOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-30 lg:hidden" onClick={() => setMobileMenuOpen(false)} />
      )}

      <div>
        <header className=" bg-white border-b border-gray-200 sticky top-0 z-20">
          

          <div className="p-4 max-w-5xl mx-auto w-full px-4 md:px-6 py-4 flex items-center justify-between gap-4">
            <button
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg border border-gray-200 text-gray-600"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <Clock className="w-4 h-4 text-blue-600" />
              <span>Sınava kalan: 5646****gün</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <User className="w-4 h-4 text-gray-500" />
              <span>TYT Adayı</span>
            </div>
          </div>
        </header>

        <main className="max-w-5xl mx-auto w-full px-4 md:px-6 py-8 space-y-8">
          {currentPage === "home" && <HomePage onStartExam={startExam} />}
          {currentPage === "dashboard" && <DashboardPage />}
          {currentPage === "exams" && (
            <ExamPage
              onStart={startExam}
              onExplain={explainAnswer}
              onReset={resetExamState}
              examStarted={examStarted}
              question={question}
              selectedOption={selectedOption}
              setSelectedOption={setSelectedOption}
              explanation={explanation}
              loadingQuestion={loadingQuestion}
              loadingExplanation={loadingExplanation}
              errorMessage={errorMessage}
              selectedApi={selectedApi}
              setSelectedApi={setSelectedApi}
            />
          )}
          {currentPage === "progress" && <ProgressPage />}
          {currentPage === "progress-overview" && <ProgressPage />}
          {currentPage === "subjects" && <SubjectsPage />}
        </main>
      </div>
    </div>
  );
}
