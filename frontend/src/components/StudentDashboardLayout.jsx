import React, { useState, useEffect } from 'react';
import {
  Menu,
  X,
  User,
  Clock,
} from 'lucide-react';
import { apiCall } from '../config/api';
import StudentSidebar from './StudentSidebar';
import StudentDashboardPage from './StudentDashboardPage';
import HomePage from './HomePage';
import ExamPage from './ExamPage';
import ProgressPage from './ProgressPage';
import SubjectsPage from './SubjectsPage';
import QuestionsPage from './QuestionsPage';
import AssessmentPage from './AssessmentPage';
import LoginPage from './LoginPage';
import QuickTestPage from './QuickTestPage';
import QuickTestExam from './QuickTestExam';
import QuickTestResults from './QuickTestResults';
import { useAuth } from '../contexts/AuthContext';
import { useExamState } from '../hooks/useExamState';

const StudentDashboardLayout = () => {
  const { isAuthenticated, isAdmin, loading, logout } = useAuth();
  const [currentPage, setCurrentPage] = useState('student-dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);
  const [showLanding, setShowLanding] = useState(true);
  const [isPageLoading, setIsPageLoading] = useState(false);

  // Quick test state
  const [quickTestSession, setQuickTestSession] = useState(null);
  const [quickTestResults, setQuickTestResults] = useState(null);

  // Exam state
  const examState = useExamState();

  // Handle URL-based navigation
  useEffect(() => {
    const handleRoute = () => {
      const path = window.location.pathname;
      if (path === '/student-dashboard') {
        setCurrentPage('student-dashboard');
        setShowLanding(false);
      } else if (path === '/quicktest-start') {
        setCurrentPage('quicktest-start');
        setShowLanding(false);
      } else if (path === '/quicktest-exam') {
        setCurrentPage('quicktest-exam');
        setShowLanding(false);
      } else if (path === '/quicktest-results') {
        setCurrentPage('quicktest-results');
        setShowLanding(false);
      } else if (path === '/assessment') {
        setCurrentPage('assessment');
        setShowLanding(false);
      } else if (path === '/login') {
        setCurrentPage('login');
        setShowLanding(true);
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
    if (page === 'student-dashboard') {
      window.history.pushState({}, '', '/student-dashboard');
    } else if (page === 'quicktest-start') {
      window.history.pushState({}, '', '/quicktest-start');
    } else if (page === 'quicktest-exam') {
      window.history.pushState({}, '', '/quicktest-exam');
    } else if (page === 'quicktest-results') {
      window.history.pushState({}, '', '/quicktest-results');
    } else if (page === 'assessment') {
      window.history.pushState({}, '', '/assessment');
    } else if (page === 'login') {
      window.history.pushState({}, '', '/login');
    } else if (page === 'home') {
      window.history.pushState({}, '', '/');
    }

    setTimeout(() => {
      setCurrentPage(page);
      // If navigating to main app, hide landing page
      if (['student-dashboard', 'exams', 'progress', 'subjects', 'questions', 'quicktest-start'].includes(page)) {
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
      throw error;
    } finally {
      setIsPageLoading(false);
    }
  };

  const handleQuickTestComplete = (results) => {
    console.log('🔍 handleQuickTestComplete - received results:', results);
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
    setCurrentPage('student-dashboard');
    setShowLanding(true);
  };

  const handleAssessmentComplete = (results) => {
    console.log('Assessment completed:', results);
    handleNavigate('student-dashboard');
  };

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

  // Show login page for non-authenticated users
  if (!isAuthenticated || currentPage === 'login') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoginPage
          onLoginSuccess={() => {
            handleNavigate('student-dashboard');
            setShowLanding(false);
          }}
        />
      </div>
    );
  }

  // Show landing page for first-time visitors
  if (showLanding && currentPage === 'student-dashboard') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <HomePage
          onStartExam={() => {
            handleNavigate('exams');
            examState.startExam();
          }}
        />
      </div>
    );
  }

  // Show assessment page
  if (currentPage === 'assessment') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <AssessmentPage
          onComplete={handleAssessmentComplete}
          onBack={() => {
            setShowLanding(true);
            setCurrentPage('student-dashboard');
          }}
        />
      </div>
    );
  }

  // Show quick test start page
  if (currentPage === 'quicktest-start') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <QuickTestPage
          onStartQuickTest={handleQuickTestConfig}
          onBack={handleQuickTestBackToLanding}
        />
      </div>
    );
  }

  // Show quick test exam page
  if (currentPage === 'quicktest-exam' && quickTestSession) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <QuickTestExam
          sessionData={quickTestSession}
          onComplete={handleQuickTestComplete}
          onBack={handleQuickTestBackToLanding}
        />
      </div>
    );
  }

  // Show quick test results page
  if (currentPage === 'quicktest-results' && quickTestResults) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <QuickTestResults
          resultData={quickTestResults}
          onStartNewTest={handleQuickTestNewTest}
        />
      </div>
    );
  }

  // Main student layout
  return (
    <div className="min-h-screen bg-gray-50 lg:pl-64">
      <StudentSidebar
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
          {currentPage === 'student-dashboard' && <StudentDashboardPage />}
          {currentPage === 'exams' && <ExamPage {...examState} />}
          {currentPage === 'progress' && <ProgressPage />}
          {currentPage === 'progress-overview' && <ProgressPage />}
          {currentPage === 'subjects' && <SubjectsPage />}
          {currentPage === 'questions' && <QuestionsPage />}
        </main>
      </div>

      {/* Global Loading Overlay */}
      {isPageLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-white">Yükleniyor...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboardLayout;