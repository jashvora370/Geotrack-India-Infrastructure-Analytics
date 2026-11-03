'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  Layers,
  Calendar,
  Filter,
  Info,
  Route,
  CheckSquare,
  Square,
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { GeoJSONCollection, MapMode } from '@/lib/types';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

// Dynamic import with SSR false for Leaflet map component
const GeoMap = dynamic(() => import('@/components/map/GeoMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-950 text-slate-400 gap-3">
      <LoadingSpinner size="lg" />
      <span className="text-xs font-mono">Loading Leaflet Geospatial Canvas...</span>
    </div>
  ),
});

export default function InteractiveMapPage() {
  const [mapMode, setMapMode] = useState<MapMode>('diff');
  const [year, setYear] = useState<number>(2026);
  const [segments, setSegments] = useState<GeoJSONCollection | null>(null);
  const [newRoads, setNewRoads] = useState<GeoJSONCollection | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Layer toggles
  const [showHighways, setShowHighways] = useState<boolean>(true);
  const [showArterials, setShowArterials] = useState<boolean>(true);
  const [showLocal, setShowLocal] = useState<boolean>(true);

  useEffect(() => {
    async function loadRoadData() {
      try {
        setLoading(true);
        const [allSegs, newSegs] = await Promise.all([
          api.roadNetwork.getSegments(1001, year),
          api.roadNetwork.getNewRoads(1001),
        ]);
        setSegments(allSegs);
        setNewRoads(newSegs);
      } catch (err) {
        console.error('Failed to load road network map layers:', err);
      } finally {
        setLoading(false);
      }
    }
    loadRoadData();
  }, [year]);

  // Filter features based on active classification toggles
  const filteredSegments = React.useMemo(() => {
    if (!segments || !segments.features) return null;
    return {
      ...segments,
      features: segments.features.filter((f: any) => {
        const hw = f?.properties?.highway || '';
        if (hw === 'motorway' || hw === 'trunk') return showHighways;
        if (hw === 'primary' || hw === 'secondary') return showArterials;
        return showLocal;
      }),
    };
  }, [segments, showHighways, showArterials, showLocal]);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col lg:flex-row overflow-hidden bg-slate-950">
      {/* Left Control & Inspector Panel */}
      <div className="w-full lg:w-96 border-b lg:border-b-0 lg:border-r border-slate-800 bg-slate-900/90 flex flex-col overflow-y-auto z-10">
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-sky-400" />
            <h2 className="text-base font-semibold text-slate-100">
              GIS Layer Controls
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Configure geospatial filters, snapshots, and attribute inspection
          </p>
        </div>

        <div className="p-5 space-y-6">
          {/* Analysis View Mode */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
              Comparison Mode
            </label>
            <div className="grid grid-cols-3 gap-1.5 bg-slate-950 p-1.5 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => {
                  setMapMode('diff');
                  setYear(2026);
                }}
                className={`py-1.5 rounded-lg transition font-medium ${
                  mapMode === 'diff'
                    ? 'bg-sky-500 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Change Diff
              </button>
              <button
                onClick={() => {
                  setMapMode('2026');
                  setYear(2026);
                }}
                className={`py-1.5 rounded-lg transition font-medium ${
                  mapMode === '2026'
                    ? 'bg-emerald-500 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                2026 View
              </button>
              <button
                onClick={() => {
                  setMapMode('2016');
                  setYear(2016);
                }}
                className={`py-1.5 rounded-lg transition font-medium ${
                  mapMode === '2016'
                    ? 'bg-sky-500 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                2016 Baseline
              </button>
            </div>
          </div>

          {/* Year Range Slider */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-sky-400" />
                Snapshot Year
              </label>
              <span className="font-mono text-xs font-bold text-sky-400">
                {year}
              </span>
            </div>
            <input
              type="range"
              min={2016}
              max={2026}
              step={1}
              value={year}
              onChange={(e) => setYear(parseInt(e.target.value, 10))}
              className="w-full accent-sky-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
              <span>2016</span>
              <span>2021</span>
              <span>2026</span>
            </div>
          </div>

          {/* Road Classification Filter Checkboxes */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2.5">
              Road Classification Layers
            </label>
            <div className="space-y-2 text-xs">
              <button
                onClick={() => setShowHighways(!showHighways)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 text-slate-300 hover:text-white"
              >
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-purple-500"></span>
                  <span>National & State Highways</span>
                </div>
                {showHighways ? (
                  <CheckSquare className="w-4 h-4 text-purple-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600" />
                )}
              </button>

              <button
                onClick={() => setShowArterials(!showArterials)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 text-slate-300 hover:text-white"
              >
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-cyan-500"></span>
                  <span>District & Arterial Roads</span>
                </div>
                {showArterials ? (
                  <CheckSquare className="w-4 h-4 text-cyan-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600" />
                )}
              </button>

              <button
                onClick={() => setShowLocal(!showLocal)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-950/60 border border-slate-800 text-slate-300 hover:text-white"
              >
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-amber-500"></span>
                  <span>Urban Local & Residential</span>
                </div>
                {showLocal ? (
                  <CheckSquare className="w-4 h-4 text-amber-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-600" />
                )}
              </button>
            </div>
          </div>

          {/* Road Feature Inspector */}
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2">
              Feature Attribute Inspector
            </label>
            {selectedFeature ? (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs space-y-2">
                <div className="font-semibold text-slate-100 text-sm pb-1.5 border-b border-slate-800">
                  {selectedFeature.name || 'Unnamed Road Segment'}
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-300">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Classification</span>
                    <span className="font-medium">{selectedFeature.highway}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Status</span>
                    <span className="font-medium uppercase text-emerald-400">
                      {selectedFeature.changeType || 'Existing'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Carriageway Width</span>
                    <span className="font-medium">{selectedFeature.width} m</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Lanes</span>
                    <span className="font-medium">{selectedFeature.lanes || 2}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Surface Material</span>
                    <span className="font-medium">{selectedFeature.surface || 'Asphalt'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Length</span>
                    <span className="font-medium">
                      {selectedFeature.length_m ? (selectedFeature.length_m / 1000).toFixed(2) + ' km' : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-slate-950/60 border border-dashed border-slate-800 rounded-xl p-4 text-center text-xs text-slate-400">
                Click any road segment on the map to inspect its attributes, width, and classification history.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Map Canvas */}
      <div className="flex-1 relative h-full">
        <GeoMap
          segments={filteredSegments}
          newRoads={newRoads}
          mode={mapMode}
          year={year}
          height="100%"
          onSelectFeature={(props) => setSelectedFeature(props)}
        />
      </div>
    </div>
  );
}
