'use client';

import { useState, useCallback } from 'react';
import type { SelectedRegion, State, District, City } from '@/lib/types';

const DEFAULT_REGION: SelectedRegion = {
  level: 'none',
  name: 'Select a Region',
};

export function useRegion() {
  const [selectedRegion, setSelectedRegion] =
    useState<SelectedRegion>(DEFAULT_REGION);

  const selectState = useCallback((state: State) => {
    setSelectedRegion({
      level: 'state',
      name: state.name,
      state,
      bbox: undefined,
    });
  }, []);

  const selectDistrict = useCallback(
    (district: District, parentState: State) => {
      setSelectedRegion((prev) => ({
        level: 'district',
        name: `${district.name}, ${parentState.name}`,
        state: parentState,
        district,
      }));
    },
    []
  );

  const selectCity = useCallback(
    (city: City, parentDistrict: District, parentState: State) => {
      setSelectedRegion({
        level: 'city',
        name: `${city.name}, ${parentDistrict.name}`,
        state: parentState,
        district: parentDistrict,
        city,
      });
    },
    []
  );

  const clearRegion = useCallback(() => {
    setSelectedRegion(DEFAULT_REGION);
  }, []);

  const getBreadcrumb = useCallback(() => {
    const parts: string[] = ['India'];
    if (selectedRegion.state) parts.push(selectedRegion.state.name);
    if (selectedRegion.district) parts.push(selectedRegion.district.name);
    if (selectedRegion.city) parts.push(selectedRegion.city.name);
    return parts;
  }, [selectedRegion]);

  return {
    selectedRegion,
    selectState,
    selectDistrict,
    selectCity,
    clearRegion,
    getBreadcrumb,
    hasRegion: selectedRegion.level !== 'none',
  };
}
