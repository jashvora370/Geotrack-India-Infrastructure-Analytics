'use client';

import React, { useState } from 'react';
import { Download, FileText, Table, FileSpreadsheet, CheckCircle2, Loader2 } from 'lucide-react';
import { api, downloadBlob } from '@/lib/api';
import toast from 'react-hot-toast';

export function ReportDownloader({ regionId = 1001 }: { regionId?: number }) {
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [loadingCsv, setLoadingCsv] = useState(false);
  const [loadingXlsx, setLoadingXlsx] = useState(false);

  const handleDownloadPdf = async () => {
    try {
      setLoadingPdf(true);
      toast.loading('Compiling 10-year Geospatial PDF report...', { id: 'pdf' });
      const blob = await api.reports.generatePDF(regionId);
      downloadBlob(blob, `MargaVikas_Research_Report_Pune_2016_2026.pdf`);
      toast.success('PDF report downloaded successfully!', { id: 'pdf' });
    } catch (err: any) {
      toast.error(`Download failed: ${err.message}`, { id: 'pdf' });
    } finally {
      setLoadingPdf(false);
    }
  };

  const handleDownloadCsv = async () => {
    try {
      setLoadingCsv(true);
      toast.loading('Packaging CSV datasets...', { id: 'csv' });
      const blob = await api.reports.generateCSV(regionId);
      downloadBlob(blob, `MargaVikas_Data_Pune_2016_2026.zip`);
      toast.success('CSV dataset archive downloaded!', { id: 'csv' });
    } catch (err: any) {
      toast.error(`Download failed: ${err.message}`, { id: 'csv' });
    } finally {
      setLoadingCsv(false);
    }
  };

  const handleDownloadExcel = async () => {
    try {
      setLoadingXlsx(true);
      toast.loading('Generating multi-sheet Excel workbook...', { id: 'xlsx' });
      const blob = await api.reports.generateExcel(regionId);
      downloadBlob(blob, `MargaVikas_Workbook_Pune_2016_2026.xlsx`);
      toast.success('Excel workbook downloaded!', { id: 'xlsx' });
    } catch (err: any) {
      toast.error(`Download failed: ${err.message}`, { id: 'xlsx' });
    } finally {
      setLoadingXlsx(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {/* PDF Card */}
      <div className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-4">
            <FileText className="w-6 h-6" />
          </div>
          <h4 className="text-base font-semibold text-slate-100 mb-2">
            Comprehensive PDF Report
          </h4>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Complete academic report with project introduction, methodology,
            spatial change detection tables, before/after maps, data quality
            caveats, and statistical findings.
          </p>
          <ul className="text-xs text-slate-300 space-y-1.5 mb-6">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              10-Year Network Growth Statistics
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Satellite NDVI & Land Cover Comparison
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              IRC Road Width Distribution
            </li>
          </ul>
        </div>
        <button
          onClick={handleDownloadPdf}
          disabled={loadingPdf}
          className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-rose-900/20 transition disabled:opacity-50"
        >
          {loadingPdf ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Download Research PDF
        </button>
      </div>

      {/* CSV Card */}
      <div className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center mb-4">
            <Table className="w-6 h-6" />
          </div>
          <h4 className="text-base font-semibold text-slate-100 mb-2">
            Raw CSV Dataset Archive (ZIP)
          </h4>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Direct tabular exports suitable for Python pandas, R, or QGIS analysis.
            Includes road classification tables, annual timeseries, and network metrics.
          </p>
          <ul className="text-xs text-slate-300 space-y-1.5 mb-6">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              annual_timeseries_2016_2026.csv
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              road_classification_stats.csv
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              network_connectivity_metrics.csv
            </li>
          </ul>
        </div>
        <button
          onClick={handleDownloadCsv}
          disabled={loadingCsv}
          className="w-full py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-sky-900/20 transition disabled:opacity-50"
        >
          {loadingCsv ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Download CSVs (ZIP)
        </button>
      </div>

      {/* Excel Card */}
      <div className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
        <div>
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <h4 className="text-base font-semibold text-slate-100 mb-2">
            Excel Analytics Workbook
          </h4>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Multi-tab styled Excel workbook formatted for business intelligence
            and executive presentation with summary sheets and KPI tables.
          </p>
          <ul className="text-xs text-slate-300 space-y-1.5 mb-6">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Tab 1: Executive KPI Summary
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Tab 2: 10-Year Annual Timeseries
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Tab 3: Change Detection & Widths
            </li>
          </ul>
        </div>
        <button
          onClick={handleDownloadExcel}
          disabled={loadingXlsx}
          className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/20 transition disabled:opacity-50"
        >
          {loadingXlsx ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Download Excel (.xlsx)
        </button>
      </div>
    </div>
  );
}
