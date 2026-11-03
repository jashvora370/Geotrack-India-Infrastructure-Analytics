# app/services/change_detection.py
"""
Road network change-detection engine for GeoTrack India.

Algorithm Overview
------------------
1. Reproject both GeoDataFrames to a local metric CRS (EPSG:32643 – UTM 43N,
   appropriate for most of India).
2. Buffer every road segment in the *from* dataset by ``buffer_m`` metres.
3. Perform a GeoPandas spatial join (``sjoin`` with ``intersects`` predicate)
   to match segments between the two years.
4. Compute Intersection-over-Union (IoU) on the buffered geometries to
   determine whether a match is a true overlap.
5. Classify each segment as NEW / REMOVED / WIDENED / UNCHANGED / RECLASSIFIED.
6. Aggregate into KPI summary statistics and apply an OSM completeness warning
   when the growth signal is implausibly high.

OSM Completeness Caveat
-----------------------
Change detection between OSM snapshots will conflate genuine road construction
with retrospective data entry (mappers adding roads that were built earlier).
The :meth:`RoadChangeDetector.detect_changes` method embeds a
``data_quality_note`` in the summary when the detected new-road percentage
exceeds 20 % of the baseline length.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# UTM 43N – covers most of India and neighbouring areas.
INDIA_UTM_CRS = "EPSG:32643"

# Change category labels
CHANGE_NEW = "NEW"
CHANGE_REMOVED = "REMOVED"
CHANGE_WIDENED = "WIDENED"
CHANGE_UNCHANGED = "UNCHANGED"
CHANGE_RECLASSIFIED = "RECLASSIFIED"


# ─────────────────────────────────────────────────────────────────────────────
# IoU helper
# ─────────────────────────────────────────────────────────────────────────────

def calculate_iou(geom1: Any, geom2: Any, buffer_m: float = 15.0) -> float:
    """
    Compute the Intersection-over-Union between two LineString geometries.

    Both geometries are buffered by ``buffer_m`` metres before the IoU
    calculation, converting them to polygons for area-based comparison.
    The geometries must already be in a metric CRS.

    Args:
        geom1:    First Shapely geometry (LineString or MultiLineString).
        geom2:    Second Shapely geometry (LineString or MultiLineString).
        buffer_m: Buffer radius in metres applied to both geometries.

    Returns:
        IoU score in [0, 1].  Returns 0.0 if either geometry is None or empty.
    """
    try:
        if geom1 is None or geom2 is None:
            return 0.0
        b1 = geom1.buffer(buffer_m)
        b2 = geom2.buffer(buffer_m)
        if b1.is_empty or b2.is_empty:
            return 0.0
        inter = b1.intersection(b2)
        union = b1.union(b2)
        if union.area == 0:
            return 0.0
        return float(inter.area / union.area)
    except Exception as exc:
        logger.debug("IoU calculation error: %s", exc)
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Segment-level classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_change(
    segment_from: pd.Series,
    segment_to: pd.Series,
    iou: float,
    iou_threshold: float = 0.4,
) -> str:
    """
    Classify the change between a matched pair of road segments.

    Classification rules (in priority order):
        WIDENED       – IoU ≥ threshold AND width increased by ≥ 20 %.
        RECLASSIFIED  – IoU ≥ threshold AND highway tag changed.
        UNCHANGED     – IoU ≥ threshold AND no significant attribute change.
        NEW           – No match found in the *from* dataset (iou == 0.0).
        REMOVED       – No match found in the *to* dataset.

    Args:
        segment_from:  Pandas Series for the road segment in the earlier year.
        segment_to:    Pandas Series for the road segment in the later year.
        iou:           Pre-computed IoU score for the matched pair.
        iou_threshold: Minimum IoU to consider a pair a spatial match.

    Returns:
        Change category string: one of the ``CHANGE_*`` module constants.
    """
    if iou < iou_threshold:
        return CHANGE_NEW

    highway_from = str(segment_from.get("highway", "")).lower()
    highway_to = str(segment_to.get("highway", "")).lower()

    width_from = segment_from.get("width_m") or segment_from.get("width") or 0
    width_to = segment_to.get("width_m") or segment_to.get("width") or 0

    try:
        width_from = float(width_from) if width_from else 0.0
        width_to = float(width_to) if width_to else 0.0
    except (TypeError, ValueError):
        width_from = width_to = 0.0

    if width_from > 0 and width_to > 0:
        width_change_pct = (width_to - width_from) / width_from * 100
        if width_change_pct >= 20:
            return CHANGE_WIDENED

    if highway_from and highway_to and highway_from != highway_to:
        return CHANGE_RECLASSIFIED

    return CHANGE_UNCHANGED


# ─────────────────────────────────────────────────────────────────────────────
# Main change-detection class
# ─────────────────────────────────────────────────────────────────────────────

class RoadChangeDetector:
    """
    Spatial change-detection engine comparing two road network GeoDataFrames.

    Attributes:
        buffer_m:      Buffer radius (metres) for spatial matching.
        iou_threshold: Minimum IoU to count a segment pair as a match.
        crs:           Working CRS for metric calculations.
    """

    def __init__(
        self,
        buffer_m: float = 15.0,
        iou_threshold: float = 0.4,
        crs: str = INDIA_UTM_CRS,
    ) -> None:
        self.buffer_m = buffer_m
        self.iou_threshold = iou_threshold
        self.crs = crs

    def _prepare_gdf(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Reproject a GeoDataFrame to the working metric CRS.

        Args:
            gdf: Input GeoDataFrame in any CRS.

        Returns:
            Reprojected GeoDataFrame.

        Raises:
            ValueError: If the GeoDataFrame has no CRS set.
        """
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        return gdf.to_crs(self.crs)

    def detect_changes(
        self,
        gdf_from: gpd.GeoDataFrame,
        gdf_to: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Detect road changes between two annual road network snapshots.

        Spatial matching is performed using a buffer + spatial join approach:
            1. Buffer all *from* segments by ``self.buffer_m``.
            2. Spatial-join *to* segments against the buffers.
            3. Compute IoU for each matched pair.
            4. Classify each segment.

        Args:
            gdf_from: Road network GeoDataFrame for the earlier year.
            gdf_to:   Road network GeoDataFrame for the later year.

        Returns:
            GeoDataFrame containing all segments from both years with a
            ``change_type`` column indicating the classification.

        Raises:
            ValueError: If either GeoDataFrame is empty.
        """
        logger.info(
            "Detecting changes: %d from-segments, %d to-segments",
            len(gdf_from),
            len(gdf_to),
        )

        if gdf_from.empty and gdf_to.empty:
            raise ValueError("Both GeoDataFrames are empty; cannot detect changes.")

        gdf_from = self._prepare_gdf(gdf_from.copy())
        gdf_to = self._prepare_gdf(gdf_to.copy())

        # Reset indices for clean merging
        gdf_from = gdf_from.reset_index(drop=True)
        gdf_to = gdf_to.reset_index(drop=True)

        # Build buffered version of from-segments for spatial join
        gdf_from_buf = gdf_from.copy()
        gdf_from_buf["geometry"] = gdf_from_buf.geometry.buffer(self.buffer_m)

        # Spatial join: to-segments that intersect from-buffers
        joined = gpd.sjoin(
            gdf_to,
            gdf_from_buf[["geometry"]].rename(columns={"geometry": "geometry"}),
            how="left",
            predicate="intersects",
        )

        # Identify unmatched to-segments (NEW roads)
        matched_to_idx = set(joined.index[joined["index_right"].notna()])
        new_roads = gdf_to[~gdf_to.index.isin(matched_to_idx)].copy()
        new_roads["change_type"] = CHANGE_NEW
        new_roads["iou"] = 0.0

        # Identify removed roads (from-segments not matched by any to-segment)
        matched_from_idx = set(joined["index_right"].dropna().astype(int).tolist())
        removed_roads = gdf_from[~gdf_from.index.isin(matched_from_idx)].copy()
        removed_roads["change_type"] = CHANGE_REMOVED
        removed_roads["iou"] = 0.0

        # Classify matched segments using IoU
        classified_rows: List[Dict[str, Any]] = []
        for to_idx, group in joined[joined["index_right"].notna()].groupby(level=0):
            to_seg = gdf_to.loc[to_idx]
            # Pick the best matching from-segment by IoU
            best_iou = 0.0
            best_class = CHANGE_UNCHANGED
            for _, row in group.iterrows():
                from_idx = int(row["index_right"])
                from_seg = gdf_from.loc[from_idx]
                iou_val = calculate_iou(
                    to_seg.geometry, from_seg.geometry, self.buffer_m
                )
                if iou_val > best_iou:
                    best_iou = iou_val
                    best_class = classify_change(
                        from_seg, to_seg, iou_val, self.iou_threshold
                    )

            row_dict = to_seg.to_dict()
            row_dict["change_type"] = best_class
            row_dict["iou"] = best_iou
            classified_rows.append(row_dict)

        classified_gdf = gpd.GeoDataFrame(
            classified_rows, geometry="geometry", crs=self.crs
        ) if classified_rows else gpd.GeoDataFrame(
            columns=list(gdf_to.columns) + ["change_type", "iou"],
            geometry="geometry",
            crs=self.crs,
        )

        result = gpd.GeoDataFrame(
            pd.concat([new_roads, removed_roads, classified_gdf], ignore_index=True),
            geometry="geometry",
            crs=self.crs,
        )

        logger.info(
            "Change detection complete: %d total segments classified",
            len(result),
        )
        return result

    def generate_change_summary(
        self,
        changes_gdf: gpd.GeoDataFrame,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute KPI summary statistics from a classified change GeoDataFrame.

        Args:
            changes_gdf: Output of :meth:`detect_changes`.
            region:      Optional region name for quality-note generation.

        Returns:
            Dictionary with keys:
                new_roads_km, removed_roads_km, widened_roads_km,
                unchanged_km, total_from_km, total_to_km, pct_growth,
                segments_added, segments_removed, segments_widened,
                segments_unchanged, data_quality_note.
        """
        if changes_gdf.empty:
            return self._empty_summary()

        # Compute length in km for each segment
        gdf = changes_gdf.copy()
        if gdf.crs is None or not gdf.crs.is_projected:
            gdf = gdf.set_crs(self.crs, allow_override=True)
        gdf["length_m"] = gdf.geometry.length

        def _sum_km(category: str) -> float:
            mask = gdf["change_type"] == category
            return round(gdf.loc[mask, "length_m"].sum() / 1000, 3)

        def _count(category: str) -> int:
            return int((gdf["change_type"] == category).sum())

        new_km = _sum_km(CHANGE_NEW)
        removed_km = _sum_km(CHANGE_REMOVED)
        widened_km = _sum_km(CHANGE_WIDENED)
        unchanged_km = _sum_km(CHANGE_UNCHANGED) + _sum_km(CHANGE_RECLASSIFIED)

        total_from_km = removed_km + unchanged_km + widened_km
        total_to_km = new_km + widened_km + unchanged_km

        pct_growth = (
            round((total_to_km - total_from_km) / total_from_km * 100, 2)
            if total_from_km > 0
            else 0.0
        )

        data_quality_note = ""
        if total_from_km > 0 and new_km / total_from_km > 0.20:
            data_quality_note = (
                "New roads exceed 20 % of the baseline network length. "
                "This may partly reflect OSM mapping backfill rather than genuine construction."
            )

        summary: Dict[str, Any] = {
            "new_roads_km": new_km,
            "removed_roads_km": removed_km,
            "widened_roads_km": widened_km,
            "unchanged_km": unchanged_km,
            "total_from_km": total_from_km,
            "total_to_km": total_to_km,
            "pct_growth": pct_growth,
            "segments_added": _count(CHANGE_NEW),
            "segments_removed": _count(CHANGE_REMOVED),
            "segments_widened": _count(CHANGE_WIDENED),
            "segments_unchanged": _count(CHANGE_UNCHANGED),
            "data_quality_note": data_quality_note,
        }

        if region:
            from app.services.osm_service import apply_osm_completeness_correction
            summary = apply_osm_completeness_correction(summary, region)

        return summary

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        """Return a zeroed summary dict when no segments are available."""
        return {
            "new_roads_km": 0.0,
            "removed_roads_km": 0.0,
            "widened_roads_km": 0.0,
            "unchanged_km": 0.0,
            "total_from_km": 0.0,
            "total_to_km": 0.0,
            "pct_growth": 0.0,
            "segments_added": 0,
            "segments_removed": 0,
            "segments_widened": 0,
            "segments_unchanged": 0,
            "data_quality_note": "No road segments available for analysis.",
        }
