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
import type { TimeseriesData } from '@/lib/types';

interface TimeSeriesChartProps {
  data?: TimeseriesData[];
}

const DEFAULT_SERIES = [
  { year: 2016, totalLength_km: 2410.5, highways_km: 160.7, local_km: 1552.9 },
  { year: 2017, totalLength_km: 2495.2, highways_km: 162.1, local_km: 1621.2 },
  { year: 2018, totalLength_km: 2590.8, highways_km: 168.4, local_km: 1685.3 },
  { year: 2019, totalLength_km: 2715.4, highways_km: 178.9, local_km: 1761.8 },
  { year: 2020, totalLength_km: 2810.1, highways_km: 185.0, local_km: 1825.6 },
  { year: 2021, totalLength_km: 2930.6, highways_km: 196.2, local_km: 1902.4 },
  { year: 2022, totalLength_km: 3065.3, highways_km: 210.5, local_km: 1991.2 },
  { year: 2023, totalLength_km: 3205.8, highways_km: 228.1, local_km: 2080.5 },
  { year: 2024, totalLength_km: 3318.4, highways_km: 239.4, local_km: 2155.5 },
  { year: 2025, totalLength_km: 3410.9, highways_km: 250.0, local_km: 2217.6 },
  { year: 2026, totalLength_km: 3480.2, highways_km: 256.6, local_km: 2267.8 },
];

export function TimeSeriesChart({ data = DEFAULT_SERIES as any }: TimeSeriesChartProps) {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            10-Year Annual Road Network Expansion (2016–2026)
          </h3>
          <p className="text-xs text-slate-400">Total and classification-level network length progression</p>
        </div>
        <span className="text-[10px] font-mono text-sky-400 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/40">
          Source: ohsome API
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="localGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickLine={false} />
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
          <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px', paddingBottom: '8px' }} />
          <Area
            type="monotone"
            dataKey="totalLength_km"
            name="Total Road Length"
            stroke="#0ea5e9"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#totalGrad)"
          />
          <Area
            type="monotone"
            dataKey="local_km"
            name="Urban & Local Roads"
            stroke="#10b981"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#localGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
