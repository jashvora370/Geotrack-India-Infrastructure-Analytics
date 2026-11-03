'use client';

import React, { useState, useRef, useCallback } from 'react';
import { Sliders, Maximize2, Sparkles, Layers } from 'lucide-react';

interface ImagerySliderProps {
  locationName?: string;
  yearBefore?: number;
  yearAfter?: number;
}

export function ImagerySlider({
  locationName = 'Hinjawadi IT Expressway Corridor, Pune',
  yearBefore = 2016,
  yearAfter = 2026,
}: ImagerySliderProps) {
  const [sliderPos, setSliderPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [bandMode, setBandMode] = useState<'rgb' | 'ndvi'>('rgb');
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMove = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSliderPos(pct);
    },
    []
  );

  const onMouseDown = () => setIsDragging(true);
  const onMouseUp = () => setIsDragging(false);

  const onMouseMove = (e: React.MouseEvent) => {
    if (isDragging) handleMove(e.clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    if (e.touches[0]) handleMove(e.touches[0].clientX);
  };

  return (
    <div className="w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-100">{locationName}</h3>
            <span className="text-[10px] font-mono bg-sky-950 text-sky-400 px-2 py-0.5 rounded border border-sky-800/40">
              Sentinel-2 & Landsat 8 (10m)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Interactive before-and-after satellite comparison slider
          </p>
        </div>

        {/* Toggle Mode */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 p-1 rounded-xl border border-slate-700/60 text-xs">
          <button
            onClick={() => setBandMode('rgb')}
            className={`px-3 py-1 rounded-lg transition font-medium ${
              bandMode === 'rgb' ? 'bg-sky-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            True Color (RGB)
          </button>
          <button
            onClick={() => setBandMode('ndvi')}
            className={`px-3 py-1 rounded-lg transition font-medium ${
              bandMode === 'ndvi' ? 'bg-emerald-500 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            NDVI False Color
          </button>
        </div>
      </div>

      {/* Comparison Viewport */}
      <div
        ref={containerRef}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onTouchMove={onTouchMove}
        className="relative w-full h-[400px] sm:h-[460px] rounded-xl overflow-hidden cursor-ew-resize select-none border border-slate-800 bg-slate-950"
      >
        {/* RIGHT IMAGE (2026 - Background) */}
        <div
          className="absolute inset-0 w-full h-full flex items-center justify-center bg-cover bg-center"
          style={{
            backgroundImage:
              bandMode === 'rgb'
                ? `radial-gradient(circle at 50% 50%, rgba(15,23,42,0.1), rgba(15,23,42,0.8)), linear-gradient(135deg, #1e293b 0%, #0f172a 100%)`
                : `radial-gradient(circle at 60% 40%, rgba(16,185,129,0.3), rgba(15,23,42,0.9)), linear-gradient(135deg, #064e3b 0%, #022c22 100%)`,
          }}
        >
          {/* Simulated satellite vector road grid overlay */}
          <svg className="w-full h-full opacity-60 pointer-events-none" viewBox="0 0 800 500">
            {/* 2026 Expanded 6-lane expressway + Ring Road */}
            <path d="M 50 150 Q 300 200 750 120" stroke="#f59e0b" strokeWidth="12" fill="none" opacity="0.9" />
            <path d="M 80 450 Q 400 300 700 420" stroke="#10b981" strokeWidth="10" fill="none" opacity="0.9" />
            <path d="M 380 50 L 420 480" stroke="#3b82f6" strokeWidth="8" fill="none" opacity="0.8" />
            <path d="M 200 100 L 250 400" stroke="#8b5cf6" strokeWidth="6" fill="none" opacity="0.8" />
            <circle cx="400" cy="220" r="14" fill="#ef4444" opacity="0.8" />
          </svg>
          <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono font-semibold text-emerald-400">
            {yearAfter} (Urbanized Corridor)
          </div>
        </div>

        {/* LEFT IMAGE (2016 - Clipped Foreground) */}
        <div
          className="absolute inset-0 h-full overflow-hidden flex items-center justify-center bg-cover bg-center border-r-2 border-white shadow-2xl"
          style={{
            width: `${sliderPos}%`,
            backgroundImage:
              bandMode === 'rgb'
                ? `radial-gradient(circle at 40% 60%, rgba(30,41,59,0.3), rgba(15,23,42,0.9)), linear-gradient(135deg, #334155 0%, #1e293b 100%)`
                : `radial-gradient(circle at 40% 50%, rgba(5,150,105,0.5), rgba(15,23,42,0.9)), linear-gradient(135deg, #047857 0%, #064e3b 100%)`,
          }}
        >
          {/* Simulated 2016 baseline overlay (narrow 2-lane road and dense vegetation) */}
          <div className="w-[800px] h-[500px] flex-shrink-0 pointer-events-none opacity-50">
            <svg className="w-full h-full" viewBox="0 0 800 500">
              <path d="M 50 150 Q 300 200 750 120" stroke="#94a3b8" strokeWidth="5" fill="none" opacity="0.8" />
              <path d="M 380 50 L 420 480" stroke="#64748b" strokeWidth="4" fill="none" opacity="0.7" />
            </svg>
          </div>

          <div className="absolute top-4 left-4 bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono font-semibold text-sky-400">
            {yearBefore} (Baseline Sparse Road)
          </div>
        </div>

        {/* SLIDER DIVIDER HANDLE */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-white cursor-ew-resize z-20 flex items-center justify-center shadow-[0_0_15px_rgba(255,255,255,0.7)]"
          style={{ left: `${sliderPos}%` }}
          onMouseDown={onMouseDown}
        >
          <div className="w-8 h-8 -ml-3.5 bg-slate-900 text-white rounded-full border-2 border-white flex items-center justify-center shadow-xl">
            <Sliders className="w-4 h-4 text-sky-400" />
          </div>
        </div>
      </div>

      {/* Footer Notes */}
      <div className="mt-3 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
        <span>Drag center handle left/right to reveal infrastructure transformation</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span>
            New Road Construction
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span>
            Widened Corridor
          </span>
        </div>
      </div>
    </div>
  );
}
