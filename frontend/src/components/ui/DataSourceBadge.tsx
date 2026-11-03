'use client';

import { clsx } from 'clsx';

interface DataSourceBadgeProps {
  source: string;
  reliability?: 'HIGH' | 'MEDIUM' | 'LOW';
  url?: string;
  className?: string;
}

const reliabilityColors = {
  HIGH: 'text-emerald-400',
  MEDIUM: 'text-yellow-400',
  LOW: 'text-amber-400',
};

export function DataSourceBadge({
  source,
  reliability,
  url,
  className,
}: DataSourceBadgeProps) {
  const content = (
    <span
      className={clsx(
        'inline-flex items-center gap-1 text-xs text-slate-400 font-mono',
        className
      )}
    >
      <span className="opacity-60">src:</span>
      <span
        className={clsx(
          'font-medium',
          reliability ? reliabilityColors[reliability] : 'text-slate-300'
        )}
      >
        {source}
      </span>
      {reliability && (
        <span className={clsx('opacity-70', reliabilityColors[reliability])}>
          ({reliability})
        </span>
      )}
    </span>
  );

  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className="hover:underline">
        {content}
      </a>
    );
  }

  return content;
}
