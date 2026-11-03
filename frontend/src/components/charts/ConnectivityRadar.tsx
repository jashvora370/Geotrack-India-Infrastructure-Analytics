'use client';

import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';

const RADAR_DATA = [
  { metric: 'Avg Degree', year2016: 65, year2026: 82, fullMark: 100 },
  { metric: 'Clustering', year2016: 45, year2026: 68, fullMark: 100 },
  { metric: 'Density', year2016: 52, year2026: 78, fullMark: 100 },
  { metric: 'Intersection Den.', year2016: 60, year2026: 89, fullMark: 100 },
  { metric: 'Alt. Routing', year2016: 50, year2026: 80, fullMark: 100 },
];

export function ConnectivityRadar() {
  return (
    <div className="w-full h-80 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
      <div className="flex items-center justify-between mb-1">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Road Network Graph Connectivity Index
          </h3>
          <p className="text-xs text-slate-400">Relative structural indices (0–100 scale)</p>
        </div>
        <span className="text-[10px] font-mono text-purple-400 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
          NetworkX Graph
        </span>
      </div>

      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={RADAR_DATA}>
            <PolarGrid stroke="#334155" opacity={0.6} />
            <PolarAngleAxis dataKey="metric" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" tick={{ fontSize: 9 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '12px',
                color: '#f8fafc',
                fontSize: '12px',
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
            <Radar name="2016 Baseline" dataKey="year2016" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.25} />
            <Radar name="2026 Current" dataKey="year2026" stroke="#a855f7" fill="#a855f7" fillOpacity={0.35} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
