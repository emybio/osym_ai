import React, { useState, useEffect } from 'react';
import {
  Clock,
  Menu,
  User,
  X,
  Shield,
  Upload
} from 'lucide-react';

// Components
import Sidebar from './components/Sidebar';
import LandingPage from './components/LandingPage';
import HomePage from './components/HomePage';
import DashboardPage from './components/DashboardPage';
import ExamPage from './components/ExamPage';
import ProgressPage from './components/ProgressPage';
import SubjectsPage from './components/SubjectsPage';
import QuestionsPage from './components/QuestionsPage';
import AssessmentPage from './components/AssessmentPage';
import LoginPage from './components/LoginPage';
import PDFUploadPage from './components/PDFUploadPage';
import QuickTestPage from './components/QuickTestPage';
import QuickTestExam from './components/QuickTestExam';
import QuickTestResults from './components/QuickTestResults';
import AnalyticsPage from './components/AnalyticsPage';
import DatabaseStatusPage from './components/DatabaseStatusPage';
import ABTestingPage from './components/ABTestingPage';
import Toast, { ToastProvider, useToast } from './components/Toast';
import AnimatedTransition from './components/AnimatedTransition';
import LoadingOverlay from './components/LoadingOverlay';
import OfflineStatus from './components/OfflineStatus';

// Context
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Hooks
import { useExamState } from './hooks/useExamState';

// API Configuration
import { apiCall } from './config/api';

// Inner App component that uses auth context
const AppContent = () => {
  const { isAuthenticated, isAdmin, loading, logout } = useAuth();

  
  // Navigation state
  const [currentPage, setCurrentPage] = useState('landing');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);
  const [showLanding, setShowLanding] = useState(true);
  const [isPageLoading, setIsPageLoading] = useState(false);

  // Quick test state
  const [quickTestSession, setQuickTestSession] = useState(null);
  const [quickTestResults, setQuickTestResults] = useState(null);

  // Handle URL-based navigation
  useEffect(() => {
    const handleRoute = () => {
      const path = window.location.pathname;
      if (path === '/login') {
        setCurrentPage('login');
        setShowLanding(false);
      } else if (path === '/upload') {
        setCurrentPage('upload');
        setShowLanding(false);
      } else if (path === '/') {
        setCurrentPage('landing');
      }
    };

    handleRoute();
    window.addEventListener('popstate', handleRoute);
    return () => window.removeEventListener('popstate', handleRoute);
  }, []);

  // Navigation handler with submenu reset
  const handleNavigate = (page) => {
    setIsPageLoading(true);

    // Update URL
    if (page === 'login') {
      window.history.pushState({}, '', '/login');
    } else if (page === 'upload') {
      window.history.pushState({}, '', '/upload');
    } else if (page === 'landing') {
      window.history.pushState({}, '', '/');
    }

    setTimeout(() => {
      setCurrentPage(page);
      // If navigating to main app, hide landing page
      if (['dashboard', 'exams', 'progress', 'subjects', 'questions'].includes(page)) {
        setShowLanding(false);
      }
      // Reset submenu when navigating to main items
      if (!['progress-overview', 'subjects'].includes(page)) {
        setExpandedSubmenu(null);
      }
      setMobileMenuOpen(false);
      setIsPageLoading(false);
    }, 300);
  };

  // Landing page handlers
  const handleStartDemo = () => {
    setShowLanding(false);
    handleNavigate('home');
  };

  const handleStartAssessment = () => {
    setShowLanding(true);
    setCurrentPage('assessment');
  };

  const handleAssessmentComplete = (results) => {
    console.log('Assessment completed:', results);
    handleNavigate('home');
  };

  // Quick test handlers
  const handleStartQuickTest = () => {
    setShowLanding(false);
    setCurrentPage('quicktest-start');
  };

  const handleQuickTestConfig = async (config) => {
    setIsPageLoading(true);
    try {
      const session = await apiCall('/quicktest/init/', {
        method: 'POST',
        body: JSON.stringify(config),
      });

      setQuickTestSession(session);
      setCurrentPage('quicktest-exam');

    } catch (error) {
      console.error('Error starting quick test:', error);
      setIsPageLoading(false);
      // Error'ı yukarı at ki QuickTestPage handle edebilsin
      throw error;
    } finally {
      setIsPageLoading(false);
    }
  };

  const handleQuickTestComplete = (results) => {
    setQuickTestResults(results);
    setCurrentPage('quicktest-results');
  };

  const handleQuickTestNewTest = () => {
    setQuickTestSession(null);
    setQuickTestResults(null);
    setCurrentPage('quicktest-start');
  };

  const handleQuickTestBackToLanding = () => {
    setQuickTestSession(null);
    setQuickTestResults(null);
    setCurrentPage('landing');
    setShowLanding(true);
  };

  const handleCreateAccountSuccess = (userData) => {
    console.log('Account created:', userData);
    // Redirect to main app after successful registration
    setShowLanding(false);
    setCurrentPage('dashboard');
    setQuickTestSession(null);
    setQuickTestResults(null);
  };

  // Exam state
  const examState = useExamState();

  // Show loading while checking auth
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Show login page for admin routes
  if (currentPage === 'login') {
    return (
      <AnimatedTransition>
        <LoginPage
          onLoginSuccess={() => {
            // SPA-style login success
            window.history.pushState({}, '', '/upload');
            setCurrentPage('upload');
            setShowLanding(false);
          }}
        />
      </AnimatedTransition>
    );
  }

  // Show upload page (protected)
  if (currentPage === 'upload') {
    return (
      <PDFUploadPage
        onLogout={() => {
          // SPA-style logout: update URL without page reload
          window.history.pushState({}, '', '/login');
          setCurrentPage('login');
          setShowLanding(false);
        }}
      />
    );
  }

  // Show landing page for first-time visitors
  if (showLanding && currentPage === 'landing') {
    return (
      <AnimatedTransition>
        <LandingPage
          onStartDemo={handleStartDemo}
          onStartAssessment={handleStartAssessment}
          onStartQuickTest={handleStartQuickTest}
        />
      </AnimatedTransition>
    );
  }

  // Show assessment page
  if (currentPage === 'assessment') {
    return (
      <AnimatedTransition>
        <AssessmentPage
          onComplete={handleAssessmentComplete}
          onBack={() => {
            setShowLanding(true);
            setCurrentPage('landing');
          }}
        />
      </AnimatedTransition>
    );
  }

  // Show quick test start page
  if (currentPage === 'quicktest-start') {
    return (
      <AnimatedTransition>
        <QuickTestPage
          onStartQuickTest={handleQuickTestConfig}
          onBack={handleQuickTestBackToLanding}
        />
      </AnimatedTransition>
    );
  }

  // Show quick test exam page
  if (currentPage === 'quicktest-exam' && quickTestSession) {
    return (
      <AnimatedTransition>
        <QuickTestExam
          sessionData={quickTestSession}
          onComplete={handleQuickTestComplete}
          onBack={handleQuickTestBackToLanding}
        />
      </AnimatedTransition>
    );
  }

  // Show quick test results page
  if (currentPage === 'quicktest-results' && quickTestResults) {
    return (
      <AnimatedTransition>
        <QuickTestResults
          resultData={quickTestResults}
          onStartNewTest={handleQuickTestNewTest}
          onCreateAccount={handleCreateAccountSuccess}
        />
      </AnimatedTransition>
    );
  }

  // Main app layout
  return (
    <div className="min-h-screen bg-gray-50 lg:pl-64">
      <Sidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobile={setMobileMenuOpen}
        expandedSubmenu={expandedSubmenu}
        onToggleSubmenu={setExpandedSubmenu}
        isAuthenticated={isAuthenticated}
        isAdmin={isAdmin}
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
          {currentPage === 'home' && <HomePage onStartExam={() => { handleNavigate('exams'); examState.startExam(); }} />}
          {currentPage === 'dashboard' && <DashboardPage />}
          {currentPage === 'exams' && <ExamPage {...examState} />}
          {currentPage === 'progress' && <ProgressPage />}
          {currentPage === 'progress-overview' && <ProgressPage />}
          {currentPage === 'subjects' && <SubjectsPage />}
          {currentPage === 'questions' && <QuestionsPage />}
          {currentPage === 'analytics' && <AnalyticsPage />}
          {currentPage === 'database' && <DatabaseStatusPage />}
          {currentPage === 'ab_testing' && <ABTestingPage />}
        </main>
      </div>

      {/* Global Loading Overlay */}
      <LoadingOverlay
        show={isPageLoading}
        text="Yükleniyor..."
        size="medium"
      />

      {/* Offline Status Component */}
      <OfflineStatus />

      </div>
  );
};

// Main App component with AuthProvider
const App = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;