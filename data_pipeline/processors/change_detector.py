"""
Spatial Change Detector
=========================
Detects road network changes between two GeoDataFrames representing different
time periods.  Uses spatial buffering and intersection to classify segments as
new, removed, widened, or unchanged.

Methodology note
-----------------
OSM historical data reflects *mapping* activity, not physical road construction.
Apparent new roads between 2016 and 2026 may partly reflect improved OSM
coverage rather than actual construction.  The ``apply_completeness_caveat``
method appends standardised caveats to generated reports.

Spatial matching approach
--------------------------
Two segments are considered *matched* if the 2026 segment's geometry intersects
the 15-metre buffer of a 2016 segment (or vice versa).  This tolerates minor
digitisation differences and coordinate shifts between OSM snapshots.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import MultiLineString, LineString

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_BUFFER_M = 15.0
TARGET_CRS = "EPSG:32643"  # UTM Zone 43N — metric CRS for Pune

# OSM completeness caveats keyed by region
_COMPLETENESS_NOTES: dict[str, str] = {
    "default": (
        "OSM completeness improved significantly between 2016 and 2026. "
        "Some apparent new roads may reflect improved mapping rather than "
        "physical construction."
    ),
    "pune": (
        "OSM completeness in Pune improved significantly between 2016 and 2026. "
        "Some apparent new roads may reflect improved mapping rather than "
        "physical construction. Cross-reference with GHSL built-up data to "
        "distinguish mapping growth from infrastructure growth."
    ),
    "mumbai": (
        "OSM completeness in Mumbai improved significantly between 2016 and 2026. "
        "Urban densification and mapping campaigns introduced many road segments "
        "post-2018 that physically predated that period."
    ),
}


class ChangeDetector:
    """
    Detects spatial changes between two road network GeoDataFrames.

    Parameters
    ----------
    buffer_m : float
        Default buffer distance in metres for spatial matching.
    target_crs : str
        Projected CRS for metric operations.
    """

    def __init__(
        self,
        buffer_m: float = DEFAULT_BUFFER_M,
        target_crs: str = TARGET_CRS,
    ) -> None:
        self.buffer_m = buffer_m
        self.target_crs = target_crs
        logger.info(
            "ChangeDetector initialised (buffer_m=%.1f, crs=%s)",
            buffer_m, target_crs,
        )

    # ------------------------------------------------------------------
    # CRS alignment
    # ------------------------------------------------------------------

    def align_crs(
        self,
        gdf1: gpd.GeoDataFrame,
        gdf2: gpd.GeoDataFrame,
    ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Ensure both GeoDataFrames share self.target_crs.

        If a GeoDataFrame has no CRS set, it is assumed to be EPSG:4326.

        Parameters
        ----------
        gdf1, gdf2 : gpd.GeoDataFrame

        Returns
        -------
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]
            Both projected to self.target_crs.
        """
        def _project(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            if str(gdf.crs) != self.target_crs:
                gdf = gdf.to_crs(self.target_crs)
            return gdf

        gdf1 = _project(gdf1.copy())
        gdf2 = _project(gdf2.copy())
        logger.debug("Both GeoDataFrames projected to %s", self.target_crs)
        return gdf1, gdf2

    # ------------------------------------------------------------------
    # Buffer matching
    # ------------------------------------------------------------------

    def buffer_match(
        self,
        gdf_2016: gpd.GeoDataFrame,
        gdf_2026: gpd.GeoDataFrame,
        buffer_m: Optional[float] = None,
    ) -> gpd.GeoDataFrame:
        """
        Spatially join 2026 segments to 2016 buffered segments.

        A 2026 segment is *matched* when its geometry intersects the buffer
        of at least one 2016 segment.

        Parameters
        ----------
        gdf_2016, gdf_2026 : gpd.GeoDataFrame
        buffer_m : float, optional

        Returns
        -------
        gpd.GeoDataFrame
            2026 segments enriched with a 'matched_2016_idx' column.
        """
        buf = buffer_m if buffer_m is not None else self.buffer_m
        gdf_2016, gdf_2026 = self.align_crs(gdf_2016, gdf_2026)

        buf_2016 = gdf_2016.copy()
        buf_2016["geometry"] = buf_2016.geometry.buffer(buf)
        buf_2016 = buf_2016.reset_index(drop=True)
        buf_2016["_buf_idx"] = buf_2016.index

        joined = gpd.sjoin(
            gdf_2026.reset_index(drop=True),
            buf_2016[["geometry", "_buf_idx"]],
            how="left",
            predicate="intersects",
        )
        # Deduplicate: keep first match per 2026 segment
        joined = joined.reset_index(drop=True)
        first_match = joined.groupby(joined.index)["_buf_idx"].first()
        gdf_2026 = gdf_2026.copy().reset_index(drop=True)
        gdf_2026["matched_2016_idx"] = first_match
        return gdf_2026

    # ------------------------------------------------------------------
    # New roads
    # ------------------------------------------------------------------

    def find_new_roads(
        self,
        gdf_2016: gpd.GeoDataFrame,
        gdf_2026: gpd.GeoDataFrame,
        buffer_m: Optional[float] = None,
    ) -> gpd.GeoDataFrame:
        """
        Return 2026 segments not within *buffer_m* of any 2016 segment.

        Parameters
        ----------
        gdf_2016, gdf_2026 : gpd.GeoDataFrame
        buffer_m : float, optional

        Returns
        -------
        gpd.GeoDataFrame
            Subset of gdf_2026 representing new roads.
        """
        buf = buffer_m if buffer_m is not None else self.buffer_m
        gdf_2016, gdf_2026 = self.align_crs(gdf_2016, gdf_2026)

        buf_2016 = gdf_2016.copy()
        buf_2016["geometry"] = buf_2016.geometry.buffer(buf)
        union_2016 = buf_2016.geometry.union_all()

        new_mask = ~gdf_2026.geometry.intersects(union_2016)
        new_roads = gdf_2026[new_mask].copy()
        new_roads["change_type"] = "new"

        if "length_km" not in new_roads.columns:
            new_roads["length_km"] = new_roads.geometry.length / 1000.0

        logger.info(
            "New roads: %d segments (%.2f km)",
            len(new_roads), new_roads["length_km"].sum(),
        )
        return new_roads

    # ------------------------------------------------------------------
    # Removed roads
    # ------------------------------------------------------------------

    def find_removed_roads(
        self,
        gdf_2016: gpd.GeoDataFrame,
        gdf_2026: gpd.GeoDataFrame,
        buffer_m: Optional[float] = None,
    ) -> gpd.GeoDataFrame:
        """
        Return 2016 segments not within *buffer_m* of any 2026 segment.

        Parameters
        ----------
        gdf_2016, gdf_2026 : gpd.GeoDataFrame
        buffer_m : float, optional

        Returns
        -------
        gpd.GeoDataFrame
            Subset of gdf_2016 representing removed roads.
        """
        buf = buffer_m if buffer_m is not None else self.buffer_m
        gdf_2016, gdf_2026 = self.align_crs(gdf_2016, gdf_2026)

        buf_2026 = gdf_2026.copy()
        buf_2026["geometry"] = buf_2026.geometry.buffer(buf)
        union_2026 = buf_2026.geometry.union_all()

        removed_mask = ~gdf_2016.geometry.intersects(union_2026)
        removed_roads = gdf_2016[removed_mask].copy()
        removed_roads["change_type"] = "removed"

        if "length_km" not in removed_roads.columns:
            removed_roads["length_km"] = removed_roads.geometry.length / 1000.0

        logger.info(
            "Removed roads: %d segments (%.2f km)",
            len(removed_roads), removed_roads["length_km"].sum(),
        )
        return removed_roads

    # ------------------------------------------------------------------
    # Widened roads
    # ------------------------------------------------------------------

    def find_widened_roads(
        self,
        matched_pairs: gpd.GeoDataFrame,
        width_threshold_m: float = 1.0,
    ) -> gpd.GeoDataFrame:
        """
        Identify matched road segments that have been widened.

        A segment is *widened* when 2026 width_m > 2016 width_m + *width_threshold_m*
        and both width estimates have confidence ≠ 'ESTIMATED'.

        Parameters
        ----------
        matched_pairs : gpd.GeoDataFrame
            Output of ``buffer_match`` with suffixed columns (_2016, _2026).
        width_threshold_m : float
            Minimum width increase to count as a widening event.

        Returns
        -------
        gpd.GeoDataFrame
        """
        required = {"width_m_2026", "width_m_2016"}
        if not required.issubset(matched_pairs.columns):
            logger.warning(
                "matched_pairs missing width columns; returning empty DataFrame."
            )
            return gpd.GeoDataFrame(columns=list(matched_pairs.columns))

        df = matched_pairs.copy()
        df["width_m_2016"] = pd.to_numeric(df.get("width_m_2016", np.nan), errors="coerce")
        df["width_m_2026"] = pd.to_numeric(df.get("width_m_2026", np.nan), errors="coerce")

        # Exclude ESTIMATED confidence on either end
        conf_2016_ok = df.get("width_confidence_2016", "MEDIUM") != "ESTIMATED"
        conf_2026_ok = df.get("width_confidence_2026", "MEDIUM") != "ESTIMATED"
        widened_mask = (
            conf_2016_ok
            & conf_2026_ok
            & (df["width_m_2026"] > df["width_m_2016"] + width_threshold_m)
        )
        widened = df[widened_mask].copy()
        widened["change_type"] = "widened"
        widened["width_increase_m"] = widened["width_m_2026"] - widened["width_m_2016"]

        if "length_km" not in widened.columns:
            if "geometry" in widened.columns:
                widened["length_km"] = widened.geometry.length / 1000.0
            else:
                widened["length_km"] = np.nan

        logger.info(
            "Widened roads: %d segments (%.2f km)", len(widened),
            widened["length_km"].sum() if "length_km" in widened.columns else 0.0,
        )
        return widened

    # ------------------------------------------------------------------
    # IoU
    # ------------------------------------------------------------------

    def calculate_iou_for_pair(
        self,
        geom1: Any,
        geom2: Any,
        buffer_m: float = 10.0,
    ) -> float:
        """
        Compute Intersection-over-Union for a pair of geometries.

        Both geometries are buffered by *buffer_m* before computing IoU
        to produce a fair comparison of linear features.

        Parameters
        ----------
        geom1, geom2 : Shapely geometry
        buffer_m : float

        Returns
        -------
        float
            IoU value between 0 and 1.
        """
        try:
            b1 = geom1.buffer(buffer_m)
            b2 = geom2.buffer(buffer_m)
            intersection_area = b1.intersection(b2).area
            union_area = b1.union(b2).area
            return intersection_area / union_area if union_area > 0 else 0.0
        except Exception as exc:
            logger.debug("IoU calculation failed: %s", exc)
            return 0.0

    # ------------------------------------------------------------------
    # Change report
    # ------------------------------------------------------------------

    def generate_change_report(
        self,
        gdf_2016: gpd.GeoDataFrame,
        gdf_2026: gpd.GeoDataFrame,
        region_name: str = "Study Area",
    ) -> dict[str, Any]:
        """
        Generate a comprehensive change detection report.

        Parameters
        ----------
        gdf_2016 : gpd.GeoDataFrame
        gdf_2026 : gpd.GeoDataFrame
        region_name : str

        Returns
        -------
        dict
        """
        gdf_2016, gdf_2026 = self.align_crs(gdf_2016, gdf_2026)

        # Ensure length_km
        for gdf in [gdf_2016, gdf_2026]:
            if "length_km" not in gdf.columns:
                gdf["length_km"] = gdf.geometry.length / 1000.0

        total_2016 = float(gdf_2016["length_km"].sum())
        total_2026 = float(gdf_2026["length_km"].sum())
        pct_growth = ((total_2026 - total_2016) / total_2016 * 100.0) if total_2016 > 0 else float("nan")

        new_roads = self.find_new_roads(gdf_2016, gdf_2026)
        removed_roads = self.find_removed_roads(gdf_2016, gdf_2026)

        new_km = float(new_roads["length_km"].sum()) if not new_roads.empty else 0.0
        removed_km = float(removed_roads["length_km"].sum()) if not removed_roads.empty else 0.0
        unchanged_km = max(0.0, total_2016 - removed_km)

        # Classification breakdown (2026)
        class_breakdown: dict[str, dict] = {}
        class_col = "road_class" if "road_class" in gdf_2026.columns else "highway"
        if class_col in gdf_2026.columns:
            for cls, grp in gdf_2026.groupby(class_col):
                class_breakdown[str(cls)] = {
                    "count": len(grp),
                    "length_km": round(float(grp["length_km"].sum()), 3),
                }

        report: dict[str, Any] = {
            "year_from": 2016,
            "year_to": 2026,
            "region": region_name,
            "total_2016_km": round(total_2016, 3),
            "total_2026_km": round(total_2026, 3),
            "pct_growth": round(pct_growth, 2),
            "new_roads_km": round(new_km, 3),
            "new_roads_count": len(new_roads),
            "removed_roads_km": round(removed_km, 3),
            "removed_roads_count": len(removed_roads),
            "widened_roads_count": 0,  # updated below if width info is available
            "widened_roads_km": 0.0,
            "unchanged_km": round(unchanged_km, 3),
            "classification_breakdown": class_breakdown,
            "data_quality_notes": [],
            "methodology": (
                "Spatial buffer matching (15 m tolerance) between OSM snapshots. "
                "New roads: 2026 segments not intersecting any 2016 buffer. "
                "Removed roads: 2016 segments not intersecting any 2026 buffer. "
                "Width change requires OSM tag or lane data (ESTIMATED confidence excluded)."
            ),
        }

        # Widened roads — requires width columns on both frames
        if "width_m" in gdf_2016.columns and "width_m" in gdf_2026.columns:
            matched = self.buffer_match(gdf_2016, gdf_2026)
            # Build pseudo-merged DataFrame for widening analysis
            # (simplified: compare per-class medians)
            widened = self.find_widened_roads(
                _build_matched_pairs(gdf_2016, gdf_2026, matched)
            )
            report["widened_roads_count"] = len(widened)
            report["widened_roads_km"] = round(
                float(widened["length_km"].sum()) if not widened.empty else 0.0, 3
            )

        report = self.apply_completeness_caveat(report, region_name)
        logger.info(
            "Change report: +%.2f km new, -%.2f km removed (%.1f%% growth)",
            new_km, removed_km, pct_growth,
        )
        return report

    # ------------------------------------------------------------------
    # Completeness caveat
    # ------------------------------------------------------------------

    def apply_completeness_caveat(
        self,
        stats: dict[str, Any],
        region_name: str,
    ) -> dict[str, Any]:
        """
        Append OSM completeness caveat to the report's data_quality_notes list.

        Parameters
        ----------
        stats : dict
            Change report dictionary (modified in place).
        region_name : str

        Returns
        -------
        dict
            Updated stats dict.
        """
        region_key = region_name.lower().strip()
        note = _COMPLETENESS_NOTES.get(region_key, _COMPLETENESS_NOTES["default"])
        if "data_quality_notes" not in stats:
            stats["data_quality_notes"] = []
        stats["data_quality_notes"].append(note)
        logger.info("Completeness caveat appended for region '%s'.", region_name)
        return stats


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _build_matched_pairs(
    gdf_2016: gpd.GeoDataFrame,
    gdf_2026: gpd.GeoDataFrame,
    matched_2026: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Build a merged GeoDataFrame of matched pairs with suffixed columns.

    Parameters
    ----------
    gdf_2016 : gpd.GeoDataFrame
    gdf_2026 : gpd.GeoDataFrame
    matched_2026 : gpd.GeoDataFrame
        Output of ChangeDetector.buffer_match (contains matched_2016_idx).

    Returns
    -------
    gpd.GeoDataFrame
    """
    gdf_2016 = gdf_2016.reset_index(drop=True)
    pairs = matched_2026.dropna(subset=["matched_2016_idx"]).copy()
    pairs["matched_2016_idx"] = pairs["matched_2016_idx"].astype(int)

    # Suffix columns
    pairs_cols = {c: f"{c}_2026" for c in pairs.columns if c not in ["geometry", "matched_2016_idx"]}
    pairs = pairs.rename(columns=pairs_cols)

    old_cols = {c: f"{c}_2016" for c in gdf_2016.columns if c != "geometry"}
    gdf_2016_renamed = gdf_2016.rename(columns=old_cols)

    merged = pairs.merge(
        gdf_2016_renamed,
        left_on="matched_2016_idx",
        right_index=True,
        how="left",
        suffixes=("", "_old"),
    )
    return merged
