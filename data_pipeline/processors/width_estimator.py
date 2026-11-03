"""
GeoTrack India — Road Width Estimator (Data Pipeline)
======================================================
Estimates road widths and width classifications for geospatial datasets.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

logger = logging.getLogger(__name__)

# Standard lane widths based on IRC standards
IRC_LANE_WIDTHS = {
    "motorway": 3.75,
    "trunk": 3.75,
    "primary": 3.50,
    "secondary": 3.00,
    "tertiary": 3.00,
    "unclassified": 2.75,
    "residential": 2.75,
    "living_street": 2.50,
    "service": 2.50,
    "track": 2.50,
}

IRC_DEFAULT_WIDTHS = {
    "motorway": 24.0,
    "trunk": 14.0,
    "primary": 10.5,
    "secondary": 7.0,
    "tertiary": 5.5,
    "unclassified": 4.0,
    "residential": 4.0,
    "living_street": 3.5,
    "service": 3.0,
    "track": 2.5,
}


class WidthEstimator:
    """Estimates and classifies road widths based on OSM attributes and geometric defaults."""

    def __init__(self):
        pass

    def estimate_from_row(self, row: pd.Series) -> Tuple[Optional[float], str, str]:
        """
        Estimate road width for a single row.
        Returns: (width_m, confidence, method)
        """
        # 1. Direct width tag
        width_val = row.get("width")
        if pd.notna(width_val):
            try:
                clean_w = str(width_val).strip().replace("m", "").replace(",", ".")
                w = float(clean_w)
                if 1.0 <= w <= 100.0:
                    return w, "HIGH", "OSM width tag"
            except (ValueError, TypeError):
                pass

        # 2. Lanes count
        lanes_val = row.get("lanes")
        highway_val = str(row.get("highway", "unclassified")).split(";")[0].split(",")[0].strip().lower()
        if pd.notna(lanes_val):
            try:
                lanes = int(float(str(lanes_val).split(";")[0].strip()))
                if 1 <= lanes <= 16:
                    base_hw = highway_val.replace("_link", "")
                    lane_w = IRC_LANE_WIDTHS.get(base_hw, 2.75)
                    median = 3.0 if lanes >= 4 and base_hw in ("motorway", "trunk", "primary") else 0.0
                    shoulder = 1.0 if base_hw in ("motorway", "trunk") else 0.5
                    total_w = lanes * lane_w + median + shoulder
                    return round(total_w, 2), "MEDIUM", "Lanes * IRC lane width"
            except (ValueError, TypeError):
                pass

        # 3. Default from highway classification
        base_hw = highway_val.replace("_link", "")
        if base_hw in IRC_DEFAULT_WIDTHS:
            return IRC_DEFAULT_WIDTHS[base_hw], "LOW", "IRC highway classification standard"

        return 4.0, "ESTIMATED", "Default regional fallback"

    def process_network(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process an entire GeoDataFrame and attach width_m, width_confidence, width_method."""
        if gdf.empty:
            gdf["width_m"] = pd.Series(dtype=float)
            gdf["width_confidence"] = pd.Series(dtype=str)
            gdf["width_method"] = pd.Series(dtype=str)
            gdf["width_class"] = pd.Series(dtype=str)
            return gdf

        gdf = gdf.copy()
        widths = []
        confidences = []
        methods = []
        classes = []

        for _, row in gdf.iterrows():
            w, conf, meth = self.estimate_from_row(row)
            widths.append(w)
            confidences.append(conf)
            methods.append(meth)
            classes.append(self.classify_width(w))

        gdf["width_m"] = widths
        gdf["width_confidence"] = confidences
        gdf["width_method"] = methods
        gdf["width_class"] = classes
        return gdf

    @staticmethod
    def classify_width(width_m: Optional[float]) -> str:
        """Classify into standard IRC categories."""
        if width_m is None or np.isnan(width_m):
            return "Unknown"
        if width_m < 5.5:
            return "Narrow"
        if width_m < 10.0:
            return "Medium"
        if width_m < 20.0:
            return "Wide"
        if width_m < 45.0:
            return "Arterial"
        return "Highway"

    def compute_distribution(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Compute aggregate width statistics."""
        if gdf.empty or "width_m" not in gdf.columns:
            return {
                "avg_width_m": 0.0,
                "median_width_m": 0.0,
                "min_width_m": 0.0,
                "max_width_m": 0.0,
                "pct_narrow": 0.0,
                "pct_medium": 0.0,
                "pct_wide": 0.0,
                "pct_arterial": 0.0,
                "pct_highway": 0.0,
            }

        valid_widths = gdf["width_m"].dropna()
        if valid_widths.empty:
            return {}

        counts = gdf["width_class"].value_counts(normalize=True) * 100
        return {
            "avg_width_m": round(float(valid_widths.mean()), 2),
            "median_width_m": round(float(valid_widths.median()), 2),
            "min_width_m": round(float(valid_widths.min()), 2),
            "max_width_m": round(float(valid_widths.max()), 2),
            "pct_narrow": round(float(counts.get("Narrow", 0.0)), 1),
            "pct_medium": round(float(counts.get("Medium", 0.0)), 1),
            "pct_wide": round(float(counts.get("Wide", 0.0)), 1),
            "pct_arterial": round(float(counts.get("Arterial", 0.0)), 1),
            "pct_highway": round(float(counts.get("Highway", 0.0)), 1),
        }
