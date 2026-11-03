'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface ClassificationPieProps {
  year?: number;
}

const PIE_DATA_2026 = [
  { name: 'National Highways (NH)', value: 256.6, color: '#8b5cf6' },
  { name: 'State Highways (SH)', value: 395.7, color: '#3b82f6' },
  { name: 'Major District (MDR)', value: 560.1, color: '#06b6d4' },
  { name: 'Other District (ODR)', value: 782.4, color: '#10b981' },
  { name: 'Urban Local Streets', value: 1140.5, color: '#f59e0b' },
  { name: 'Village / Unclassified', value: 344.9, color: '#64748b' },
];

export function RoadClassificationPie({ year = 2026 }: ClassificationPieProps) {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
      <div className="flex items-center justify-between mb-1">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Network Hierarchy Breakdown ({year})
          </h3>
          <p className="text-xs text-slate-400">Length distribution by administrative class</p>
        </div>
        <span className="text-[10px] font-mono text-purple-400 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
          IRC Standard
        </span>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={PIE_DATA_2026}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={3}
              dataKey="value"
            >
              {PIE_DATA_2026.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="#0f172a" strokeWidth={2} />
              ))}
            </Pie>
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
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              wrapperStyle={{ fontSize: '10.5px', lineHeight: '18px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
