'use client';

import React from 'react';
import { Database, CheckCircle2, AlertCircle, KeyRound, ExternalLink, ShieldAlert } from 'lucide-react';
import { ConfidenceBadge } from '@/components/ui/ConfidenceBadge';

interface DataSourceItem {
  name: string;
  provider: string;
  type: string;
  resolution: string;
  coverage: string;
  reliability: 'HIGH' | 'MEDIUM' | 'LOW';
  auth: string;
  url: string;
  limitations: string;
}

const DATA_SOURCES: DataSourceItem[] = [
  {
    name: 'ohsome API (OpenStreetMap History)',
    provider: 'Heidelberg Institute for Geoinformation Technology (HeiGIT)',
    type: 'Historical Vector Network',
    resolution: 'Vector geometries',
    coverage: 'Global / India (2007–2026)',
    reliability: 'HIGH',
    auth: 'None (Public REST API)',
    url: 'https://api.ohsome.org/v1',
    limitations: 'Reflects mapping activity as well as physical construction; requires completeness corrections.',
  },
  {
    name: 'OSMnx / Overpass API',
    provider: 'OpenStreetMap Community',
    type: 'Primal Network Graph',
    resolution: 'Sub-meter vector ways',
    coverage: 'Global / Live snapshot',
    reliability: 'HIGH',
    auth: 'None',
    url: 'https://overpass-api.de',
    limitations: 'Tags such as width and lanes are volunteer-submitted and may be incomplete for rural links.',
  },
  {
    name: 'Sentinel-2 MSI Harmonized (L2A)',
    provider: 'European Space Agency (Copernicus)',
    type: 'Optical Multispectral',
    resolution: '10 metres (Bands 2, 3, 4, 8)',
    coverage: 'Global (2017–2026)',
    reliability: 'HIGH',
    auth: 'Google Earth Engine account',
    url: 'https://earthengine.google.com',
    limitations: 'Monsoon cloud cover (July–Sept); 10m resolution cannot delineate individual sub-meter road lanes.',
  },
  {
    name: 'Landsat 8/9 OLI/TIRS (Collection 2)',
    provider: 'USGS / NASA',
    type: 'Optical Multispectral',
    resolution: '30 metres (Bands 1–7)',
    coverage: 'Global (2013–2026)',
    reliability: 'HIGH',
    auth: 'Google Earth Engine account',
    url: 'https://earthengine.google.com',
    limitations: '30m pixel size limits use to macro-corridor NDVI and land cover changes.',
  },
  {
    name: 'Global Human Settlement Layer (GHSL P2023A)',
    provider: 'European Commission Joint Research Centre (JRC)',
    type: 'Built-up Surface Raster',
    resolution: '10 metres (GHS_BUILT_S)',
    coverage: 'Global epochs 1975–2030',
    reliability: 'HIGH',
    auth: 'None (Direct download / GEE)',
    url: 'https://ghsl.jrc.ec.europa.eu',
    limitations: 'Multi-year epoch intervals; intermediate years are interpolated.',
  },
  {
    name: 'MoRTH / NHAI National Highway Records',
    provider: 'Ministry of Road Transport and Highways (India)',
    type: 'Official Infrastructure Inventory',
    resolution: 'Tabular / Route KM markers',
    coverage: 'National Highways of India',
    reliability: 'HIGH',
    auth: 'Public Domain / OGD Platform',
    url: 'https://morth.nic.in',
    limitations: 'Covers only NH network; state and district road updates depend on state PWD reporting.',
  },
  {
    name: 'ISRO Bhuvan Thematic Services',
    provider: 'National Remote Sensing Centre (NRSC)',
    type: 'Indian LULC & Topo Layers',
    resolution: '1:50,000 scale',
    coverage: 'India',
    reliability: 'MEDIUM',
    auth: 'Registration required',
    url: 'https://bhuvan.nrsc.gov.in',
    limitations: 'Access latency and rate-limiting on automated WMS services.',
  },
];

export default function DataSourcesPage() {
  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-slate-800 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <Database className="w-5 h-5 text-sky-400" />
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Data Sources, Verification & Analytical Methodology
          </h1>
        </div>
        <p className="text-sm text-slate-400">
          Strict academic provenance, data quality framework, and reproducible algorithms for the 2016–2026 study
        </p>
      </div>

      {/* Provenance Guarantee Alert */}
      <div className="bg-sky-950/40 border border-sky-800/60 rounded-2xl p-5 flex items-start gap-4">
        <ShieldAlert className="w-6 h-6 text-sky-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <h3 className="font-semibold text-slate-100 text-sm">
            Academic Research Integrity Policy
          </h3>
          <p className="leading-relaxed text-slate-400">
            Never generate synthetic or fabricated road network measurements. Where historical satellite or mapping data is unavailable or constrained by cloud cover, parameters are explicitly labelled as <span className="text-amber-400 font-mono font-medium">ESTIMATED</span> or <span className="text-slate-400 font-mono font-medium">UNAVAILABLE</span>.
          </p>
        </div>
      </div>

      {/* Data Sources Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-100 mb-2">
          Integrated Primary & Secondary Datasets
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          All external datasets utilised in GeoTrack India pipelines with their respective limitations and spatial coverage.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-3 px-2">Source & Provider</th>
                <th className="py-3 px-2">Data Type</th>
                <th className="py-3 px-2">Resolution</th>
                <th className="py-3 px-2">Reliability</th>
                <th className="py-3 px-2">Authentication</th>
                <th className="py-3 px-2">Known Limitations</th>
                <th className="py-3 px-2">Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {DATA_SOURCES.map((ds, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition">
                  <td className="py-3 px-2">
                    <div className="font-semibold text-slate-100">{ds.name}</div>
                    <div className="text-[11px] text-slate-400">{ds.provider}</div>
                  </td>
                  <td className="py-3 px-2 font-mono text-[11px] text-slate-300">{ds.type}</td>
                  <td className="py-3 px-2 font-mono text-[11px]">{ds.resolution}</td>
                  <td className="py-3 px-2">
                    <ConfidenceBadge level={ds.reliability} />
                  </td>
                  <td className="py-3 px-2 text-[11px] text-slate-400">{ds.auth}</td>
                  <td className="py-3 px-2 text-[11px] text-slate-400 max-w-xs">{ds.limitations}</td>
                  <td className="py-3 px-2">
                    <a
                      href={ds.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sky-400 hover:text-sky-300 inline-flex items-center gap-1"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology Deep-Dive Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <h3 className="text-sm font-semibold text-slate-100 mb-2">
            1. Spatial Matching & Change Detection Methodology
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-3">
            Road network change detection operates in projected metric space (UTM Zone 43N, EPSG:32643) to guarantee metric precision:
          </p>
          <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside">
            <li><strong>Buffer Tolerance:</strong> 15-metre spatial buffers constructed around 2016 baseline geometries to absorb GPS inaccuracies and volunteer alignment deviations.</li>
            <li><strong>Geometric Conflation:</strong> Segments from 2026 whose centroid and buffered geometry do not intersect 2016 buffered ways are classified as <span className="text-emerald-400 font-medium">NEW</span>.</li>
            <li><strong>Intersection-over-Union (IoU):</strong> Applied to buffered pairs to distinguish alignment refinements from genuine road widening.</li>
          </ul>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
          <h3 className="text-sm font-semibold text-slate-100 mb-2">
            2. Google Earth Engine & API Credentials Setup
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-3">
            The platform functions with public endpoints (ohsome, Overpass, GHSL) by default. To enable direct cloud GEE processing:
          </p>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1 mb-3">
            <div>1. Register at <span className="text-sky-400">earthengine.google.com</span></div>
            <div>2. Run: <span className="text-emerald-400">python -c "import ee; ee.Authenticate()"</span></div>
            <div>3. Or configure backend/.env:</div>
            <div className="text-slate-400">GEE_SERVICE_ACCOUNT=your-sa@project.iam.gserviceaccount.com</div>
          </div>
          <p className="text-[11px] text-slate-400">
            If GEE credentials are not supplied, the platform automatically serves verified cached statistics.
          </p>
        </div>
      </div>
    </div>
  );
}
