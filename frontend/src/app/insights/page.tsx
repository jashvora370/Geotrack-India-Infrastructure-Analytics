'use client';

import React, { useEffect, useState } from 'react';
import { BarChart3, Filter, Sparkles } from 'lucide-react';
import { InsightCard } from '@/components/insights/InsightCard';
import { api } from '@/lib/api';
import type { Insight } from '@/lib/types';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function InsightsPage() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadInsights() {
      try {
        setLoading(true);
        const data = await api.analytics.getInsights(1001);
        setInsights(data);
      } catch (err) {
        console.error('Failed to load insights:', err);
      } finally {
        setLoading(false);
      }
    }
    loadInsights();
  }, []);

  const categories = [
    { id: 'all', label: 'All Findings' },
    { id: 'road_growth', label: 'Road Growth' },
    { id: 'urban_expansion', label: 'Urban Expansion' },
    { id: 'connectivity', label: 'Network Connectivity' },
    { id: 'land_use', label: 'Land Use & Canopy' },
    { id: 'general', label: 'Data Quality & Caveats' },
  ];

  const filteredInsights =
    selectedCategory === 'all'
      ? insights
      : insights.filter((item) => item.category === selectedCategory);

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-5 h-5 text-sky-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Statistical Insights & Empirical Findings
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Algorithmic research findings derived from 10-year multi-source geospatial analysis (2016–2026)
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-950/60 px-3 py-1.5 rounded-xl border border-emerald-800/40">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          6 Rigorous Peer-Verifiable Findings
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex flex-wrap items-center gap-2 bg-slate-900/60 p-2 rounded-2xl border border-slate-800 text-xs">
        <Filter className="w-3.5 h-3.5 text-slate-400 ml-2 mr-1" />
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            className={`px-3 py-1.5 rounded-xl font-medium transition ${
              selectedCategory === cat.id
                ? 'bg-sky-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/80'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Insights List */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
          <LoadingSpinner size="lg" />
          <span className="text-xs font-mono">Deriving statistical findings...</span>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredInsights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </div>
  );
}
