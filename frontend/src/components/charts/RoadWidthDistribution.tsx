'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const WIDTH_DATA = [
  { category: 'Narrow (<5.5m)', year2016: 32.4, year2026: 24.2 },
  { category: 'Medium (5.5-10m)', year2016: 45.1, year2026: 48.6 },
  { category: 'Wide (10-20m)', year2016: 15.2, year2026: 19.4 },
  { category: 'Arterial (20-45m)', year2016: 5.5, year2026: 5.8 },
  { category: 'Highway (>45m)', year2016: 1.8, year2026: 2.0 },
];

export function RoadWidthDistribution() {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Width Distribution Shifts (2016 vs 2026)
          </h3>
          <p className="text-xs text-slate-400">Proportion of road network in each width band (%)</p>
        </div>
        <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
          IRC Standards
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={WIDTH_DATA} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis dataKey="category" stroke="#94a3b8" fontSize={11} tickLine={false} angle={-10} textAnchor="end" />
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
          <Bar dataKey="year2016" name="2016 (%)" fill="#64748b" radius={[4, 4, 0, 0]} />
          <Bar dataKey="year2026" name="2026 (%)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
