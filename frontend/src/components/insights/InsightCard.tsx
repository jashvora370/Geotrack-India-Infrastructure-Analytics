'use client';

import React from 'react';
import {
  TrendingUp,
  Building2,
  Network,
  TreePine,
  Ruler,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import type { Insight } from '@/lib/types';

const ICON_MAP: Record<string, React.ElementType> = {
  TrendingUp,
  Building2,
  Network,
  TreePine,
  Ruler,
  AlertTriangle,
};

export function InsightCard({ insight }: { insight: Insight }) {
  const Icon = (insight.iconName && ICON_MAP[insight.iconName]) || Lightbulb;

  return (
    <div className="bg-slate-900/80 hover:bg-slate-900 transition-all border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 shadow-lg flex gap-4">
      <div className="p-3 bg-slate-800/80 rounded-xl text-sky-400 h-fit flex-shrink-0">
        <Icon className="w-5 h-5" />
      </div>

      <div className="flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
          <span className="text-xs uppercase font-mono tracking-wider text-slate-400">
            {insight.category.replace('_', ' ')}
          </span>
          <ConfidenceBadge level={insight.confidence} />
        </div>

        <h4 className="text-base font-semibold text-slate-100 mb-2">
          {insight.headline}
        </h4>

        <p className="text-sm text-slate-300 leading-relaxed mb-3">
          {insight.supportingText}
        </p>

        <div className="pt-2.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Source: <strong className="text-slate-300">{insight.source}</strong></span>
          {insight.value !== undefined && (
            <span className="font-mono text-sky-400 font-semibold">
              {insight.value > 0 ? `+${insight.value}` : insight.value} {insight.unit}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
