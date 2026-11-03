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
  Cell,
} from 'recharts';

interface ChangeChartProps {
  newRoadsKm?: number;
  removedRoadsKm?: number;
  widenedRoadsKm?: number;
  unchangedKm?: number;
}

export function ChangeDetectionChart({
  newRoadsKm = 1184.2,
  removedRoadsKm = 114.5,
  widenedRoadsKm = 342.8,
  unchangedKm = 2181.5,
}: ChangeChartProps) {
  const data = [
    { name: 'Newly Added', length_km: newRoadsKm, color: '#10b981' },
    { name: 'Widened', length_km: widenedRoadsKm, color: '#f59e0b' },
    { name: 'Unchanged', length_km: unchangedKm, color: '#3b82f6' },
    { name: 'Discontinued', length_km: removedRoadsKm, color: '#ef4444' },
  ];

  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Network Dynamics (2016 vs 2026)
          </h3>
          <p className="text-xs text-slate-400">Kilometres categorised by spatial change detection engine</p>
        </div>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
          Spatial Join IoU
        </span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 30, left: 30, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} horizontal={false} />
          <XAxis type="number" stroke="#94a3b8" fontSize={11} unit=" km" />
          <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} tickLine={false} width={85} />
          <Tooltip
            formatter={(value: any) => [`${value} km`, 'Length']}
            contentStyle={{
              backgroundColor: '#0f172a',
              borderColor: '#334155',
              borderRadius: '12px',
              color: '#f8fafc',
              fontSize: '12px',
            }}
          />
          <Bar dataKey="length_km" radius={[0, 6, 6, 0]}>
            {data.map((entry, index) => (
              <Cell key={`bar-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
