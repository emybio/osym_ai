import React, { useState } from 'react';
import {
  Clock,
  Menu,
  User,
  X,
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
import AnimatedTransition from './components/AnimatedTransition';
import LoadingOverlay from './components/LoadingOverlay';

// Hooks
import { useExamState } from './hooks/useExamState';

const App = () => {
  // Navigation state
  const [currentPage, setCurrentPage] = useState('landing');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);
  const [showLanding, setShowLanding] = useState(true);
  const [isPageLoading, setIsPageLoading] = useState(false);

  // Navigation handler with submenu reset
  const handleNavigate = (page) => {
    setIsPageLoading(true);

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

  // Exam state
  const examState = useExamState();

  // Show landing page for first-time visitors
  if (showLanding && currentPage === 'landing') {
    return <AnimatedTransition><LandingPage onStartDemo={handleStartDemo} onStartAssessment={handleStartAssessment} /></AnimatedTransition>;
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
        </main>
      </div>

      {/* Global Loading Overlay */}
      <LoadingOverlay
        show={isPageLoading}
        text="Yükleniyor..."
        size="medium"
      />
    </div>
  );
};

export default App;