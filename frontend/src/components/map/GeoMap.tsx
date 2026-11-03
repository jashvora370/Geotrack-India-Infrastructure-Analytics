'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { GeoJSONCollection, MapMode, TileLayerType } from '@/lib/types';
import { MapLegend } from './MapLegend';
import { Layers, ZoomIn, ZoomOut, Maximize2, Compass } from 'lucide-react';

interface GeoMapProps {
  segments?: GeoJSONCollection | null;
  newRoads?: GeoJSONCollection | null;
  center?: [number, number]; // [lat, lng]
  zoom?: number;
  mode?: MapMode;
  year?: number;
  height?: string;
  onSelectFeature?: (props: any) => void;
}

export default function GeoMap({
  segments,
  newRoads,
  center = [18.5204, 73.8567], // Pune center
  zoom = 12,
  mode = 'diff',
  year = 2026,
  height = '100%',
  onSelectFeature,
}: GeoMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const geojsonLayerRef = useRef<any>(null);
  const [activeTile, setActiveTile] = useState<TileLayerType>('osm');
  const [tileMenuOpen, setTileMenuOpen] = useState(false);

  // Initialize Leaflet map safely on client side
  useEffect(() => {
    if (typeof window === 'undefined' || !mapContainerRef.current) return;

    let isMounted = true;

    async function initMap() {
      const L = (await import('leaflet')).default;
      // Inject leaflet stylesheet if not present
      if (!document.getElementById('leaflet-css')) {
        const link = document.createElement('link');
        link.id = 'leaflet-css';
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
      }

      if (!mapInstanceRef.current && mapContainerRef.current) {
        const map = L.map(mapContainerRef.current, {
          center: center,
          zoom: zoom,
          zoomControl: false,
        });

        // Clean, 100% Free basemaps (Zero API Keys required, No watermarks)
        const tileUrls: Record<TileLayerType, { url: string; attr: string }> = {
          'cartodb-dark': {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
            attr: '&copy; Esri &copy; OpenStreetMap contributors',
          },
          'cartodb-light': {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
            attr: '&copy; Esri &copy; OpenStreetMap contributors',
          },
          osm: {
            url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr: '&copy; OpenStreetMap contributors',
          },
          satellite: {
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr: '&copy; Esri, Maxar, Earthstar Geographics',
          },
        };

        const tileConfig = tileUrls[activeTile];
        const tileLayer = L.tileLayer(tileConfig.url, {
          attribution: tileConfig.attr,
          maxZoom: 19,
        }).addTo(map);

        mapInstanceRef.current = { map, tileLayer, L, tileUrls };
      }
    }

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.map.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Tile Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const { map, tileLayer, L, tileUrls } = mapInstanceRef.current;
    if (tileLayer) map.removeLayer(tileLayer);

    const config = tileUrls[activeTile];
    const newLayer = L.tileLayer(config.url, {
      attribution: config.attr,
      maxZoom: 19,
    }).addTo(map);
    newLayer.bringToBack();
    mapInstanceRef.current.tileLayer = newLayer;
  }, [activeTile]);

  // Update GeoJSON features
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const { map, L } = mapInstanceRef.current;

    if (geojsonLayerRef.current) {
      map.removeLayer(geojsonLayerRef.current);
      geojsonLayerRef.current = null;
    }

    // Use segments for current year snapshot; fallback to newRoads if segments not yet loaded
    const dataToRender = segments || newRoads;
    if (!dataToRender || !dataToRender.features || dataToRender.features.length === 0) {
      return;
    }

    const layer = L.geoJSON(dataToRender as any, {
      style: (feature: any) => {
        const props = feature?.properties || {};
        const cType = props.changeType || 'existing';
        const hw = props.highway || '';

        let color = '#3b82f6'; // existing blue
        let weight = 3;

        if (mode === 'diff') {
          if (cType === 'new') {
            color = '#10b981'; // bright emerald green
            weight = 4.5;
          } else if (cType === 'widened') {
            color = '#f59e0b'; // amber/orange
            weight = 4.5;
          } else if (hw === 'motorway' || hw === 'trunk') {
            color = '#8b5cf6'; // purple highway
            weight = 3.5;
          } else if (hw === 'primary') {
            color = '#06b6d4'; // cyan
            weight = 3;
          }
        } else {
          // Functional classification view (2016 baseline or 2026 full view)
          if (hw === 'motorway' || hw === 'trunk') {
            color = '#8b5cf6'; // purple highway
            weight = 4.5;
          } else if (hw === 'primary') {
            color = '#06b6d4'; // cyan primary
            weight = 3.5;
          } else if (hw === 'secondary') {
            color = '#38bdf8'; // sky blue
            weight = 3;
          } else {
            color = '#94a3b8'; // local/tertiary
            weight = 2.5;
          }
        }

        return {
          color: color,
          weight: weight,
          opacity: 0.88,
          lineJoin: 'round',
          lineCap: 'round',
        };
      },
      onEachFeature: (feature: any, featureLayer: any) => {
        const props = feature?.properties || {};
        const popupContent = `
          <div style="font-family: inherit; font-size: 12px; color: #0f172a; padding: 4px;">
            <div style="font-weight: 700; font-size: 13px; margin-bottom: 4px;">${props.name || 'Unnamed Road'}</div>
            <div><strong>Classification:</strong> ${props.highway || 'local'}</div>
            <div><strong>Status:</strong> ${props.changeType ? props.changeType.toUpperCase() : 'EXISTING'}</div>
            <div><strong>Width:</strong> ${props.width ? props.width + ' m' : 'Estimated'}</div>
            <div><strong>Lanes:</strong> ${props.lanes || 2}</div>
            <div><strong>Length:</strong> ${props.length_m ? (props.length_m / 1000).toFixed(2) + ' km' : 'N/A'}</div>
            <div><strong>Year Tagged:</strong> ${props.year || year}</div>
          </div>
        `;
        featureLayer.bindPopup(popupContent);

        featureLayer.on({
          click: () => {
            if (onSelectFeature) onSelectFeature(props);
          },
          mouseover: (e: any) => {
            const target = e.target;
            target.setStyle({ weight: 6, opacity: 1.0 });
          },
          mouseout: (e: any) => {
            layer.resetStyle(e.target);
          },
        });
      },
    }).addTo(map);

    geojsonLayerRef.current = layer;
  }, [segments, newRoads, mode, year, onSelectFeature]);

  const handleZoomIn = () => mapInstanceRef.current?.map.zoomIn();
  const handleZoomOut = () => mapInstanceRef.current?.map.zoomOut();
  const handleReset = () => mapInstanceRef.current?.map.setView(center, zoom);

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-slate-800 shadow-2xl bg-slate-950" style={{ height }}>
      {/* Map DOM Element */}
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Floating Header Overlay */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3.5 py-1.5 rounded-xl shadow-lg flex items-center gap-2">
          <Compass className="w-4 h-4 text-sky-400 animate-spin-slow" />
          <span className="text-xs font-semibold text-slate-200">
            Pune Metropolitan Region (2016 ↔ 2026)
          </span>
          <span className="text-[10px] bg-sky-950 text-sky-300 font-mono px-2 py-0.5 rounded border border-sky-800/40">
            {mode.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Map Controls (Top Right) */}
      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        {/* Layer Selector */}
        <div className="relative">
          <button
            onClick={() => setTileMenuOpen(!tileMenuOpen)}
            className="p-2.5 bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl border border-slate-800 shadow-lg backdrop-blur transition"
            title="Map Tiles"
          >
            <Layers className="w-4 h-4" />
          </button>

          {tileMenuOpen && (
            <div className="absolute right-0 mt-2 w-44 bg-slate-900/95 border border-slate-800 rounded-xl p-1.5 shadow-2xl backdrop-blur-md text-xs space-y-1">
              {[
                { id: 'cartodb-dark', label: 'Dark Canvas (Esri)' },
                { id: 'osm', label: 'OpenStreetMap' },
                { id: 'satellite', label: 'Satellite (Esri Imagery)' },
                { id: 'cartodb-light', label: 'Light Canvas (Esri)' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => {
                    setActiveTile(opt.id as TileLayerType);
                    setTileMenuOpen(false);
                  }}
                  className={`w-full text-left px-3 py-1.5 rounded-lg transition ${
                    activeTile === opt.id
                      ? 'bg-sky-500/20 text-sky-300 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Zoom Controls */}
        <div className="flex flex-col bg-slate-900/90 border border-slate-800 rounded-xl shadow-lg backdrop-blur overflow-hidden">
          <button
            onClick={handleZoomIn}
            className="p-2.5 text-slate-300 hover:text-white hover:bg-slate-800 border-b border-slate-800/60 transition"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2.5 text-slate-300 hover:text-white hover:bg-slate-800 border-b border-slate-800/60 transition"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleReset}
            className="p-2.5 text-slate-300 hover:text-white hover:bg-slate-800 transition"
            title="Reset Extent"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Legend (Bottom Right) */}
      <div className="absolute bottom-5 right-5 z-10">
        <MapLegend />
      </div>
    </div>
  );
}
