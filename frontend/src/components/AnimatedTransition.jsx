import React, { useEffect, useRef } from 'react';

const AnimatedTransition = ({ children, className = '', delay = 0 }) => {
  const elementRef = useRef(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (elementRef.current) {
      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Start animation after delay
      timeoutRef.current = setTimeout(() => {
        if (elementRef.current) {
          elementRef.current.style.opacity = '1';
          elementRef.current.style.transform = 'translateY(0)';
        }
      }, delay);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [delay]);

  return (
    <div
      ref={elementRef}
      className={`${className} page-transition`}
      style={{
        opacity: '0',
        transform: 'translateY(20px)',
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
      }}
    >
      {children}
    </div>
  );
};

export default AnimatedTransition;