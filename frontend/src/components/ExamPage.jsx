import React, { useMemo } from 'react';
import {
  AlertCircle,
  Award,
  Brain,
  CheckCircle,
  Clock,
  Loader2,
} from 'lucide-react';

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
  selectedApi,
  setSelectedApi,
  introShown, // ← YENİ PROP
}) => {
  const correctIndex = useMemo(() => {
    if (!question?.answer) return null;
    const letter = question.answer.trim().charAt(0).toUpperCase();
    const code = letter.charCodeAt(0);
    if (code < 65 || code > 69) return null;
    return code - 65;
  }, [question]);

  const explanationSteps = useMemo(() => (explanation ? formatExplanation(explanation) : []), [explanation]);

  const handleExplainClick = () => {
    console.log('Explain button clicked');
    onExplain();
  };

  const handleNewQuestionClick = async () => {
  console.log('New question button clicked');
  if (loadingQuestion) return; // zaten yükleniyorsa engelle 
  // onReset();
  await onStart(); // yeni soruyu başlat
};

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
              onClick={() => {
                console.log('=== RESET BUTTON CLICKED ===');
                console.log('onReset function:', onReset);
                onReset();
              }}
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




          <div className={`flex flex-col items-center justify-center text-center py-16 px-6 rounded-2xl border border-dashed border-gray-200 ${question ? "hidden" : ""
            }`}
          >
            <div className="w-16 h-16 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
              <Brain className="w-8 h-8" />
            </div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-2">Hazırsan başlayalım</h3>
            <p className="text-sm text-gray-500 max-w-md mb-6">
              Yapay zeka seviyene uygun matematik sorusu üretsin, birlikte çözelim ve adım adım açıklamasını dinleyelim.
            </p>
            <div className="flex items-center gap-4 text-sm mb-6">
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="radio"
                  name="apiSelect"
                  value="openai"
                  checked={selectedApi === "openai"}
                  onChange={(e) => setSelectedApi(e.target.value)} disabled={loadingQuestion}
                />
                OpenAI
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="radio"
                  name="apiSelect"
                  value="claude"
                  checked={selectedApi === "claude"}
                  onChange={(e) => setSelectedApi(e.target.value)} disabled={loadingQuestion}
                />
                Claude
              </label>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="radio"
                  name="apiSelect"
                  value="deepseek"
                  checked={selectedApi === "deepseek"}
                  onChange={(e) => setSelectedApi(e.target.value)} disabled={loadingQuestion}
                />
                DeepSeek
              </label>
            </div>

            <button
              onClick={() => {
                console.log('=== BUTTON CLICKED ===');
                console.log('onStart function:', onStart);
                console.log('loadingQuestion:', loadingQuestion);
                console.log('Calling onStart...');
                onStart();
              }}
              disabled={loadingQuestion}
              className="px-6 py-3 rounded-xl bg-blue-600 text-white font-semibold shadow hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {loadingQuestion && <Loader2 className="w-4 h-4 animate-spin" />}
              {loadingQuestion ? "Hazırlanıyor..." : "AI Sorusu Oluştur"}
            </button>
          </div>


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
                    onClick={handleExplainClick}
                    disabled={selectedOption === null || loadingExplanation}
                    className="flex items-center gap-2 px-5 py-3 rounded-xl bg-green-600 text-white font-semibold shadow hover:bg-green-700 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {loadingExplanation && <Loader2 className="w-4 h-4 animate-spin" />}
                    {loadingExplanation ? 'Açıklama Hazırlanıyor...' : 'Çözümü Göster'}
                  </button>
                  <button
                    onClick={handleNewQuestionClick}
                    disabled={loadingQuestion}
                    className="px-5 py-3 rounded-xl border border-gray-200 text-gray-700 font-semibold hover:bg-gray-100 disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {loadingQuestion && <Loader2 className="w-4 h-4 animate-spin" />}
                    {loadingQuestion ? 'Yeni Soru Hazırlanıyor...' : 'Yeni Soru'}
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

export default ExamPage;