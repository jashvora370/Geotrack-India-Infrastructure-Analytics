'use client';

import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const LAND_USE_TIMESERIES = [
  { year: 2016, builtUp: 38.2, vegetation: 42.1, agriculture: 16.5, other: 3.2 },
  { year: 2018, builtUp: 41.0, vegetation: 39.8, agriculture: 15.9, other: 3.3 },
  { year: 2020, builtUp: 43.8, vegetation: 38.0, agriculture: 14.8, other: 3.4 },
  { year: 2022, builtUp: 46.9, vegetation: 35.8, agriculture: 13.9, other: 3.4 },
  { year: 2024, builtUp: 49.8, vegetation: 33.6, agriculture: 13.1, other: 3.5 },
  { year: 2026, builtUp: 52.4, vegetation: 31.8, agriculture: 12.3, other: 3.5 },
];

export function UrbanExpansionChart() {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Land Cover Transition & Built-up Expansion (2016–2026)
          </h3>
          <p className="text-xs text-slate-400">Area proportion (%) over Pune metropolitan extent</p>
        </div>
        <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
          JRC GHSL (10m)
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <AreaChart
          data={LAND_USE_TIMESERIES}
          margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} unit="%" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '12px',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px', paddingBottom: '6px' }} />
          <Area type="monotone" dataKey="builtUp" name="Built-Up / Impervious" stackId="1" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.6} />
          <Area type="monotone" dataKey="vegetation" name="Vegetation & Canopy" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.5} />
          <Area type="monotone" dataKey="agriculture" name="Cropland / Scrub" stackId="1" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.4} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
