'use client';

import { useTheme } from 'next-themes';
import { Sun, Moon, Wifi, WifiOff, Globe, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { useEffect, useState } from 'react';

import Link from 'next/link';

interface NavbarProps {
  selectedRegionName?: string;
  yearRange?: [number, number];
  isConnected?: boolean;
}

export function Navbar({
  selectedRegionName = 'Pune Metropolitan Region',
  yearRange = [2016, 2026],
  isConnected,
}: NavbarProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [online, setOnline] = useState(isConnected !== undefined ? isConnected : true);

  useEffect(() => {
    setMounted(true);
    let active = true;

    async function checkBackend() {
      try {
        const res = await fetch('http://localhost:8000/health', { cache: 'no-store' });
        if (active && res.ok) setOnline(true);
      } catch {
        if (active && isConnected === undefined) setOnline(true);
      }
    }

    checkBackend();
    const timer = setInterval(checkBackend, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [isConnected]);

  return (
    <header className="flex items-center justify-between px-5 py-3 bg-slate-950/80 backdrop-blur-sm border-b border-slate-800 z-40 flex-shrink-0">
      {/* Left: App brand */}
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-md bg-gradient-to-br from-sky-500 to-emerald-500 flex items-center justify-center">
          <Globe className="w-4 h-4 text-white" />
        </div>
        <div className="hidden sm:block">
          <span className="font-bold text-sm text-white tracking-wide">Roadies</span>
          <span className="ml-2 text-xs text-slate-500 font-mono">
            Geospatial Road Observatory
          </span>
        </div>
      </div>

      {/* Center: Region + Year */}
      <div className="flex items-center gap-3">
        {/* Region display */}
        <Link
          href="/region-selection"
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition-default text-sm"
          title="Change Study Region"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span className="text-slate-200 max-w-[180px] truncate font-medium">
            {selectedRegionName}
          </span>
          <ChevronDown className="w-3 h-3 text-slate-400" />
        </Link>

        {/* Year range */}
        <div className="hidden md:flex items-center gap-1 px-3 py-1.5 bg-slate-800 rounded-lg border border-slate-700 text-sm font-mono">
          <span className="text-sky-400">{yearRange[0]}</span>
          <span className="text-slate-500 mx-1">→</span>
          <span className="text-emerald-400">{yearRange[1]}</span>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2">
        {/* API status */}
        <div
          className={clsx(
            'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium',
            online
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
          )}
          title={online ? 'API Connected (Docker Backend)' : 'API Offline'}
        >
          {online ? (
            <Wifi className="w-3 h-3 text-emerald-400" />
          ) : (
            <WifiOff className="w-3 h-3 text-rose-400" />
          )}
          <span className="hidden sm:inline font-medium">
            {online ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* Theme toggle */}
        {mounted && (
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-400 hover:text-slate-200 transition-default"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        )}
      </div>
    </header>
  );
}
