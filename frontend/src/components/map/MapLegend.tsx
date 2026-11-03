'use client';

import React from 'react';

interface LegendItem {
  label: string;
  color: string;
  style?: 'solid' | 'dashed';
}

const ROAD_LEGEND_ITEMS: LegendItem[] = [
  { label: 'Existing Road (2016)', color: '#3b82f6' },
  { label: 'Newly Built Road (2026)', color: '#10b981' },
  { label: 'Removed / Discontinued', color: '#ef4444' },
  { label: 'Widened / Lane Added', color: '#f59e0b' },
  { label: 'National Highway (NH)', color: '#8b5cf6' },
  { label: 'State Highway (SH)', color: '#06b6d4' },
];

export function MapLegend() {
  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-xl p-3.5 shadow-xl text-xs max-w-xs pointer-events-auto">
      <div className="font-semibold text-slate-200 mb-2.5 pb-1.5 border-b border-slate-800 flex items-center justify-between">
        <span>Map Legend</span>
        <span className="text-[10px] text-slate-400 font-normal">OSM / Satellite</span>
      </div>
      <div className="space-y-2">
        {ROAD_LEGEND_ITEMS.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5">
            <span
              className="w-5 h-1.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-slate-300 font-medium text-[11px] leading-tight">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
