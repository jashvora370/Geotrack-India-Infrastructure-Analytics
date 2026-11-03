"""
Road Network Processor
========================
Cleans, standardises, and enriches raw OSM road network GeoDataFrames for
analysis.  Reprojects to EPSG:32643 (UTM Zone 43N) which provides accurate
metric measurements over the Pune / Maharashtra study area.

OSM highway tag → Indian road classification mapping is based on:
  - IRC:SP:73 (Rural Road Design)
  - IRC:SP:84 (Urban Road Design)
  - NHAI road classification scheme
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.validation import make_valid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Target CRS for metric measurements — UTM Zone 43N covers Pune/Maharashtra
TARGET_CRS = "EPSG:32643"
SOURCE_CRS = "EPSG:4326"

# OSM highway tag → Indian road classification
HIGHWAY_CLASSIFICATION: dict[str, str] = {
    "motorway": "National Highway",
    "trunk": "National Highway",
    "primary": "State Highway",
    "secondary": "Major District Road",
    "tertiary": "Other District Road",
    "unclassified": "Local/Village Road",
    "residential": "Local/Village Road",
    "motorway_link": "Highway Link",
    "trunk_link": "Highway Link",
    "primary_link": "Highway Link",
    "secondary_link": "Highway Link",
    "tertiary_link": "Highway Link",
    "living_street": "Service Road",
    "service": "Service Road",
    "track": "Unpaved Track",
    "path": "Footpath",
    "footway": "Footpath",
    "cycleway": "Cycleway",
    "pedestrian": "Pedestrian Zone",
    "steps": "Footpath",
    "road": "Unclassified",
}

# Default widths (m) per road class when no tag information is available
DEFAULT_WIDTH_M: dict[str, float] = {
    "National Highway": 45.0,
    "State Highway": 20.0,
    "Major District Road": 12.0,
    "Other District Road": 9.0,
    "Local/Village Road": 5.5,
    "Highway Link": 8.0,
    "Service Road": 4.0,
    "Unpaved Track": 3.5,
    "Footpath": 2.0,
    "Cycleway": 2.0,
    "Pedestrian Zone": 6.0,
    "Unclassified": 6.0,
}


class RoadNetworkProcessor:
    """
    Processes raw OSM road network GeoDataFrames into analysis-ready format.

    Parameters
    ----------
    target_crs : str
        EPSG code of the projected CRS to use for metric calculations.
        Default: EPSG:32643 (UTM Zone 43N).
    """

    def __init__(self, target_crs: str = TARGET_CRS) -> None:
        self.target_crs = target_crs
        logger.info("RoadNetworkProcessor initialised (target_crs=%s)", target_crs)

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    def process_raw_network(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Clean, standardise and reproject a raw OSM GeoDataFrame.

        Steps:
          1. Drop rows with null geometry.
          2. Validate and repair geometries.
          3. Flatten list-valued columns (OSMnx multi-value tags).
          4. Reproject to self.target_crs.
          5. Ensure required columns are present.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Raw GeoDataFrame from OsmCollector.

        Returns
        -------
        gpd.GeoDataFrame
            Cleaned and reprojected GeoDataFrame.
        """
        logger.info("Processing raw network: %d rows", len(gdf))
        gdf = gdf.copy()

        # 1. Drop null geometry
        null_geom = gdf.geometry.isna()
        if null_geom.any():
            logger.warning("Dropping %d rows with null geometry", null_geom.sum())
            gdf = gdf[~null_geom].copy()

        # 2. Validate geometries
        gdf["geometry"] = gdf["geometry"].apply(
            lambda geom: make_valid(geom) if geom is not None and not geom.is_valid else geom
        )

        # 3. Flatten list-valued cells
        for col in gdf.columns:
            if col == "geometry":
                continue
            gdf[col] = gdf[col].apply(
                lambda v: v[0] if isinstance(v, list) and len(v) > 0 else v
            )

        # 4. Ensure required columns
        for col in ["osm_id", "name", "highway", "surface", "lanes", "width", "maxspeed"]:
            if col not in gdf.columns:
                gdf[col] = None

        # 5. Reproject
        if gdf.crs is None:
            gdf = gdf.set_crs(SOURCE_CRS)
        if str(gdf.crs) != self.target_crs:
            gdf = gdf.to_crs(self.target_crs)

        logger.info("Processing complete: %d valid rows (CRS=%s)", len(gdf), self.target_crs)
        return gdf

    # ------------------------------------------------------------------
    # Length calculation
    # ------------------------------------------------------------------

    def calculate_lengths(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Compute accurate road segment length in km using the projected CRS.

        If the GeoDataFrame is not already in a projected CRS, it is
        reprojected temporarily for measurement.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame

        Returns
        -------
        gpd.GeoDataFrame
            With added / updated column: length_km.
        """
        gdf = gdf.copy()
        if gdf.crs is None or gdf.crs.is_geographic:
            logger.info("Reprojecting to %s for length calculation", self.target_crs)
            gdf_proj = gdf.to_crs(self.target_crs)
        else:
            gdf_proj = gdf
        gdf["length_km"] = gdf_proj.geometry.length / 1000.0
        logger.debug(
            "Lengths calculated: total=%.2f km over %d segments",
            gdf["length_km"].sum(), len(gdf),
        )
        return gdf

    # ------------------------------------------------------------------
    # Road classification
    # ------------------------------------------------------------------

    def classify_roads(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Map OSM ``highway`` tags to the Indian road classification scheme.

        Unmapped tags are labelled 'Other'.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame

        Returns
        -------
        gpd.GeoDataFrame
            With added column: road_class.
        """
        gdf = gdf.copy()
        if "highway" not in gdf.columns:
            logger.warning("'highway' column missing; all roads will be classified as 'Other'.")
            gdf["road_class"] = "Other"
            return gdf

        gdf["road_class"] = gdf["highway"].map(HIGHWAY_CLASSIFICATION).fillna("Other")
        class_counts = gdf["road_class"].value_counts()
        logger.info("Road classification summary:\n%s", class_counts.to_string())
        return gdf

    # ------------------------------------------------------------------
    # Width estimation
    # ------------------------------------------------------------------

    def estimate_widths(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Estimate road width (metres) in priority order:

          1. Existing OSM ``width`` tag (HIGH confidence).
          2. OSM ``lanes`` × lane width for road class (MEDIUM confidence).
          3. Road class default (LOW confidence → ESTIMATED).

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Must contain road_class column (run classify_roads first).

        Returns
        -------
        gpd.GeoDataFrame
            With added columns: width_m, width_confidence.
        """
        from .width_estimator import WidthEstimator  # relative import

        estimator = WidthEstimator()
        gdf = gdf.copy()

        width_m_list: list[float] = []
        confidence_list: list[str] = []

        for _, row in gdf.iterrows():
            w, conf = estimator.estimate_from_osm_attributes(row)
            width_m_list.append(w)
            confidence_list.append(conf)

        gdf["width_m"] = width_m_list
        gdf["width_confidence"] = confidence_list
        logger.info(
            "Width estimation complete. Confidence breakdown:\n%s",
            pd.Series(confidence_list).value_counts().to_string(),
        )
        return gdf

    # ------------------------------------------------------------------
    # Density
    # ------------------------------------------------------------------

    def compute_road_density(
        self,
        gdf: gpd.GeoDataFrame,
        bbox_area_km2: float,
    ) -> float:
        """
        Compute road density (km of road per km² of study area).

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
        bbox_area_km2 : float
            Total study area in km².

        Returns
        -------
        float
            Road density in km/km².
        """
        if "length_km" not in gdf.columns:
            gdf = self.calculate_lengths(gdf)
        total_km = gdf["length_km"].sum()
        density = total_km / bbox_area_km2 if bbox_area_km2 > 0 else float("nan")
        logger.info(
            "Road density: %.4f km/km² (total=%.2f km, area=%.2f km²)",
            density, total_km, bbox_area_km2,
        )
        return density

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_stats(
        self,
        gdf: gpd.GeoDataFrame,
        classification_col: str = "road_class",
    ) -> dict[str, Any]:
        """
        Return a comprehensive KPI dictionary for the road network.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
        classification_col : str
            Column name containing road classification labels.

        Returns
        -------
        dict
            Keys: total_length_km, segment_count, classification_breakdown,
            avg_length_km, surface_breakdown, lane_stats, width_stats.
        """
        if "length_km" not in gdf.columns:
            gdf = self.calculate_lengths(gdf)

        total_km = float(gdf["length_km"].sum())
        segment_count = len(gdf)

        # Classification breakdown
        if classification_col in gdf.columns:
            class_breakdown: dict[str, dict] = {}
            for cls, group in gdf.groupby(classification_col):
                class_breakdown[str(cls)] = {
                    "count": len(group),
                    "length_km": round(float(group["length_km"].sum()), 3),
                    "pct": round(float(group["length_km"].sum() / total_km * 100), 2) if total_km > 0 else 0.0,
                }
        else:
            class_breakdown = {}

        # Surface breakdown
        surface_counts: dict[str, int] = {}
        if "surface" in gdf.columns:
            surface_counts = gdf["surface"].fillna("unknown").value_counts().to_dict()

        # Lane stats
        lane_stats: dict[str, float] = {}
        if "lanes" in gdf.columns:
            lane_series = pd.to_numeric(gdf["lanes"], errors="coerce").dropna()
            if not lane_series.empty:
                lane_stats = {
                    "mean": round(float(lane_series.mean()), 2),
                    "min": int(lane_series.min()),
                    "max": int(lane_series.max()),
                    "median": float(lane_series.median()),
                }

        # Width stats
        width_stats: dict[str, float] = {}
        if "width_m" in gdf.columns:
            w_series = pd.to_numeric(gdf["width_m"], errors="coerce").dropna()
            if not w_series.empty:
                width_stats = {
                    "mean_m": round(float(w_series.mean()), 2),
                    "min_m": round(float(w_series.min()), 2),
                    "max_m": round(float(w_series.max()), 2),
                    "median_m": round(float(w_series.median()), 2),
                }

        stats = {
            "total_length_km": round(total_km, 3),
            "segment_count": segment_count,
            "avg_segment_length_km": round(total_km / segment_count, 4) if segment_count > 0 else 0.0,
            "classification_breakdown": class_breakdown,
            "surface_breakdown": {str(k): int(v) for k, v in surface_counts.items()},
            "lane_stats": lane_stats,
            "width_stats": width_stats,
        }
        logger.info(
            "Aggregate stats: %d segments, %.2f km total", segment_count, total_km
        )
        return stats
