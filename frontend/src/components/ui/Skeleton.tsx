'use client';

import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: boolean;
  circle?: boolean;
}

export function Skeleton({
  className,
  width,
  height,
  rounded = false,
  circle = false,
}: SkeletonProps) {
  return (
    <div
      className={clsx(
        'shimmer',
        circle ? 'rounded-full' : rounded ? 'rounded-lg' : 'rounded',
        className
      )}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx('card p-5 space-y-3', className)}>
      <Skeleton height={16} width="60%" rounded />
      <Skeleton height={32} width="80%" rounded />
      <Skeleton height={12} width="40%" rounded />
    </div>
  );
}

export function SkeletonChart({ className }: { className?: string }) {
  return (
    <div className={clsx('card p-5 space-y-4', className)}>
      <Skeleton height={16} width="40%" rounded />
      <div className="flex items-end gap-2 h-40">
        {[60, 80, 45, 90, 70, 55, 85, 65].map((h, i) => (
          <Skeleton key={i} height={`${h}%`} className="flex-1" rounded />
        ))}
      </div>
    </div>
  );
}

export function SkeletonText({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={12}
          width={i === lines - 1 ? '60%' : '100%'}
          rounded
        />
      ))}
    </div>
  );
}
