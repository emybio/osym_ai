import React from 'react';

const SkeletonLoader = ({
  type = 'card',
  count = 1,
  className = ''
}) => {
  const shimmer = 'animate-pulse bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%]';

  const CardSkeleton = () => (
    <div className={`bg-white rounded-xl p-6 border border-gray-200 ${className}`}>
      <div className={`h-4 ${shimmer} rounded mb-4 w-3/4`} />
      <div className={`h-3 ${shimmer} rounded mb-2 w-full`} />
      <div className={`h-3 ${shimmer} rounded mb-2 w-5/6`} />
      <div className={`h-3 ${shimmer} rounded w-4/6`} />
    </div>
  );

  const QuestionSkeleton = () => (
    <div className={`bg-white rounded-xl p-8 border border-gray-200 ${className}`}>
      <div className={`h-6 ${shimmer} rounded mb-6 w-2/3`} />
      <div className="space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`h-12 ${shimmer} rounded-lg`} />
        ))}
      </div>
    </div>
  );

  const SubjectSkeleton = () => (
    <div className={`bg-white rounded-2xl p-8 border-2 border-gray-200 ${className}`}>
      <div className={`h-12 ${shimmer} rounded mb-4 w-12 mx-auto`} />
      <div className={`h-6 ${shimmer} rounded mb-2 w-3/4 mx-auto`} />
      <div className={`h-4 ${shimmer} rounded w-1/2 mx-auto`} />
    </div>
  );

  const renderSkeleton = () => {
    switch (type) {
      case 'question':
        return <QuestionSkeleton />;
      case 'subject':
        return <SubjectSkeleton />;
      default:
        return <CardSkeleton />;
    }
  };

  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index}>
          {renderSkeleton()}
        </div>
      ))}
    </div>
  );
};

export default SkeletonLoader;