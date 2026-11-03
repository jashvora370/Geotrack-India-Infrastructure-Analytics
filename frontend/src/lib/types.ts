// ─── Region Types ──────────────────────────────────────────────────────────────
export interface State {
  id: number;
  name: string;
  code: string;
  area_km2: number;
}

export interface District {
  id: number;
  name: string;
  state: string;
  area_km2: number;
}

export interface City {
  id: number;
  name: string;
  district: string;
  state: string;
  population?: number;
}

export interface Region {
  id: number;
  name: string;
  level: 'state' | 'district' | 'city';
  parent?: string;
  bbox?: [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
}

export interface RegionBoundary {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

// ─── GeoJSON Types ─────────────────────────────────────────────────────────────
export interface GeoJSONFeature {
  type: 'Feature';
  geometry: {
    type: string;
    coordinates: number[] | number[][] | number[][][];
  };
  properties: Record<string, unknown>;
}

export interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

// ─── Road Network Types ────────────────────────────────────────────────────────
export interface RoadSegment {
  id: string;
  osmId?: string;
  geometry: {
    type: 'LineString';
    coordinates: [number, number][];
  };
  properties: {
    name?: string;
    highway?: string;
    lanes?: number;
    width?: number;
    surface?: string;
    year?: number;
    changeType?: 'existing' | 'new' | 'removed' | 'widened';
    length_m?: number;
  };
}

export interface NetworkStats {
  regionId: number;
  year: number;
  totalLength_km: number;
  totalSegments: number;
  avgWidth_m?: number;
  roadDensity_km_per_km2?: number;
  classification: {
    motorway: number;
    trunk: number;
    primary: number;
    secondary: number;
    tertiary: number;
    residential: number;
    unclassified: number;
    other: number;
  };
}

export interface ChangeResult {
  regionId: number;
  fromYear: number;
  toYear: number;
  newRoads_km: number;
  removedRoads_km: number;
  widenedRoads_km: number;
  totalGrowth_km: number;
  growthPct: number;
  newSegmentsCount: number;
  removedSegmentsCount: number;
  widenedSegmentsCount: number;
  newRoadsGeoJSON?: GeoJSONCollection;
  removedRoadsGeoJSON?: GeoJSONCollection;
  widenedRoadsGeoJSON?: GeoJSONCollection;
}

export interface AnalysisJob {
  jobId: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  result?: ChangeResult;
}

// ─── Analytics Types ───────────────────────────────────────────────────────────
export interface DashboardData {
  regionId: number;
  regionName: string;
  updatedAt: string;
  kpis: {
    roadLength2016_km: number | null;
    roadLength2026_km: number | null;
    roadGrowthPct: number | null;
    newSegments: number | null;
    roadDensity_km_per_km2: number | null;
    avgRoadWidth_m: number | null;
    builtUpGrowthPct: number | null;
    greenCoverChangePct: number | null;
  };
  confidence: {
    roadLength: ConfidenceLevel;
    roadWidth: ConfidenceLevel;
    builtUp: ConfidenceLevel;
    greenCover: ConfidenceLevel;
  };
  dataSource: {
    roadNetwork: string;
    builtUp: string;
    satellite: string;
  };
}

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'ESTIMATED';

export interface Insight {
  id: string;
  category: 'road_growth' | 'urban_expansion' | 'connectivity' | 'land_use' | 'general';
  headline: string;
  supportingText: string;
  value?: number;
  unit?: string;
  confidence: ConfidenceLevel;
  source: string;
  iconName?: string;
}

export interface TimeseriesData {
  year: number;
  totalLength_km?: number | null;
  highways_km?: number | null;
  primary_km?: number | null;
  secondary_km?: number | null;
  local_km?: number | null;
  builtUpPct?: number | null;
  vegetationPct?: number | null;
  agriculturePct?: number | null;
  ndvi?: number | null;
  waterPct?: number | null;
}

export interface ClassificationData {
  year: number;
  data: {
    label: string;
    length_km: number;
    pct: number;
    color: string;
  }[];
}

export interface ConnectivityData {
  year2016: NetworkMetrics;
  year2026: NetworkMetrics;
}

export interface NetworkMetrics {
  avgDegree: number | null;
  clusteringCoefficient: number | null;
  betweennessCentrality: number | null;
  networkDensity: number | null;
  nodeCount: number | null;
  edgeCount: number | null;
}

// ─── Width Types ────────────────────────────────────────────────────────────────
export interface WidthData {
  regionId: number;
  year: number;
  distribution: {
    label: string;
    range: string;
    count_2016: number;
    count_2026: number;
    pct_2016: number;
    pct_2026: number;
  }[];
  byClassification: {
    classification: string;
    avgWidth_m: number | null;
    minWidth_m: number | null;
    maxWidth_m: number | null;
    confidence: ConfidenceLevel;
  }[];
  overall: {
    avg_2016: number | null;
    avg_2026: number | null;
    max_2016: number | null;
    max_2026: number | null;
    min_2016: number | null;
    min_2026: number | null;
  };
}

// ─── Land Use Types ─────────────────────────────────────────────────────────────
export interface LandUseData {
  regionId: number;
  year: number;
  builtUp_km2: number | null;
  vegetation_km2: number | null;
  agriculture_km2: number | null;
  water_km2: number | null;
  barren_km2: number | null;
  total_km2: number | null;
  source: string;
}

// ─── Data Source Types ──────────────────────────────────────────────────────────
export interface DataSource {
  id: string;
  name: string;
  shortName: string;
  description: string;
  type: 'osm' | 'satellite' | 'census' | 'government' | 'derived';
  coverage: string;
  temporalRange: string;
  resolution?: string;
  reliability: 'HIGH' | 'MEDIUM' | 'LOW';
  url?: string;
  license?: string;
  lastUpdated?: string;
  status: 'active' | 'partial' | 'unavailable';
}

// ─── UI State Types ─────────────────────────────────────────────────────────────
export interface SelectedRegion {
  state?: State;
  district?: District;
  city?: City;
  level: 'none' | 'state' | 'district' | 'city';
  name: string;
  regionId?: number;
  bbox?: [number, number, number, number];
}

export interface MapLayerConfig {
  roads2016: boolean;
  roads2026: boolean;
  newRoads: boolean;
  removedRoads: boolean;
  widenedRoads: boolean;
  highways: boolean;
  builtUp: boolean;
  ndvi: boolean;
}

export type MapMode = '2016' | '2026' | 'diff';

export type TileLayerType = 'osm' | 'cartodb-dark' | 'cartodb-light' | 'satellite';
