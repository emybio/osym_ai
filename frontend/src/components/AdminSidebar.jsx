import React from 'react';
import {
  PieChart,
  Upload,
  Database,
  Beaker,
  Settings,
  BarChart3,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const ADMIN_NAV_ITEMS = [
  { id: "admin-dashboard", label: "Sistem Paneli", icon: PieChart },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "database", label: "Veritabanı", icon: Database },
  { id: "ab_testing", label: "A/B Testing", icon: Beaker },
  { id: "upload", label: "PDF Yükle", icon: Upload },
];

const AdminSidebar = ({ currentPage, onNavigate, mobileMenuOpen, onToggleMobile, expandedSubmenu, onToggleSubmenu }) => {
  const { logout, user } = useAuth();

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transform transition-transform duration-300 ease-in-out ${mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
    >
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-purple-800 rounded-lg flex items-center justify-center text-white font-bold">
            ADM
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Admin Panel</h1>
            <p className="text-sm text-gray-500">Sistem Yönetimi</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Yönetim Araçları</p>
          <div className="space-y-1.5">
            {ADMIN_NAV_ITEMS.map((item) => {
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
                    className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${isActive ? "bg-purple-600 text-white" : "text-gray-600 hover:bg-gray-100"
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
                              ? "bg-purple-100 text-purple-700"
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
            <div className="px-4 py-2 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-purple-600" />
                <span>{user?.username || 'Admin Kullanıcı'}</span>
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
          </div>
        </div>

        <div className="p-4 bg-purple-50 border border-purple-100 rounded-xl">
          <div className="flex items-center gap-3 mb-3">
            <Settings className="w-10 h-10 text-purple-600" />
            <div>
              <p className="text-sm font-semibold text-purple-900">Yönetici İpucu</p>
              <p className="text-xs text-purple-700">Sistem performansını düzenli kontrol edin.</p>
            </div>
          </div>
        </div>
      </nav>

      <div className="p-4 border-t border-gray-200">
        {user ? (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
              <Settings className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{user.username}</p>
              <p className="text-xs text-purple-600">Sistem Yöneticisi</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
              <Settings className="w-5 h-5 text-gray-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Admin Kullanıcı</p>
              <p className="text-xs text-gray-500">Sistem Yönetimi</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default AdminSidebar;