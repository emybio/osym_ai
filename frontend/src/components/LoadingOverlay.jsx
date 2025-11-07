import React from 'react';
import LoadingSpinner from './LoadingSpinner';

const LoadingOverlay = ({
  show = false,
  text = 'Yükleniyor...',
  size = 'large',
  backdrop = true
}) => {
  if (!show) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${
      backdrop ? 'bg-black bg-opacity-40' : 'bg-transparent'
    } backdrop-blur-sm`}>
      <div className="bg-white rounded-2xl p-8 shadow-2xl">
        <LoadingSpinner size={size} text={text} className="min-w-[200px]" />
      </div>
    </div>
  );
};

export default LoadingOverlay;