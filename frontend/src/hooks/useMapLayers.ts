'use client';

import { useState, useCallback } from 'react';
import type { MapLayerConfig, MapMode, TileLayerType } from '@/lib/types';

const DEFAULT_LAYERS: MapLayerConfig = {
  roads2016: false,
  roads2026: true,
  newRoads: true,
  removedRoads: true,
  widenedRoads: true,
  highways: true,
  builtUp: false,
  ndvi: false,
};

export function useMapLayers() {
  const [layers, setLayers] = useState<MapLayerConfig>(DEFAULT_LAYERS);
  const [mode, setMode] = useState<MapMode>('diff');
  const [tileLayer, setTileLayer] = useState<TileLayerType>('cartodb-dark');
  const [yearSlider, setYearSlider] = useState<number>(2026);

  const toggleLayer = useCallback((key: keyof MapLayerConfig) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const setLayer = useCallback((key: keyof MapLayerConfig, value: boolean) => {
    setLayers((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetLayers = useCallback(() => {
    setLayers(DEFAULT_LAYERS);
  }, []);

  const setMapMode = useCallback((newMode: MapMode) => {
    setMode(newMode);
    // Auto-adjust layer visibility based on mode
    if (newMode === '2016') {
      setLayers((prev) => ({
        ...prev,
        roads2016: true,
        roads2026: false,
        newRoads: false,
        removedRoads: false,
        widenedRoads: false,
      }));
    } else if (newMode === '2026') {
      setLayers((prev) => ({
        ...prev,
        roads2016: false,
        roads2026: true,
        newRoads: false,
        removedRoads: false,
        widenedRoads: false,
      }));
    } else {
      setLayers(DEFAULT_LAYERS);
    }
  }, []);

  return {
    layers,
    mode,
    tileLayer,
    yearSlider,
    toggleLayer,
    setLayer,
    resetLayers,
    setMode: setMapMode,
    setTileLayer,
    setYearSlider,
  };
}
