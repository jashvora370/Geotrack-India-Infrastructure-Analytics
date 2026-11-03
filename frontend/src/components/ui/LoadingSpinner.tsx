'use client';

import { clsx } from 'clsx';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-2',
  lg: 'w-12 h-12 border-3',
};

export function LoadingSpinner({
  size = 'md',
  className,
  label,
}: LoadingSpinnerProps) {
  return (
    <div
      className={clsx('flex flex-col items-center justify-center gap-3', className)}
      role="status"
      aria-label={label || 'Loading'}
    >
      <div
        className={clsx(
          sizeClasses[size],
          'rounded-full border-slate-700 border-t-geotrack-primary animate-spin'
        )}
      />
      {label && (
        <span className="text-sm text-slate-400 font-medium">{label}</span>
      )}
    </div>
  );
}

export function FullPageLoader({ message }: { message?: string }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" label={message || 'Loading data...'} />
    </div>
  );
}
