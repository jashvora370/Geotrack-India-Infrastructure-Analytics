'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

const NDVI_DATA = [
  { year: 2016, ndvi: 0.364, greenFraction: 0.42 },
  { year: 2017, ndvi: 0.358, greenFraction: 0.41 },
  { year: 2018, ndvi: 0.352, greenFraction: 0.39 },
  { year: 2019, ndvi: 0.347, greenFraction: 0.38 },
  { year: 2020, ndvi: 0.349, greenFraction: 0.38 },
  { year: 2021, ndvi: 0.342, greenFraction: 0.36 },
  { year: 2022, ndvi: 0.338, greenFraction: 0.35 },
  { year: 2023, ndvi: 0.334, greenFraction: 0.34 },
  { year: 2024, ndvi: 0.330, greenFraction: 0.33 },
  { year: 2025, ndvi: 0.326, greenFraction: 0.32 },
  { year: 2026, ndvi: 0.321, greenFraction: 0.31 },
];

export function NDVITimeSeries() {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Corridor Vegetation Health (NDVI 2016–2026)
          </h3>
          <p className="text-xs text-slate-400">Mean annual NDVI inside 100m road buffer corridors</p>
        </div>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
          Sentinel-2 & Landsat
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={NDVI_DATA} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
          <XAxis dataKey="year" stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis domain={[0.25, 0.42]} stroke="#94a3b8" fontSize={11} tickLine={false} />
          <Tooltip
            formatter={(val: any) => [val, 'Mean NDVI']}
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '12px',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <ReferenceLine y={0.30} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: 'Sparse Threshold', fill: '#f59e0b', fontSize: 10 }} />
          <Line
            type="monotone"
            dataKey="ndvi"
            stroke="#10b981"
            strokeWidth={3}
            dot={{ fill: '#10b981', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
