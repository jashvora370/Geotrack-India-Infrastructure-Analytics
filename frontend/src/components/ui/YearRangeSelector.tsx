'use client';

import { clsx } from 'clsx';

interface YearRangeSelectorProps {
  value: number;
  min?: number;
  max?: number;
  onChange: (year: number) => void;
  className?: string;
  showLabel?: boolean;
}

export function YearRangeSelector({
  value,
  min = 2016,
  max = 2026,
  onChange,
  className,
  showLabel = true,
}: YearRangeSelectorProps) {
  const years = Array.from({ length: max - min + 1 }, (_, i) => min + i);

  return (
    <div className={clsx('flex flex-col gap-2', className)}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{min}</span>
          <span className="font-mono font-semibold text-geotrack-primary text-sm">
            {value}
          </span>
          <span>{max}</span>
        </div>
      )}
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none bg-slate-700 accent-geotrack-primary cursor-pointer"
        aria-label="Year selector"
      />
      {/* Quick year buttons */}
      <div className="flex gap-1 flex-wrap">
        {[2016, 2020, 2023, 2026].map((y) => (
          <button
            key={y}
            onClick={() => onChange(y)}
            className={clsx(
              'px-2 py-0.5 rounded text-xs font-mono transition-default',
              value === y
                ? 'bg-geotrack-primary text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            )}
          >
            {y}
          </button>
        ))}
      </div>
    </div>
  );
}

interface YearToggleProps {
  years?: number[];
  selected: number[];
  onToggle: (year: number) => void;
  className?: string;
}

export function YearToggle({
  years = [2016, 2026],
  selected,
  onToggle,
  className,
}: YearToggleProps) {
  return (
    <div className={clsx('flex gap-1', className)}>
      {years.map((year) => (
        <button
          key={year}
          onClick={() => onToggle(year)}
          className={clsx(
            'px-3 py-1.5 rounded-lg text-sm font-mono font-medium transition-default',
            selected.includes(year)
              ? 'bg-geotrack-primary text-white shadow-sm'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700'
          )}
        >
          {year}
        </button>
      ))}
    </div>
  );
}
