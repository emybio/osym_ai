import React from 'react';
import {
  Brain,
  ChevronDown,
  ChevronRight,
  User,
  BookOpen,
  BarChart3,
  FileText,
  Home,
  TrendingUp,
  Shield,
  Upload,
  LogOut,
  PieChart,
  Database,
  Beaker,
  Zap,
  Target,
  Clock,
  Award,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const STUDENT_NAV_ITEMS = [
  { id: "home", label: "Anasayfa", icon: Home },
  { id: "student-dashboard", label: "Öğrenci Paneli", icon: BarChart3 },
  { id: "exams", label: "AI Sınavı", icon: FileText },
  { id: "questions", label: "Sorular", icon: BookOpen },
  {
    id: "progress",
    label: "İlerleme",
    icon: TrendingUp,
    submenu: [
      { id: "progress-overview", label: "Genel Bakış" },
      { id: "subjects", label: "Dersler" }
    ]
  },
  { id: "quicktest", label: "Hızlı Test", icon: Target },
  { id: "results", label: "Sonuçlar", icon: Award },
];

const StudentSidebar = ({ currentPage, onNavigate, mobileMenuOpen, onToggleMobile, expandedSubmenu, onToggleSubmenu }) => {
  const { logout, user } = useAuth();

  return (
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
          <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Öğrenci Araçları</p>
          <div className="space-y-1.5">
            {STUDENT_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id || (item.submenu && expandedSubmenu === item.id) ||
                (item.submenu && item.submenu.some(sub => currentPage === sub.id));
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

        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Hesap</p>
          <div className="space-y-1.5">
            {user ? (
              <>
                <div className="px-4 py-2 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-600" />
                    <span>{user.username}</span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    logout();
                    if (mobileMenuOpen) onToggleMobile(false);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="flex-1 text-left">Çıkış Yap</span>
                </button>
              </>
            ) : (
              <div className="px-4 py-2 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-green-600" />
                  <span>Ziyaretçi Modu</span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <Brain className="w-10 h-10 text-blue-600" />
            <div>
              <p className="text-sm font-semibold text-blue-900">AI Önerisi</p>
              <p className="text-xs text-blue-700">Çalışma planınızı kişiselleştirin.</p>
            </div>
          </div>
          <button className="w-full py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
            Plan Oluştur
          </button>
        </div>
      </nav>

      <div className="p-4 border-t border-gray-200">
        {user ? (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{user.username || 'Öğrenci'}</p>
              <p className="text-xs text-blue-600">Aktif Kullanıcı</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
              <User className="w-5 h-5 text-gray-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Zeynep Arslan</p>
              <p className="text-xs text-gray-500">TYT Adayı</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default StudentSidebar;