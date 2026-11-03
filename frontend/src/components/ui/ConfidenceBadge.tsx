'use client';

import { clsx } from 'clsx';
import type { ConfidenceLevel } from '@/lib/types';

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  showLabel?: boolean;
  className?: string;
}

const CONFIG: Record<
  ConfidenceLevel,
  { label: string; dot: string; badge: string }
> = {
  HIGH: {
    label: 'HIGH',
    dot: 'bg-emerald-500',
    badge:
      'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  },
  MEDIUM: {
    label: 'MEDIUM',
    dot: 'bg-yellow-500',
    badge: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30',
  },
  LOW: {
    label: 'LOW',
    dot: 'bg-amber-500',
    badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
  },
  ESTIMATED: {
    label: 'EST.',
    dot: 'bg-rose-500',
    badge: 'bg-rose-500/10 text-rose-400 border border-rose-500/30',
  },
};

export function ConfidenceBadge({
  level,
  showLabel = true,
  className,
}: ConfidenceBadgeProps) {
  const cfg = CONFIG[level];
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-mono font-medium',
        cfg.badge,
        className
      )}
      title={`Confidence: ${level}`}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {showLabel && cfg.label}
    </span>
  );
}
