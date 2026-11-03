'use client';

import React from 'react';
import { Download, BookOpen, Quote, ShieldCheck } from 'lucide-react';
import { ReportDownloader } from '@/components/reports/ReportDownloader';

export default function ReportsPage() {
  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Download className="w-5 h-5 text-sky-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">
              Export Research Reports & Datasets
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Download comprehensive academic publications, raw CSV data tables, and formatted Excel workbooks
          </p>
        </div>
      </div>

      {/* Downloader Cards */}
      <ReportDownloader regionId={1001} />

      {/* Academic Citation Guide */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center gap-2">
          <Quote className="w-5 h-5 text-sky-400" />
          <h3 className="text-base font-semibold text-slate-100">
            Academic Citation & Attribution Standards
          </h3>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          If referencing or integrating data derived from MargaVikas in an academic paper, thesis, or technical report, please adhere to standard attribution format:
        </p>

        <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-slate-300 leading-relaxed overflow-x-auto select-all">
          MargaVikas (2026). Decadal Road Infrastructure Change Detection and Geospatial Analytics Platform (Pune Metropolitan Region Study 2016–2026). Academic Internship Research Project. Utilizing OpenStreetMap history (ohsome API, HeiGIT), Copernicus Sentinel-2 MSI, USGS/NASA Landsat 8/9, and JRC Global Human Settlement Layer (GHSL).
        </div>
      </div>

      {/* Data Quality and Reproducibility Notice */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex items-start gap-4 text-xs text-slate-400">
        <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-slate-200 text-sm mb-1">
            Reproducibility & Open Science Compliance
          </h4>
          <p className="leading-relaxed">
            All code pipelines, buffer matching parameters (15m tolerance threshold), IoU similarity formulas, and IRC width lookups are documented and open-sourced under the MargaVikas repository. Raw GeoJSON extracts are preserved in UTM 43N projected metric coordinates.
          </p>
        </div>
      </div>
    </div>
  );
}
