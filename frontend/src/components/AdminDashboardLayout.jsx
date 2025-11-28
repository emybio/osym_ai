import React, { useState, useEffect } from 'react';
import {
  Menu,
  X,
  User,
  Settings,
} from 'lucide-react';
import AdminSidebar from './AdminSidebar';
import AdminDashboardPage from './AdminDashboardPage';
import AnalyticsPage from './AnalyticsPage';
import DatabaseStatusPage from './DatabaseStatusPage';
import ABTestingPage from './ABTestingPage';
import PDFUploadPage from './PDFUploadPage';
import { useAuth } from '../contexts/AuthContext';

const AdminDashboardLayout = ({ initialPage = 'admin-dashboard' }) => {
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);
  const { logout } = useAuth();

  // Handle URL-based navigation
  useEffect(() => {
    const handleRoute = () => {
      const path = window.location.pathname;
      if (path.startsWith('/admin/')) {
        const page = path.replace('/admin/', '') || 'dashboard';
        setCurrentPage(page);
      }
    };

    handleRoute();
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, []);

  // Navigation handler
  const handleNavigate = (page) => {
    setIsPageLoading(true);

    // Update URL
    if (page.startsWith('admin-')) {
      const pageId = page.replace('admin-', '');
      window.history.pushState({}, '', `/admin/${pageId}`);
    } else if (page === 'login') {
      window.history.pushState({}, '', '/login');
    } else {
      window.history.pushState({}, '', `/admin/${page}`);
    }

    setTimeout(() => {
      setCurrentPage(page);
      setMobileMenuOpen(false);
      setIsPageLoading(false);
    }, 300);
  };

  // Quick state for loading
  const [isPageLoading, setIsPageLoading] = useState(false);

  // Show loading while checking auth
  if (isPageLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Main admin layout
  return (
    <div className="min-h-screen bg-gray-50 lg:pl-64">
      <AdminSidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobile={setMobileMenuOpen}
        expandedSubmenu={expandedSubmenu}
        onToggleSubmenu={setExpandedSubmenu}
      />

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-40 z-30 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <div>
        <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
          <div className="p-4 max-w-5xl mx-auto w-full px-4 md:px-6 py-4 flex items-center justify-between gap-4">
            <button
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg border border-gray-200 text-gray-600"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <Settings className="w-4 h-4 text-purple-600" />
              <span>Admin Dashboard</span>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <User className="w-4 h-4 text-gray-500" />
              <span>Sistem Yöneticisi</span>
            </div>
          </div>
        </header>

        <main className="max-w-5xl mx-auto w-full px-4 md:px-6 py-8 space-y-8">
          {currentPage === 'dashboard' && <AdminDashboardPage />}
          {currentPage === 'analytics' && <AnalyticsPage />}
          {currentPage === 'database' && <DatabaseStatusPage />}
          {currentPage === 'ab_testing' && <ABTestingPage />}
          {currentPage === 'upload' && (
            <PDFUploadPage
              onLogout={() => {
                logout();
                window.history.pushState({}, '', '/login');
                setCurrentPage('login');
              }}
            />
          )}
          {currentPage === 'admin-dashboard' && <AdminDashboardPage />}
          {currentPage === 'settings' && (
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Sistem Ayarları</h2>
              <p className="text-gray-500">Sistem ayarları ve yapılandırma burada yer alacak.</p>
            </div>
          )}
        </main>
      </div>

      {/* Global Loading Overlay */}
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 hidden">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white">Yükleniyor...</p>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardLayout;