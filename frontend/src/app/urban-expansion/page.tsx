'use client';

import React from 'react';
import { Building2, TrendingUp, Layers, MapPin, Globe } from 'lucide-react';
import { UrbanExpansionChart } from '@/components/charts/UrbanExpansionChart';
import { KPICard } from '@/components/dashboard/KPICard';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import { DataSourceBadge } from '@/components/ui/DataSourceBadge';

export default function UrbanExpansionPage() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-amber-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Urban Sprawl & Land Cover Transition (2016–2026)
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Analysing peri-urban road network expansion alongside impervious surface growth via JRC GHSL and ESA WorldCover
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DataSourceBadge source="JRC GHSL P2023A" />
          <DataSourceBadge source="ESA WorldCover" />
          <ConfidenceBadge level="HIGH" />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Built-up Surface (2016)"
          value="38.2%"
          unit="of study area"
          icon={Building2}
          confidence="HIGH"
          source="GHSL GHS_BUILT_S"
        />
        <KPICard
          title="Built-up Surface (2026)"
          value="52.4%"
          unit="of study area"
          change={37.17}
          changeLabel="10-year sprawl growth"
          icon={TrendingUp}
          confidence="HIGH"
          source="GHSL Epoch Extrapolation"
        />
        <KPICard
          title="Converted Land Area"
          value="47.1"
          unit="km²"
          icon={Layers}
          confidence="HIGH"
          source="Agri & Scrub to Impervious"
        />
        <KPICard
          title="Resolution"
          value="10"
          unit="metres"
          icon={Globe}
          confidence="HIGH"
          source="GHSL European Commission"
        />
      </div>

      {/* Chart */}
      <UrbanExpansionChart />

      {/* Corridor Level Urban Growth Hotspots */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
        <h3 className="text-sm font-semibold text-slate-100 mb-2 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-sky-400" />
          Corridor-Level Urbanization & Road Densification Hotspots (Pune)
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Sub-regions exhibiting the fastest rates of simultaneous road construction and impervious surface conversion.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-2.5">Urban Corridor / Ward</th>
                <th className="py-2.5">Road Length 2016</th>
                <th className="py-2.5">Road Length 2026</th>
                <th className="py-2.5">Road Growth</th>
                <th className="py-2.5">Built-up Area Growth</th>
                <th className="py-2.5">Primary Growth Driver</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
              <tr>
                <td className="py-2.5 font-sans font-medium text-slate-100">Hinjawadi - Maan - Marunji Belt</td>
                <td className="py-2.5">142.6 km</td>
                <td className="py-2.5 text-sky-400">238.4 km</td>
                <td className="py-2.5 text-emerald-400">+67.2%</td>
                <td className="py-2.5 text-amber-400">+58.4%</td>
                <td className="py-2.5 font-sans text-slate-400">IT Park Phase 3 & residential high-rises</td>
              </tr>
              <tr>
                <td className="py-2.5 font-sans font-medium text-slate-100">Kharadi - Wagholi Eastern Corridor</td>
                <td className="py-2.5">118.2 km</td>
                <td className="py-2.5 text-sky-400">195.8 km</td>
                <td className="py-2.5 text-emerald-400">+65.6%</td>
                <td className="py-2.5 text-amber-400">+61.2%</td>
                <td className="py-2.5 font-sans text-slate-400">Ahmednagar Highway bypass & SEZ towers</td>
              </tr>
              <tr>
                <td className="py-2.5 font-sans font-medium text-slate-100">Wakad - Punawale - Ravet Spine</td>
                <td className="py-2.5">165.4 km</td>
                <td className="py-2.5 text-sky-400">246.0 km</td>
                <td className="py-2.5 text-emerald-400">+48.7%</td>
                <td className="py-2.5 text-amber-400">+44.8%</td>
                <td className="py-2.5 font-sans text-slate-400">PCMC peri-urban residential expansion</td>
              </tr>
              <tr>
                <td className="py-2.5 font-sans font-medium text-slate-100">Hadapsar - Undri - Saswad Road</td>
                <td className="py-2.5">188.0 km</td>
                <td className="py-2.5 text-sky-400">264.2 km</td>
                <td className="py-2.5 text-emerald-400">+40.5%</td>
                <td className="py-2.5 text-amber-400">+36.9%</td>
                <td className="py-2.5 font-sans text-slate-400">Logistics hubs & residential townships</td>
              </tr>
              <tr>
                <td className="py-2.5 font-sans font-medium text-slate-100">Kothrud - Warje - Sinhagad Road</td>
                <td className="py-2.5">284.5 km</td>
                <td className="py-2.5 text-sky-400">324.0 km</td>
                <td className="py-2.5 text-emerald-400">+13.9%</td>
                <td className="py-2.5 text-amber-400">+9.8%</td>
                <td className="py-2.5 font-sans text-slate-400">Mature urban core; primarily widening</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
