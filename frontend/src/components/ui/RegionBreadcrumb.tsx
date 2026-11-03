'use client';

import { ChevronRight, MapPin } from 'lucide-react';
import { clsx } from 'clsx';

interface RegionBreadcrumbProps {
  parts: string[];
  className?: string;
}

export function RegionBreadcrumb({ parts, className }: RegionBreadcrumbProps) {
  return (
    <nav
      aria-label="Region breadcrumb"
      className={clsx('flex items-center gap-1 text-sm', className)}
    >
      <MapPin className="w-3.5 h-3.5 text-geotrack-primary flex-shrink-0" />
      {parts.map((part, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && (
            <ChevronRight className="w-3 h-3 text-slate-500 flex-shrink-0" />
          )}
          <span
            className={clsx(
              i === parts.length - 1
                ? 'text-slate-100 font-medium'
                : 'text-slate-400'
            )}
          >
            {part}
          </span>
        </span>
      ))}
    </nav>
  );
}
