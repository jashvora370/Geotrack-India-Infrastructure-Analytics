'use client';

import React from 'react';
import { clsx } from 'clsx';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import type { ConfidenceLevel } from '@/lib/types';

interface KPICardProps {
  title: string;
  value: number | string | null;
  unit?: string;
  change?: number | null;
  changeLabel?: string;
  icon?: LucideIcon;
  confidence?: ConfidenceLevel;
  source?: string;
  isLoading?: boolean;
}

export function KPICard({
  title,
  value,
  unit,
  change,
  changeLabel = 'vs 2016 baseline',
  icon: Icon,
  confidence = 'HIGH',
  source,
  isLoading = false,
}: KPICardProps) {
  if (isLoading) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/2 mb-3"></div>
        <div className="h-8 bg-slate-800 rounded w-3/4 mb-2"></div>
        <div className="h-3 bg-slate-800 rounded w-1/3"></div>
      </div>
    );
  }

  const isPositive = change !== undefined && change !== null && change > 0;
  const isNegative = change !== undefined && change !== null && change < 0;

  return (
    <div className="bg-slate-900/90 hover:bg-slate-900 transition-all border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 shadow-lg backdrop-blur flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {title}
          </span>
          {Icon && (
            <div className="p-2 bg-slate-800/80 rounded-lg text-sky-400">
              <Icon className="w-4 h-4" />
            </div>
          )}
        </div>

        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-slate-100">
            {value !== null && value !== undefined
              ? typeof value === 'number'
                ? value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
                : value
              : 'N/A'}
          </span>
          {unit && (
            <span className="text-sm font-medium text-slate-400">{unit}</span>
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
        {change !== undefined && change !== null ? (
          <div className="flex items-center gap-1.5 font-medium">
            {isPositive && (
              <span className="flex items-center gap-0.5 text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/30">
                <TrendingUp className="w-3.5 h-3.5" />
                +{change.toFixed(1)}%
              </span>
            )}
            {isNegative && (
              <span className="flex items-center gap-0.5 text-rose-400 bg-rose-950/40 px-1.5 py-0.5 rounded border border-rose-800/30">
                <TrendingDown className="w-3.5 h-3.5" />
                {change.toFixed(1)}%
              </span>
            )}
            {!isPositive && !isNegative && (
              <span className="flex items-center gap-0.5 text-slate-400">
                <Minus className="w-3.5 h-3.5" />
                0.0%
              </span>
            )}
            <span className="text-slate-400 text-[11px] truncate max-w-[110px]">
              {changeLabel}
            </span>
          </div>
        ) : (
          <span className="text-slate-400 text-[11px] truncate">
            {source || 'Measured statistic'}
          </span>
        )}

        <ConfidenceBadge level={confidence} />
      </div>
    </div>
  );
}
