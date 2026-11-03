import axios, { AxiosInstance } from 'axios';
import type {
  State,
  District,
  City,
  Region,
  GeoJSONCollection,
  AnalysisJob,
  NetworkStats,
  ChangeResult,
  DashboardData,
  Insight,
  TimeseriesData,
  ClassificationData,
  ConnectivityData,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unknown error occurred';
    return Promise.reject(new Error(message));
  }
);

export const api = {
  // ─── Regions ──────────────────────────────────────────────────────────────
  regions: {
    async getStates(): Promise<State[]> {
      const res = await client.get<State[]>('/api/v1/regions/states');
      return res.data;
    },

    async getDistricts(state: string): Promise<District[]> {
      const res = await client.get<District[]>(`/api/v1/regions/districts`, {
        params: { state },
      });
      return res.data;
    },

    async getCities(district: string): Promise<City[]> {
      const res = await client.get<City[]>(`/api/v1/regions/cities`, {
        params: { district },
      });
      return res.data;
    },

    async getBoundary(name: string, level: string): Promise<GeoJSONCollection> {
      const res = await client.get<GeoJSONCollection>(`/api/v1/regions/boundary`, {
        params: { name, level },
      });
      return res.data;
    },

    async search(query: string): Promise<Region[]> {
      const res = await client.get<Region[]>(`/api/v1/regions/search`, {
        params: { q: query },
      });
      return res.data;
    },
  },

  // ─── Road Network ─────────────────────────────────────────────────────────
  roadNetwork: {
    async analyze(
      region: string,
      bbox: number[],
      years: number[]
    ): Promise<AnalysisJob> {
      const res = await client.post<AnalysisJob>('/api/v1/road-network/analyze', {
        region,
        bbox,
        years,
      });
      return res.data;
    },

    async getJobStatus(jobId: string): Promise<AnalysisJob> {
      const res = await client.get<AnalysisJob>(`/api/v1/road-network/jobs/${jobId}`);
      return res.data;
    },

    async getStats(regionId: number): Promise<NetworkStats[]> {
      const res = await client.get<NetworkStats[]>(
        `/api/v1/road-network/stats/${regionId}`
      );
      return res.data;
    },

    async getChanges(
      regionId: number,
      fromYear: number,
      toYear: number
    ): Promise<ChangeResult> {
      const res = await client.get<ChangeResult>(
        `/api/v1/road-network/changes/${regionId}`,
        { params: { from_year: fromYear, to_year: toYear } }
      );
      return res.data;
    },

    async getSegments(
      regionId: number,
      year: number
    ): Promise<GeoJSONCollection> {
      const res = await client.get<GeoJSONCollection>(
        `/api/v1/road-network/segments/${regionId}`,
        { params: { year } }
      );
      return res.data;
    },

    async getNewRoads(regionId: number): Promise<GeoJSONCollection> {
      const res = await client.get<GeoJSONCollection>(
        `/api/v1/road-network/new-roads/${regionId}`
      );
      return res.data;
    },

    async getOhsomeTimeseries(regionId: number): Promise<TimeseriesData[]> {
      const res = await client.get<TimeseriesData[]>(
        `/api/v1/road-network/ohsome-timeseries/${regionId}`
      );
      return res.data;
    },
  },

  // ─── Analytics ────────────────────────────────────────────────────────────
  analytics: {
    async getDashboard(regionId: number): Promise<DashboardData> {
      const res = await client.get<DashboardData>(
        `/api/v1/analytics/dashboard/${regionId}`
      );
      return res.data;
    },

    async getInsights(regionId: number): Promise<Insight[]> {
      const res = await client.get<Insight[]>(
        `/api/v1/analytics/insights/${regionId}`
      );
      return res.data;
    },

    async getTimeseries(regionId: number): Promise<TimeseriesData[]> {
      const res = await client.get<TimeseriesData[]>(
        `/api/v1/analytics/timeseries/${regionId}`
      );
      return res.data;
    },

    async getRoadClassification(
      regionId: number,
      year: number
    ): Promise<ClassificationData> {
      const res = await client.get<ClassificationData>(
        `/api/v1/analytics/road-classification/${regionId}`,
        { params: { year } }
      );
      return res.data;
    },

    async getConnectivity(regionId: number): Promise<ConnectivityData> {
      const res = await client.get<ConnectivityData>(
        `/api/v1/analytics/connectivity/${regionId}`
      );
      return res.data;
    },
  },

  // ─── Reports ──────────────────────────────────────────────────────────────
  reports: {
    async generatePDF(regionId: number): Promise<Blob> {
      const res = await client.get(`/api/v1/reports/pdf/${regionId}`, {
        responseType: 'blob',
        timeout: 60000,
      });
      return res.data;
    },

    async generateCSV(regionId: number): Promise<Blob> {
      const res = await client.get(`/api/v1/reports/csv/${regionId}`, {
        responseType: 'blob',
      });
      return res.data;
    },

    async generateExcel(regionId: number): Promise<Blob> {
      const res = await client.get(`/api/v1/reports/excel/${regionId}`, {
        responseType: 'blob',
      });
      return res.data;
    },
  },
};

// Utility: download blob
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
