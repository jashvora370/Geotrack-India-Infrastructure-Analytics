'use client';

import React, { useState, useEffect } from 'react';
import { MapPin, CheckCircle2, ArrowRight, ShieldCheck, Star, Search } from 'lucide-react';
import { api } from '@/lib/api';
import type { State, District, City } from '@/lib/types';
import toast from 'react-hot-toast';
import { useRouter } from 'next/navigation';

export default function RegionSelectionPage() {
  const router = useRouter();
  const [states, setStates] = useState<State[]>([]);
  const [selectedState, setSelectedState] = useState<string>('Maharashtra');
  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedDistrict, setSelectedDistrict] = useState<string>('Pune');
  const [cities, setCities] = useState<City[]>([]);
  const [selectedCity, setSelectedCity] = useState<string>('Pune Municipal Corporation');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadStates() {
      try {
        const sList = await api.regions.getStates();
        setStates(sList);
      } catch (err) {
        console.error(err);
      }
    }
    loadStates();
  }, []);

  useEffect(() => {
    async function loadDistricts() {
      if (!selectedState) return;
      try {
        const dList = await api.regions.getDistricts(selectedState);
        setDistricts(dList);
        if (dList.length > 0) setSelectedDistrict(dList[0].name);
      } catch (err) {
        console.error(err);
      }
    }
    loadDistricts();
  }, [selectedState]);

  useEffect(() => {
    async function loadCities() {
      if (!selectedDistrict) return;
      try {
        const cList = await api.regions.getCities(selectedDistrict);
        setCities(cList);
        if (cList.length > 0) setSelectedCity(cList[0].name);
      } catch (err) {
        console.error(err);
      }
    }
    loadCities();
  }, [selectedDistrict]);

  const handleApplyRegion = (regionName: string) => {
    toast.success(`Region activated: ${regionName}`);
    router.push('/');
  };

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <MapPin className="w-5 h-5 text-sky-400" />
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Geographical Study Area Selection
          </h1>
        </div>
        <p className="text-sm text-slate-400">
          Select or customize a geographical territory in India for multi-temporal road network analysis
        </p>
      </div>

      {/* Recommended Study Regions (The 3 Evaluated Study Areas) */}
      <div>
        <h2 className="text-base font-semibold text-slate-100 mb-4 flex items-center gap-2">
          <Star className="w-4 h-4 text-amber-400" />
          Evaluated Academic Study Regions
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Option 1: Pune (RECOMMENDED) */}
          <div className="relative bg-gradient-to-b from-sky-950/40 via-slate-900 to-slate-900 border-2 border-sky-500 rounded-2xl p-6 shadow-2xl flex flex-col justify-between">
            <div className="absolute -top-3 right-4 px-3 py-0.5 bg-sky-500 text-slate-950 text-[10px] font-bold uppercase rounded-full tracking-wider shadow">
              RECOMMENDED STUDY AREA
            </div>
            <div>
              <div className="text-xs font-mono text-sky-400 font-semibold mb-1">
                MAHARASHTRA
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-2">
                Pune Metropolitan Region
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                Exceptional 10-year road growth (Ring Road, Pune Metro Line 2 corridor, Hinjawadi & Kharadi SEZs). High historical OSM completeness index and continuous cloud-free Sentinel-2 coverage.
              </p>
              <div className="space-y-1.5 text-xs text-slate-400 mb-6 font-mono">
                <div className="flex justify-between">
                  <span>Bounding Box:</span>
                  <span className="text-slate-200">18.35°N, 73.75°E</span>
                </div>
                <div className="flex justify-between">
                  <span>OSM Completeness:</span>
                  <span className="text-emerald-400">★★★★★ (98%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Satellite Quality:</span>
                  <span className="text-emerald-400">★★★★★ (10m)</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => handleApplyRegion('Pune Metropolitan Region')}
              className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-sky-900/30 transition"
            >
              <CheckCircle2 className="w-4 h-4" />
              Active Study Area
            </button>
          </div>

          {/* Option 2: Surat */}
          <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="text-xs font-mono text-slate-400 font-semibold mb-1">
                GUJARAT
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-2">
                Surat Urban Area
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                Rapid urban road widening under Smart City Mission & BRTS network expansion. Strong satellite coverage with industrial periphery expansion towards Hazira.
              </p>
              <div className="space-y-1.5 text-xs text-slate-400 mb-6 font-mono">
                <div className="flex justify-between">
                  <span>Bounding Box:</span>
                  <span className="text-slate-300">21.10°N, 72.75°E</span>
                </div>
                <div className="flex justify-between">
                  <span>OSM Completeness:</span>
                  <span className="text-amber-400">★★★★☆ (85%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Satellite Quality:</span>
                  <span className="text-emerald-400">★★★★★ (10m)</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => handleApplyRegion('Surat Urban Area')}
              className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 border border-slate-700 transition"
            >
              Switch to Surat
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Option 3: Delhi-NCR */}
          <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <div className="text-xs font-mono text-slate-400 font-semibold mb-1">
                DELHI / HARYANA
              </div>
              <h3 className="text-xl font-bold text-slate-100 mb-2">
                Delhi–NCR Corridor (Gurugram)
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                Dwarka Expressway, KMP Peripheral Expressway, and extensive rapid transit expansion. High road complexity and multi-jurisdiction governance.
              </p>
              <div className="space-y-1.5 text-xs text-slate-400 mb-6 font-mono">
                <div className="flex justify-between">
                  <span>Bounding Box:</span>
                  <span className="text-slate-300">28.40°N, 77.00°E</span>
                </div>
                <div className="flex justify-between">
                  <span>OSM Completeness:</span>
                  <span className="text-emerald-400">★★★★★ (95%)</span>
                </div>
                <div className="flex justify-between">
                  <span>Satellite Quality:</span>
                  <span className="text-amber-400">★★★★☆ (Monsoon cloud)</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => handleApplyRegion('Delhi-NCR Gurugram Corridor')}
              className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 border border-slate-700 transition"
            >
              Switch to NCR
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Custom Region Administrative Selector */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
        <div>
          <h3 className="text-base font-semibold text-slate-100">
            Administrative Hierarchy Explorer
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Select an Indian State, District, and Municipal Unit to initiate spatial network query
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* State */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">
              1. Select State / UT
            </label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {states.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </div>

          {/* District */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">
              2. Select District
            </label>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {districts.map((d) => (
                <option key={d.id} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* City / Ward */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">
              3. Municipal Unit / Ward
            </label>
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {cities.map((c) => (
                <option key={c.id} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button
            onClick={() => handleApplyRegion(`${selectedCity}, ${selectedDistrict}`)}
            className="px-5 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-sky-900/30 transition flex items-center gap-2"
          >
            Apply Administrative Boundary
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
