'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ComparisonData {
  classification: string;
  year2016: number;
  year2026: number;
}

const DEFAULT_DATA: ComparisonData[] = [
  { classification: 'National Highways', year2016: 160.7, year2026: 256.6 },
  { classification: 'State Highways', year2016: 284.1, year2026: 395.7 },
  { classification: 'Major District', year2016: 412.8, year2026: 560.1 },
  { classification: 'Other District', year2016: 590.2, year2026: 782.4 },
  { classification: 'Urban Local', year2016: 742.6, year2026: 1140.5 },
  { classification: 'Village / Unclass', year2016: 220.1, year2026: 344.9 },
];

export function RoadLengthComparison({ data = DEFAULT_DATA }: { data?: ComparisonData[] }) {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Length by Classification: 2016 vs 2026
          </h3>
          <p className="text-xs text-slate-400">Total length in kilometres (km)</p>
        </div>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
          Empirical Data
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 20, left: 0, bottom: 25 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis
            dataKey="classification"
            stroke="#94a3b8"
            fontSize={11}
            tickLine={false}
            angle={-15}
            textAnchor="end"
          />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} unit=" km" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '12px',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            wrapperStyle={{ paddingBottom: '10px', fontSize: '11px' }}
          />
          <Bar dataKey="year2016" name="2016 Baseline" fill="#38bdf8" radius={[4, 4, 0, 0]} />
          <Bar dataKey="year2026" name="2026 Current" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
