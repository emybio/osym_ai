import React, { useState } from 'react';
import {
  Clock,
  Menu,
  User,
  X,
} from 'lucide-react';

// Components
import Sidebar from './components/Sidebar';
import HomePage from './components/HomePage';
import DashboardPage from './components/DashboardPage';
import ExamPage from './components/ExamPage';
import ProgressPage from './components/ProgressPage';
import SubjectsPage from './components/SubjectsPage';

// Hooks
import { useExamState } from './hooks/useExamState';

const App = () => {
  // Navigation state
  const [currentPage, setCurrentPage] = useState('home');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [expandedSubmenu, setExpandedSubmenu] = useState(null);

  // Navigation handler with submenu reset
  const handleNavigate = (page) => {
    setCurrentPage(page);
    // Reset submenu when navigating to main items
    if (!['progress-overview', 'subjects'].includes(page)) {
      setExpandedSubmenu(null);
    }
    setMobileMenuOpen(false);
  };

  // Exam state
  const examState = useExamState();

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
        </main>
      </div>
    </div>
  );
};

export default App;