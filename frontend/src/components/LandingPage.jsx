import React, { useState, useEffect } from 'react';
import {
  Brain,
  Target,
  Award,
  TrendingUp,
  BookOpen,
  Users,
  ChevronRight,
  Play,
  Star,
  CheckCircle,
  BarChart3,
  Clock,
  Zap,
  ArrowRight
} from 'lucide-react';

const LandingPage = ({ onStartDemo, onStartAssessment }) => {
  // Testimonials data
  const testimonials = [
    {
      name: "Ayşe Y.",
      role: "TYT Öğrencisi",
      content: "OSYM AI sayesinde matemematik puanım 35'ten 85'e çıktı!",
      rating: 5
    },
    {
      name: "Mehmet K.",
      role: "YKS Adayı",
      content: "Kişiselleştirilmiş sorular sayesinde zayıf konularımı tespit ettim.",
      rating: 5
    },
    {
      name: "Zeynep A.",
      role: "Öğretmen",
      content: "Öğrencilerimin gelişimini takip etmek çok kolaylaştı.",
      rating: 5
    }
  ];

  const [currentTestimonial, setCurrentTestimonial] = useState(0);

  // Testimonial auto-rotate
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 px-4 py-2 rounded-full text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              YKS 2025'ye Hazır mısın?
            </div>

            {/* Main Heading */}
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
                YKS Sınavına
              </span>
              <br />
              Akıllı Hazırlık
            </h1>

            {/* Subheading */}
            <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
              Yapay zeka destekli kişiselleştirilmiş sorularla çalış, seviyeni ölç,
              hedefine en hızlı yoldan ulaş. <span className="font-semibold text-blue-600">Ücretsiz başla!</span>
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
              <button
                onClick={onStartDemo}
                className="group relative inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-200"
              >
                <Play className="w-5 h-5" />
                Hemen Deneyin (Ücretsiz)
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>

              <button
                onClick={onStartAssessment}
                className="inline-flex items-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold text-lg border-2 border-blue-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-200"
              >
                <Target className="w-5 h-5" />
                Seviye Testi Yap
              </button>
            </div>

            {/* Trust Indicators */}
            <div className="flex flex-col sm:flex-row gap-8 justify-center items-center text-gray-600">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-600" />
                <span className="font-medium">10,000+ Öğrenci</span>
              </div>
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-500" />
                <span className="font-medium">4.9/5 Puan</span>
              </div>
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-green-600" />
                <span className="font-medium">Başarı Oranı +32%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Background Pattern */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-blue-200/20 to-indigo-200/20 rounded-full blur-3xl -z-10" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-indigo-200/20 to-purple-200/20 rounded-full blur-3xl -z-10" />
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Neden <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">OSYM AI?</span>
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Geleneksel yöntemlerin ötesinde, kişiselleştirilmiş öğrenme deneyimi
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, idx) => (
              <div key={idx} className="group relative">
                <div className="bg-gray-50 rounded-2xl p-8 h-full hover:shadow-lg transition-all duration-300 border border-gray-100 hover:border-blue-200">
                  <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                    <feature.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                  <div className="mt-4 flex items-center gap-2 text-blue-600 font-medium group-hover:text-blue-700">
                    <span className="text-sm">Daha fazla bilgi</span>
                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Assessment Section */}
      <section className="py-20 bg-gradient-to-br from-blue-600 to-indigo-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold mb-4">
              Zaman Yönetiminizi Test Edin
            </h2>
            <p className="text-xl text-blue-100 max-w-2xl mx-auto">
              Her soru 1 dakika! YKS sınavları gibi zamanla yarışan testlerle seviyenizi ve hızınızı ölçün
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {assessmentSteps.map((step, idx) => (
              <div key={idx} className="text-center">
                <div className="w-16 h-16 bg-white/20 backdrop-blur rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold">{idx + 1}</span>
                </div>
                <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                <p className="text-blue-100">{step.description}</p>
              </div>
            ))}
          </div>

          <div className="text-center">
            <button
              onClick={onStartAssessment}
              className="inline-flex items-center gap-3 bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold text-lg shadow-xl hover:shadow-2xl transform hover:-translate-y-1 transition-all duration-200"
            >
              <Clock className="w-6 h-6" />
              Zamanlı Testi Başla
            </button>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {stats.map((stat, idx) => (
              <div key={idx} className="text-center">
                <div className="text-4xl font-bold text-blue-600 mb-2">{stat.number}</div>
                <div className="text-gray-600 font-medium">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-gray-900 to-gray-800 text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold mb-6">
            Hazır mısın? <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">Hemen Başla!</span>
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            3 adımda YKS'ye hazır hale gelin. Ücretsiz deneyin, seviyenizi ölçün.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <button
              onClick={onStartDemo}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-8 py-4 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-200"
            >
              <Zap className="w-5 h-5" />
              Hemen Deneyin
            </button>
            <button
              onClick={onStartAssessment}
              className="inline-flex items-center gap-2 bg-white/10 backdrop-blur text-white px-8 py-4 rounded-xl font-semibold text-lg border border-white/20 hover:bg-white/20 transition-all duration-200"
            >
              <Target className="w-5 h-5" />
              Seviye Testi
            </button>
          </div>

          {/* Simple Steps */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="flex items-start gap-3 bg-white/10 backdrop-blur rounded-xl p-6">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold">1</span>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Ücretsiz Deneyin</h3>
                <p className="text-gray-300 text-sm">Kayıt olmadan sınırsız soru çözün</p>
              </div>
            </div>
            <div className="flex items-start gap-3 bg-white/10 backdrop-blur rounded-xl p-6">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold">2</span>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Seviyenizi Öğrün</h3>
                <p className="text-gray-300 text-sm">3 soruluk hızlı test ile</p>
              </div>
            </div>
            <div className="flex items-start gap-3 bg-white/10 backdrop-blur rounded-xl p-6">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-white font-bold">3</span>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Hedefinize Ulaşın</h3>
                <p className="text-gray-300 text-sm">Kişiselleştirilmiş çalışma</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Simple Testimonial Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Öğrenciler Ne Diyor?</h3>
            <p className="text-gray-600">OSYM AI ile hedeflerine ulaşan binlerce öğrenci</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.slice(0, 3).map((testimonial, idx) => (
              <div key={idx} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-600 italic mb-3">"{testimonial.content}"</p>
                <p className="text-sm font-medium text-gray-900">{testimonial.name}</p>
                <p className="text-xs text-gray-500">{testimonial.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

// Data
const features = [
  {
    icon: Brain,
    title: "AI Destekli Soru Üretimi",
    description: "Seviyenize ve eksiklerinize uygun, tamamen özgün sorular anında üretilir."
  },
  {
    icon: Target,
    title: "Kişiselleştirilmiş Öğrenme",
    description: "Performansınızı analiz eder ve zayıf yönlerinize odaklanan çalışma planı oluşturur."
  },
  {
    icon: Clock,
    title: "Zaman Yönetimi Analizi",
    description: "Her soru için 1 dakika, toplam 40 soruda 40 dakika. YKS'ye gerçek zamanlı hazırlık."
  },
  {
    icon: BarChart3,
    title: "Detaylı İlerleme Takibi",
    description: "Konu bazında, zaman içindeki gelişiminizi grafiklerle takip edin."
  },
  {
    icon: Award,
    title: "Sınav Stratejileri",
    description: "Zamanla yarışan YKS sınavları için özel teknikler ve stratejiler öğrenin."
  },
  {
    icon: TrendingUp,
    title: "Başarı Garantisi",
    description: "Binlerce öğrencinin başısıyla kanıtlanmış, etkili öğrenme metodu."
  }
];

const assessmentSteps = [
  {
    title: "Konu Seçimi",
    description: "Matematik, Fizik veya Kimya seçin"
  },
  {
    title: "Zamanlı Test",
    description: "Her soru 1 dakika, süre yönetimi ölçümü"
  },
  {
    title: "Zaman Analizi",
    description: "Hız ve doğruluk performansınız"
  }
];

const stats = [
  { number: "10,000+", label: "Mutlu Öğrenci" },
  { number: "32%", label: "Başarı Artışı" },
  { number: "50K+", label: "Üretilen Soru" },
  { number: "4.9/5", label: "Kullanıcı Puanı" }
];

export default LandingPage;