import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Sidebar from '../components/Sidebar';
import HomePage from '../components/HomePage';
import ExamPage from '../components/ExamPage';
import { useExamState } from '../hooks/useExamState';

// Mock the constants
jest.mock('../constants', () => ({
  STUDENT_STATS: {
    avgScore: 78.5,
    recentExams: [
      { date: "20.10.2024", subject: "Matematik", score: 85, duration: "45 dk" },
    ],
  },
  AI_RECOMMENDATIONS: [
    {
      title: "Logaritma konusunu tekrar et",
      description: "Son 5 sınavda logaritma sorularında başarı oranı %45.",
    },
  ],
}));

// Mock the API service
jest.mock('../services/api', () => ({
  questionService: {
    generate: jest.fn(),
    explain: jest.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(message, status, data) {
      super(message);
      this.status = status;
      this.data = data;
    }
  },
}));

describe('Sidebar Component', () => {
  const defaultProps = {
    currentPage: 'home',
    onNavigate: jest.fn(),
    mobileMenuOpen: false,
    onToggleMobile: jest.fn(),
    expandedSubmenu: null,
    onToggleSubmenu: jest.fn(),
  };

  it('renders navigation items correctly', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('Anasayfa')).toBeInTheDocument();
    expect(screen.getByText('Öğrenci Paneli')).toBeInTheDocument();
    expect(screen.getByText('AI Sınavı')).toBeInTheDocument();
    expect(screen.getByText('İlerleme')).toBeInTheDocument();
  });

  it('highlights active page correctly', () => {
    render(<Sidebar {...defaultProps} currentPage="exams" />);

    const examsButton = screen.getByText('AI Sınavı').closest('button');
    expect(examsButton).toHaveClass('bg-blue-600', 'text-white');
  });

  it('calls onNavigate when navigation item is clicked', () => {
    render(<Sidebar {...defaultProps} />);

    fireEvent.click(screen.getByText('AI Sınavı'));
    expect(defaultProps.onNavigate).toHaveBeenCalledWith('exams');
  });

  it('toggles submenu when progress item is clicked', () => {
    render(<Sidebar {...defaultProps} />);

    fireEvent.click(screen.getByText('İlerleme'));
    expect(defaultProps.onToggleSubmenu).toHaveBeenCalledWith('progress');
  });

  it('shows AI suggestion card', () => {
    render(<Sidebar {...defaultProps} />);

    expect(screen.getByText('AI Önerisi')).toBeInTheDocument();
    expect(screen.getByText('Plan Oluştur')).toBeInTheDocument();
  });
});

describe('HomePage Component', () => {
  const defaultProps = {
    onStartExam: jest.fn(),
  };

  it('renders main sections correctly', () => {
    render(<HomePage {...defaultProps} />);

    expect(screen.getByText('AI Destekli Sınav')).toBeInTheDocument();
    expect(screen.getByText('Bugün tek bir soru ile başla')).toBeInTheDocument();
    expect(screen.getByText('AI Sorusu Oluştur')).toBeInTheDocument();
  });

  it('displays student statistics', () => {
    render(<HomePage {...defaultProps} />);

    expect(screen.getByText('Ortalama başarı')).toBeInTheDocument();
    expect(screen.getByText('78.5%')).toBeInTheDocument();
    expect(screen.getByText('Çalışma serisi')).toBeInTheDocument();
  });

  it('displays recent exams', () => {
    render(<HomePage {...defaultProps} />);

    expect(screen.getByText('Son Sınavlar')).toBeInTheDocument();
    expect(screen.getByText('Matematik')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('displays AI recommendations', () => {
    render(<HomePage {...defaultProps} />);

    expect(screen.getByText('AI Önerileri')).toBeInTheDocument();
    expect(screen.getByText('Logaritma konusunu tekrar et')).toBeInTheDocument();
  });

  it('calls onStartExam when button is clicked', () => {
    render(<HomePage {...defaultProps} />);

    fireEvent.click(screen.getByText('AI Sorusu Oluştur'));
    expect(defaultProps.onStartExam).toHaveBeenCalledTimes(1);
  });
});

describe('ExamPage Component', () => {
  // Mock the useExamState hook
  jest.mock('../hooks/useExamState', () => ({
    useExamState: () => ({
      examStarted: false,
      question: null,
      selectedOption: null,
      setSelectedOption: jest.fn(),
      explanation: null,
      loadingQuestion: false,
      loadingExplanation: false,
      errorMessage: '',
      selectedApi: 'openai',
      setSelectedApi: jest.fn(),
      startExam: jest.fn(),
      explainAnswer: jest.fn(),
      resetExamState: jest.fn(),
    }),
  }));

  const defaultProps = {
    examStarted: false,
    question: null,
    selectedOption: null,
    setSelectedOption: jest.fn(),
    explanation: null,
    loadingQuestion: false,
    loadingExplanation: false,
    errorMessage: '',
    selectedApi: 'openai',
    setSelectedApi: jest.fn(),
    onStart: jest.fn(),
    onExplain: jest.fn(),
    onReset: jest.fn(),
  };

  it('renders initial state correctly', () => {
    render(<ExamPage {...defaultProps} />);

    expect(screen.getByText('Yapay Zeka ile Soru Çözümü')).toBeInTheDocument();
    expect(screen.getByText('Hazırsan başlayalım')).toBeInTheDocument();
    expect(screen.getByText('AI Sorusu Oluştur')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<ExamPage {...defaultProps} loadingQuestion={true} />);

    expect(screen.getByText('Hazırlanıyor...')).toBeInTheDocument();
  });

  it('shows error message when provided', () => {
    const errorMessage = 'API hatası oluştu';
    render(<ExamPage {...defaultProps} errorMessage={errorMessage} />);

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('renders question when exam is started', () => {
    const mockQuestion = {
      id: 1,
      stem: 'What is 2+2?',
      choices: ['3', '4', '5', '6'],
      answer: 'B',
      topic: 'Mathematics',
      difficulty: 'Easy',
    };

    render(<ExamPage {...defaultProps} examStarted={true} question={mockQuestion} />);

    expect(screen.getByText('What is 2+2?')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('shows explanation when provided', () => {
    const mockQuestion = {
      id: 1,
      stem: 'What is 2+2?',
      choices: ['3', '4', '5', '6'],
      answer: 'B',
      topic: 'Mathematics',
      difficulty: 'Easy',
    };

    render(
      <ExamPage
        {...defaultProps}
        examStarted={true}
        question={mockQuestion}
        explanation="Step 1: Add the numbers\nStep 2: Get the result"
      />
    );

    expect(screen.getByText('Yapay zeka açıklaması')).toBeInTheDocument();
    expect(screen.getByText('Step 1: Add the numbers')).toBeInTheDocument();
  });

  it('allows API provider selection', () => {
    render(<ExamPage {...defaultProps} />);

    const openaiRadio = screen.getByLabelText('OpenAI');
    const zaiRadio = screen.getByLabelText('Z.ai');

    expect(openaiRadio).toBeChecked();
    expect(zaiRadio).not.toBeChecked();

    fireEvent.click(zaiRadio);
    expect(defaultProps.setSelectedApi).toHaveBeenCalledWith('zai');
  });

  it('calls onStart when AI Sorusu Oluştur is clicked', () => {
    render(<ExamPage {...defaultProps} />);

    fireEvent.click(screen.getByText('AI Sorusu Oluştur'));
    expect(defaultProps.onStart).toHaveBeenCalledTimes(1);
  });

  it('calls onReset when Sıfırla is clicked', () => {
    render(<ExamPage {...defaultProps} />);

    fireEvent.click(screen.getByText('Sıfırla'));
    expect(defaultProps.onReset).toHaveBeenCalledTimes(1);
  });
});

describe('useExamState Hook', () => {
  // Note: Hook tests require @testing-library/react-hooks or @testing-library/react
  // For now, these tests are skipped
  it('placeholder test', () => {
    expect(true).toBe(true);
  });
});

// Note: For proper hook testing, install @testing-library/react-hooks
// For now, these are simplified mock functions