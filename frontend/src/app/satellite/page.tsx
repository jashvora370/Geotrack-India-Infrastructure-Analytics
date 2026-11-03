'use client';

import React from 'react';
import { Satellite, TreePine, Sparkles, Layers, Info } from 'lucide-react';
import { ImagerySlider } from '@/components/satellite/ImagerySlider';
import { NDVITimeSeries } from '@/components/charts/NDVITimeSeries';
import { KPICard } from '@/components/dashboard/KPICard';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';
import { DataSourceBadge } from '@/components/ui/DataSourceBadge';

export default function SatelliteImageryPage() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Satellite className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Satellite Remote Sensing & Vegetation Dynamics
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Multi-spectral earth observation analysis across Pune road corridors (Copernicus Sentinel-2 & USGS Landsat 8/9)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DataSourceBadge source="Sentinel-2 (10m)" />
          <DataSourceBadge source="Landsat 8 (30m)" />
          <ConfidenceBadge level="HIGH" />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Baseline NDVI (2016)"
          value="0.364"
          unit="mean"
          icon={TreePine}
          confidence="HIGH"
          source="Landsat 8 OLI composite"
        />
        <KPICard
          title="Current NDVI (2026)"
          value="0.321"
          unit="mean"
          change={-11.81}
          changeLabel="10-year vegetation drop"
          icon={TreePine}
          confidence="HIGH"
          source="Sentinel-2 Harmonised"
        />
        <KPICard
          title="Road Corridor Buffer"
          value="100"
          unit="metres"
          icon={Layers}
          confidence="HIGH"
          source="Spatial analysis mask"
        />
        <KPICard
          title="Pixel Resolution"
          value="10"
          unit="m/px"
          icon={Satellite}
          confidence="HIGH"
          source="Copernicus MSI Band 4 & 8"
        />
      </div>

      {/* Split-screen comparison slider */}
      <ImagerySlider />

      {/* NDVI Timeseries and Methodology Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <NDVITimeSeries />
        </div>

        <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 mb-2 flex items-center gap-2">
              <Info className="w-4 h-4 text-emerald-400" />
              NDVI Mathematical Formulation & Sensors
            </h3>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Normalized Difference Vegetation Index (NDVI) assesses live green vegetation health by contrasting near-infrared (NIR) reflection with red light absorption:
            </p>

            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl mb-4 font-mono text-center text-emerald-400 text-sm">
              NDVI = (NIR - RED) / (NIR + RED)
            </div>

            <div className="space-y-2.5 text-xs text-slate-300">
              <div className="flex justify-between pb-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Sentinel-2 Bands:</span>
                <span className="font-mono text-slate-200">Band 8 (NIR, 842nm) & Band 4 (Red, 665nm)</span>
              </div>
              <div className="flex justify-between pb-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Landsat 8/9 Bands:</span>
                <span className="font-mono text-slate-200">Band 5 (NIR, 865nm) & Band 4 (Red, 655nm)</span>
              </div>
              <div className="flex justify-between pb-1.5 border-b border-slate-800/80">
                <span className="text-slate-400">Cloud Screening:</span>
                <span className="font-mono text-slate-200">QA60 mask & Pixel QA flags (&lt;15% clouds)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Composite Epoch:</span>
                <span className="font-mono text-slate-200">Annual median (Post-monsoon Oct–Dec)</span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
            Observation: Vegetation loss strongly correlates with road widening in Hinjawadi, Kharadi, and the Southern Ring Road alignment.
          </div>
        </div>
      </div>
    </div>
  );
}
