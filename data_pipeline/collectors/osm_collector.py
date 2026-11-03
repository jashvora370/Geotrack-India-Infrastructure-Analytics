"""
OSM Road Network Collector
===========================
Fetches current road network using OSMnx and historical snapshots
using the ohsome API (Heidelberg Institute for Geoinformation Technology).

Data sources:
  - OSMnx: Current OSM road network (https://github.com/gboeing/osmnx)
  - ohsome API: Historical OSM data (https://api.ohsome.org/v1)

IMPORTANT: OSM historical data reflects MAPPING activity, not physical construction.
A road appearing in 2019 OSM data may have existed physically before 2019 but was
not yet mapped by OSM contributors. The OsmCompletenessService is used to flag
regions with known rapid mapping growth.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import osmnx as ox
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from shapely.geometry import shape
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OHSOME_BASE_URL = "https://api.ohsome.org/v1"
HIGHWAY_FILTER = "highway=* and type:way"
DEFAULT_NETWORK_TYPE = "all"
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2.0  # seconds base; actual = RETRY_BACKOFF ** attempt


def _build_session(retries: int = RETRY_ATTEMPTS) -> requests.Session:
    """Return a :class:`requests.Session` with automatic retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _bbox_to_ohsome_bboxes(bbox: tuple[float, float, float, float]) -> str:
    """Convert (west, south, east, north) → ohsome bboxes string."""
    west, south, east, north = bbox
    return f"{west},{south},{east},{north}"


class OsmCollector:
    """
    Collects OSM road network data using OSMnx (current) and the ohsome API
    (historical snapshots and time-series aggregations).

    Parameters
    ----------
    timeout : int
        HTTP timeout in seconds for ohsome API requests.
    """

    def __init__(self, timeout: int = 120) -> None:
        self.timeout = timeout
        self._session = _build_session()
        ox.settings.log_console = False
        ox.settings.use_cache = True
        logger.info("OsmCollector initialised (timeout=%ds)", timeout)

    # ------------------------------------------------------------------
    # Public API — current network via OSMnx
    # ------------------------------------------------------------------

    def collect_current_network(
        self,
        bbox: tuple[float, float, float, float],
        network_type: str = DEFAULT_NETWORK_TYPE,
    ) -> gpd.GeoDataFrame:
        """
        Download the current OSM road network for *bbox* using OSMnx.

        Parameters
        ----------
        bbox : tuple
            (west, south, east, north) in WGS-84 decimal degrees.
        network_type : str
            OSMnx network type: 'all', 'drive', 'walk', 'bike', etc.

        Returns
        -------
        gpd.GeoDataFrame
            Columns: osm_id, name, highway, surface, lanes, width, maxspeed,
            geometry, length_km.
        """
        west, south, east, north = bbox
        logger.info(
            "Collecting current OSM network (type=%s) for bbox=%s", network_type, bbox
        )
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                G = ox.graph_from_bbox(
                    north=north,
                    south=south,
                    east=east,
                    west=west,
                    network_type=network_type,
                    retain_all=True,
                )
                gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
                gdf = gdf_edges.reset_index()

                # Rename / standardise columns
                rename_map = {
                    "osmid": "osm_id",
                    "name": "name",
                    "highway": "highway",
                    "surface": "surface",
                    "lanes": "lanes",
                    "width": "width",
                    "maxspeed": "maxspeed",
                    "length": "length_m",
                }
                gdf = gdf.rename(columns={k: v for k, v in rename_map.items() if k in gdf.columns})

                # Ensure required columns exist
                for col in ["osm_id", "name", "highway", "surface", "lanes", "width", "maxspeed"]:
                    if col not in gdf.columns:
                        gdf[col] = None

                # Compute length_km
                if "length_m" in gdf.columns:
                    gdf["length_km"] = gdf["length_m"] / 1000.0
                else:
                    gdf = gdf.set_geometry("geometry")
                    gdf_proj = gdf.to_crs(epsg=32643)
                    gdf["length_km"] = gdf_proj.geometry.length / 1000.0

                # Flatten list-valued cells (OSMnx may return lists for multi-value tags)
                for col in ["highway", "surface", "lanes", "width", "maxspeed", "name"]:
                    if col in gdf.columns:
                        gdf[col] = gdf[col].apply(
                            lambda v: v[0] if isinstance(v, list) else v
                        )

                keep_cols = [
                    "osm_id", "name", "highway", "surface", "lanes",
                    "width", "maxspeed", "geometry", "length_km",
                ]
                existing = [c for c in keep_cols if c in gdf.columns]
                gdf = gdf[existing].copy()
                logger.info(
                    "Current network collected: %d edges (%.2f km total)",
                    len(gdf),
                    gdf["length_km"].sum() if "length_km" in gdf.columns else 0,
                )
                return gdf

            except Exception as exc:
                logger.warning(
                    "Attempt %d/%d failed for collect_current_network: %s",
                    attempt, RETRY_ATTEMPTS, exc,
                )
                if attempt < RETRY_ATTEMPTS:
                    sleep_time = RETRY_BACKOFF ** attempt
                    logger.info("Retrying in %.1f seconds…", sleep_time)
                    time.sleep(sleep_time)
                else:
                    logger.error("All retry attempts exhausted for collect_current_network.")
                    raise

    # ------------------------------------------------------------------
    # Public API — historical snapshots via ohsome
    # ------------------------------------------------------------------

    def collect_historical_snapshot(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
        month: int = 6,
    ) -> gpd.GeoDataFrame:
        """
        Fetch a historical OSM road network snapshot using the ohsome API.

        Parameters
        ----------
        bbox : tuple
            (west, south, east, north) in WGS-84.
        year : int
            Snapshot year.
        month : int
            Snapshot month (default: 6 → June = mid-year).

        Returns
        -------
        gpd.GeoDataFrame
            Road geometries at the given timestamp.

        Notes
        -----
        Data reflects *mapping* activity, not physical construction.
        """
        timestamp = f"{year}-{month:02d}-01"
        bboxes = _bbox_to_ohsome_bboxes(bbox)
        url = f"{OHSOME_BASE_URL}/elements/geometry"
        payload = {
            "bboxes": bboxes,
            "filter": HIGHWAY_FILTER,
            "time": timestamp,
            "properties": "tags",
        }
        logger.info(
            "Fetching ohsome snapshot for year=%d (timestamp=%s)", year, timestamp
        )

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = self._session.post(url, data=payload, timeout=self.timeout)
                response.raise_for_status()
                geojson = response.json()
                features = geojson.get("features", [])
                if not features:
                    logger.warning("No features returned for timestamp=%s", timestamp)
                    return gpd.GeoDataFrame(
                        columns=["osm_id", "name", "highway", "surface", "geometry"],
                        geometry="geometry",
                        crs="EPSG:4326",
                    )

                records: list[dict[str, Any]] = []
                for feat in features:
                    props = feat.get("properties", {})
                    tags = props.get("@tags", props)
                    records.append(
                        {
                            "osm_id": props.get("@osmId", props.get("id")),
                            "name": tags.get("name"),
                            "highway": tags.get("highway"),
                            "surface": tags.get("surface"),
                            "lanes": tags.get("lanes"),
                            "width": tags.get("width"),
                            "maxspeed": tags.get("maxspeed"),
                            "geometry": shape(feat["geometry"]) if feat.get("geometry") else None,
                        }
                    )

                gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
                gdf_proj = gdf.to_crs(epsg=32643)
                gdf["length_km"] = gdf_proj.geometry.length / 1000.0
                logger.info(
                    "Snapshot year=%d: %d features (%.2f km)",
                    year, len(gdf), gdf["length_km"].sum(),
                )
                return gdf

            except requests.exceptions.HTTPError as exc:
                logger.warning(
                    "HTTP error on attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc
                )
            except Exception as exc:
                logger.warning(
                    "Error on attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc
                )
            if attempt < RETRY_ATTEMPTS:
                sleep_time = RETRY_BACKOFF ** attempt
                logger.info("Retrying in %.1f seconds…", sleep_time)
                time.sleep(sleep_time)

        logger.error("All retry attempts exhausted for collect_historical_snapshot.")
        raise RuntimeError(
            f"Failed to collect ohsome snapshot for year={year} after {RETRY_ATTEMPTS} attempts."
        )

    # ------------------------------------------------------------------
    # Public API — time-series via ohsome /elements/length
    # ------------------------------------------------------------------

    def collect_timeseries_length(
        self,
        bbox: tuple[float, float, float, float],
        start_year: int = 2016,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """
        Fetch yearly road length (in km) from ohsome /elements/length.

        Parameters
        ----------
        bbox : tuple
            (west, south, east, north).
        start_year : int
            First year (inclusive).
        end_year : int
            Last year (inclusive).

        Returns
        -------
        pd.DataFrame
            Columns: year, length_km.
        """
        bboxes = _bbox_to_ohsome_bboxes(bbox)
        time_range = f"{start_year}-01-01/{end_year}-01-01/P1Y"
        url = f"{OHSOME_BASE_URL}/elements/length"
        payload = {
            "bboxes": bboxes,
            "filter": HIGHWAY_FILTER,
            "time": time_range,
        }
        logger.info(
            "Fetching ohsome length timeseries %d–%d", start_year, end_year
        )

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = self._session.post(url, data=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                results = data.get("result", [])
                rows = []
                for item in results:
                    ts = item.get("timestamp", "")
                    year = int(ts[:4]) if ts else None
                    length_m = item.get("value", 0.0)
                    rows.append({"year": year, "length_km": length_m / 1000.0})
                df = pd.DataFrame(rows).dropna(subset=["year"])
                df["year"] = df["year"].astype(int)
                logger.info("Timeseries collected: %d data points", len(df))
                return df

            except requests.exceptions.HTTPError as exc:
                logger.warning("HTTP error attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc)
            except Exception as exc:
                logger.warning("Error attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc)
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF ** attempt)

        raise RuntimeError(
            f"Failed to collect length timeseries after {RETRY_ATTEMPTS} attempts."
        )

    # ------------------------------------------------------------------
    # Public API — road count time-series
    # ------------------------------------------------------------------

    def collect_road_count_timeseries(
        self,
        bbox: tuple[float, float, float, float],
        start_year: int = 2016,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """
        Fetch yearly road *count* from ohsome /elements/count.

        Returns
        -------
        pd.DataFrame
            Columns: year, road_count.
        """
        bboxes = _bbox_to_ohsome_bboxes(bbox)
        time_range = f"{start_year}-01-01/{end_year}-01-01/P1Y"
        url = f"{OHSOME_BASE_URL}/elements/count"
        payload = {
            "bboxes": bboxes,
            "filter": HIGHWAY_FILTER,
            "time": time_range,
        }
        logger.info(
            "Fetching ohsome count timeseries %d–%d", start_year, end_year
        )

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = self._session.post(url, data=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                results = data.get("result", [])
                rows = []
                for item in results:
                    ts = item.get("timestamp", "")
                    year = int(ts[:4]) if ts else None
                    count = item.get("value", 0)
                    rows.append({"year": year, "road_count": int(count)})
                df = pd.DataFrame(rows).dropna(subset=["year"])
                df["year"] = df["year"].astype(int)
                logger.info("Count timeseries collected: %d data points", len(df))
                return df

            except requests.exceptions.HTTPError as exc:
                logger.warning("HTTP error attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc)
            except Exception as exc:
                logger.warning("Error attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc)
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF ** attempt)

        raise RuntimeError(
            f"Failed to collect count timeseries after {RETRY_ATTEMPTS} attempts."
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def save_to_geojson(gdf: gpd.GeoDataFrame, filepath: str | Path) -> None:
        """
        Persist a GeoDataFrame to GeoJSON.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Data to save.
        filepath : str or Path
            Destination file path (parent dirs created automatically).
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(str(filepath), driver="GeoJSON")
        logger.info("Saved GeoDataFrame (%d rows) → %s", len(gdf), filepath)

    @staticmethod
    def save_timeseries_csv(df: pd.DataFrame, filepath: str | Path) -> None:
        """
        Persist a DataFrame to CSV.

        Parameters
        ----------
        df : pd.DataFrame
            Time-series data.
        filepath : str or Path
            Destination file path.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(str(filepath), index=False)
        logger.info("Saved DataFrame (%d rows) → %s", len(df), filepath)
