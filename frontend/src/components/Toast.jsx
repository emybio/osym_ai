import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertCircle, X, Info } from 'lucide-react';

const Toast = ({
  message,
  type = 'info', // success, error, warning, info
  duration = 5000,
  onClose,
  show = true
}) => {
  const [isVisible, setIsVisible] = useState(show);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (show) {
      setIsVisible(true);
      // Giriş animasyonu için küçük delay
      setTimeout(() => setIsAnimating(true), 10);

      if (duration > 0) {
        const timer = setTimeout(() => {
          handleClose();
        }, duration);

        return () => clearTimeout(timer);
      }
    }
  }, [show, duration]);

  const handleClose = () => {
    setIsAnimating(false);
    // Çıkış animasyonu bitince component'i kaldır
    setTimeout(() => {
      setIsVisible(false);
      onClose?.();
    }, 300);
  };

  if (!isVisible) return null;

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-600" />,
    error: <XCircle className="w-5 h-5 text-red-600" />,
    warning: <AlertCircle className="w-5 h-5 text-amber-600" />,
    info: <Info className="w-5 h-5 text-blue-600" />
  };

  const bgColors = {
    success: 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200',
    error: 'bg-gradient-to-r from-red-50 to-rose-50 border-red-200',
    warning: 'bg-gradient-to-r from-amber-50 to-yellow-50 border-amber-200',
    info: 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200'
  };

  const progressColors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-amber-500',
    info: 'bg-blue-500'
  };

  return (
    <div
      className={`
        fixed top-4 right-4 z-[99999] max-w-sm sm:max-w-md
        transform transition-all duration-300 ease-out
        ${isAnimating
          ? 'translate-x-0 opacity-100 scale-100'
          : 'translate-x-full opacity-0 scale-95'
        }
      `}
    >
      <div className={`
        p-4 rounded-xl border shadow-xl backdrop-blur-sm
        ${bgColors[type]}
        transition-all duration-300
      `}
      >
        {/* Progress Bar */}
        {false && duration > 0 && (
          <div className="absolute top-0 left-0 right-0 h-1 rounded-t-xl overflow-hidden">
            <div
              className={`
                h-full ${progressColors[type]} transition-all ease-linear
              `}
              style={{
                animation: `shrink ${duration}ms linear forwards`
              }}
            />
          </div>
        )}

        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            {icons[type]}
          </div>

          <p className="text-sm text-gray-800 font-medium flex-1 leading-relaxed">
            {message}
          </p>

          <button
            onClick={handleClose}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-all hover:scale-110 p-1 rounded-md hover:bg-gray-100/50"
            title="Kapat"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Animasyon styles */}
      <style>{`
        @keyframes shrink {
          from { width: 100%; }
          to { width: 0%; }
        }
      `}</style>
    </div>
  );
};

// Global Toast Context
export const ToastContext = React.createContext();

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = React.useState([]);

  const addToast = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    const newToast = { id, message, type, duration, show: true };

    setToasts(prev => [...prev, newToast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const success = (message, duration) => addToast(message, 'success', duration);
  const error = (message, duration) => addToast(message, 'error', duration);
  const warning = (message, duration) => addToast(message, 'warning', duration);
  const info = (message, duration) => addToast(message, 'info', duration);

  return (
    <ToastContext.Provider value={{
      toasts,
      addToast,
      removeToast,
      success,
      error,
      warning,
      info
    }}>
      {children}
      {/* Toast'ları burada render et */}
      {toasts.map((toastItem) => (
        <Toast
          key={toastItem.id}
          message={toastItem.message}
          type={toastItem.type}
          duration={0} // Manuel kontrol
          onClose={() => removeToast(toastItem.id)}
          show={toastItem.show}
        />
      ))}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

export default Toast;