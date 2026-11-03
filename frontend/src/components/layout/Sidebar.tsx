'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  MapPin,
  Map,
  Route,
  Ruler,
  Satellite,
  Building2,
  BarChart3,
  Download,
  Database,
  ChevronLeft,
  ChevronRight,
  Globe,
} from 'lucide-react';

const NAV_ITEMS = [
  {
    label: 'Overview',
    href: '/',
    icon: LayoutDashboard,
    description: 'Dashboard & KPIs',
  },
  {
    label: 'Region Selection',
    href: '/region-selection',
    icon: MapPin,
    description: 'Select study area',
  },
  {
    label: 'Interactive Map',
    href: '/map',
    icon: Map,
    description: 'Explore GIS layers',
  },
  {
    label: 'Road Network',
    href: '/road-network',
    icon: Route,
    description: 'Network analysis',
  },
  {
    label: 'Road Width',
    href: '/road-width',
    icon: Ruler,
    description: 'Width analysis',
  },
  {
    label: 'Satellite Imagery',
    href: '/satellite',
    icon: Satellite,
    description: 'Before/after comparison',
  },
  {
    label: 'Urban Expansion',
    href: '/urban-expansion',
    icon: Building2,
    description: 'Built-up area growth',
  },
  {
    label: 'Statistical Insights',
    href: '/insights',
    icon: BarChart3,
    description: 'Auto-generated insights',
  },
  {
    label: 'Reports',
    href: '/reports',
    icon: Download,
    description: 'Download reports',
  },
  {
    label: 'Data Sources',
    href: '/data-sources',
    icon: Database,
    description: 'Sources & methodology',
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={clsx(
        'flex flex-col h-full bg-slate-950 border-r border-slate-800 transition-all duration-300 ease-in-out',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div
        className={clsx(
          'flex items-center gap-3 px-4 py-5 border-b border-slate-800',
          collapsed && 'justify-center px-2'
        )}
      >
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500 to-emerald-500 flex items-center justify-center flex-shrink-0">
          <Globe className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="text-sm font-bold text-white leading-tight tracking-wide">
              Roadies
            </h1>
            <p className="text-xs text-slate-500 font-mono">Decadal Road Observatory</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-default group',
                isActive
                  ? 'bg-sky-500/15 text-sky-400 border border-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800',
                collapsed && 'justify-center px-2'
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon
                className={clsx(
                  'w-4 h-4 flex-shrink-0',
                  isActive ? 'text-sky-400' : 'text-slate-500 group-hover:text-slate-300'
                )}
              />
              {!collapsed && (
                <div className="min-w-0">
                  <div className="font-medium leading-tight truncate">
                    {item.label}
                  </div>
                  <div className="text-xs text-slate-500 truncate">
                    {item.description}
                  </div>
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="p-2 border-t border-slate-800">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-default',
            collapsed && 'justify-center'
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
