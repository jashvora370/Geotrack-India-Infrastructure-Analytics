"""
GeoTrack India — Road Width Analysis Service
=============================================
Estimates and classifies road widths using OSM attributes,
lane counts, and satellite imagery perpendicular transect analysis.

IMPORTANT — Width Estimation Confidence Levels:
    HIGH     : Direct OSM `width=*` tag (measured and contributed by mappers)
    MEDIUM   : Computed from `lanes=*` × standard lane width (Indian road design codes)
    LOW      : Inferred from highway classification (default widths from IRC standards)
    ESTIMATED: Satellite imagery transect analysis (±3–5m uncertainty)

Indian Road Congress (IRC) Standard Lane Widths:
    National Highway / Expressway : 3.75m per lane (SP:73 standard)
    State Highway                 : 3.50m per lane
    Major District Road           : 3.00m per lane
    Other District Road           : 3.00m per lane
    Village Road                  : 2.50m per lane (one-lane carriageway)

Width Classification (IRC classification adapted):
    Narrow       : < 5.5m   (one-lane or sub-standard local road)
    Medium       : 5.5–10m  (two-lane road)
    Wide         : 10–20m   (multi-lane road with margins)
    Arterial     : 20–45m   (major arterial with median and footpaths)
    Highway      : > 45m    (expressway with full right-of-way)

References:
    IRC:86-1983 Geometric Design Standards for Urban Roads in Plains
    IRC:73-1980 Geometric Design Standards for Rural (Non-Urban) Highways
    NHDP specifications for National Highways
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class WidthEstimate:
    """Result of a road width estimation."""

    width_m: Optional[float]
    confidence: str  # HIGH | MEDIUM | LOW | ESTIMATED | UNAVAILABLE
    method: str
    notes: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Lane width lookup table (IRC standards)
# ──────────────────────────────────────────────────────────────────────────────

_LANE_WIDTH_BY_CLASS: dict[str, float] = {
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
    "motorway_link": 3.75,
    "trunk_link": 3.75,
    "primary_link": 3.50,
    "secondary_link": 3.00,
    "tertiary_link": 3.00,
}

# Default road width (total carriageway) when lanes are unknown
_DEFAULT_WIDTH_BY_CLASS: dict[str, tuple[float, str]] = {
    "motorway":       (24.0,  "LOW"),   # 4-lane divided: 2×2×3.75 + 3m median + shoulders
    "trunk":          (14.0,  "LOW"),   # 4-lane: 4×3.75 − basic estimate
    "primary":        (10.5,  "LOW"),   # 3-lane or wide 2-lane SH
    "secondary":      (7.0,   "LOW"),   # 2-lane MDR
    "tertiary":       (5.5,   "LOW"),   # 2-lane ODR
    "unclassified":   (4.0,   "LOW"),   # Village/unclassified
    "residential":    (4.0,   "LOW"),   # Residential street
    "living_street":  (3.5,   "LOW"),   # Shared space
    "service":        (3.0,   "LOW"),   # Service lane
    "track":          (2.5,   "LOW"),   # Agricultural / forest track
    "motorway_link":  (7.5,   "LOW"),
    "trunk_link":     (7.5,   "LOW"),
    "primary_link":   (5.5,   "LOW"),
    "secondary_link": (4.0,   "LOW"),
    "tertiary_link":  (4.0,   "LOW"),
}

# Width bands for classification
_WIDTH_BANDS = [
    (0.0,  5.5,  "Narrow"),
    (5.5,  10.0, "Medium"),
    (10.0, 20.0, "Wide"),
    (20.0, 45.0, "Arterial"),
    (45.0, 9999, "Highway"),
]


# ──────────────────────────────────────────────────────────────────────────────
# Width estimator
# ──────────────────────────────────────────────────────────────────────────────


class WidthEstimator:
    """
    Estimates road widths from OSM attributes with confidence labelling.

    Priority order:
      1. OSM `width` tag → HIGH confidence
      2. OSM `lanes` tag × IRC lane width → MEDIUM confidence
      3. Highway classification default → LOW confidence
      4. Satellite transect (optional) → ESTIMATED confidence
    """

    def estimate(
        self,
        highway: Optional[str],
        width_tag: Optional[str],
        lanes_tag: Optional[str],
    ) -> WidthEstimate:
        """
        Estimate road width from OSM tags.

        Args:
            highway: OSM highway tag value (e.g. 'primary').
            width_tag: OSM width= tag value (e.g. '7.5' or '7.5 m').
            lanes_tag: OSM lanes= tag value (e.g. '2').

        Returns:
            WidthEstimate with width_m, confidence, method, and notes.
        """
        # ── 1. Direct OSM width tag ──────────────────────────────────────────
        if width_tag:
            parsed = self._parse_width_tag(width_tag)
            if parsed is not None and 1.0 <= parsed <= 120.0:
                return WidthEstimate(
                    width_m=round(parsed, 2),
                    confidence="HIGH",
                    method="OSM width= tag",
                    notes=["Width contributed directly by OSM mappers"],
                )

        # ── 2. Lanes × IRC lane width ─────────────────────────────────────
        if lanes_tag:
            parsed_lanes = self._parse_int(lanes_tag)
            if parsed_lanes and 1 <= parsed_lanes <= 12:
                hw = (highway or "unclassified").split("_")[0]  # handle _link variants
                lane_w = _LANE_WIDTH_BY_CLASS.get(hw, 2.75)
                # Add median strip for highways with ≥4 lanes
                median = 3.0 if parsed_lanes >= 4 and hw in ("motorway", "trunk", "primary") else 0.0
                shoulder = 1.0 if hw in ("motorway", "trunk") else 0.5
                total = parsed_lanes * lane_w + median + shoulder
                return WidthEstimate(
                    width_m=round(total, 2),
                    confidence="MEDIUM",
                    method="Lanes × IRC lane width",
                    notes=[
                        f"{parsed_lanes} lanes × {lane_w}m/lane (IRC standard for {hw})",
                        f"Median: {median}m, Shoulders: {shoulder}m",
                        "Does not include footpaths or right-of-way",
                    ],
                )

        # ── 3. Highway classification default ────────────────────────────────
        if highway:
            hw = highway.lower().strip()
            width_m, confidence = _DEFAULT_WIDTH_BY_CLASS.get(
                hw, (4.0, "LOW")
            )
            return WidthEstimate(
                width_m=width_m,
                confidence=confidence,
                method="Highway class default (IRC standards)",
                notes=[
                    f"Default width for OSM highway={hw} from IRC design standards",
                    "Actual width may differ significantly — treat as indicative",
                ],
            )

        # ── 4. Fallback ───────────────────────────────────────────────────────
        return WidthEstimate(
            width_m=None,
            confidence="UNAVAILABLE",
            method="No estimable data",
            notes=["Neither width tag, lanes tag, nor highway classification available"],
        )

    # ──────────────────────────────────────────────────────────────────────────
    # GeoDataFrame processing
    # ──────────────────────────────────────────────────────────────────────────

    def process_geodataframe(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Apply width estimation to all rows in a road segment GeoDataFrame.

        Expected columns: highway, width (optional), lanes (optional).

        Adds columns: width_m, width_confidence, width_method.

        Returns:
            GeoDataFrame with width columns added.
        """
        results = []
        for _, row in gdf.iterrows():
            est = self.estimate(
                highway=str(row.get("highway", "")) or None,
                width_tag=str(row.get("width", "")) or None,
                lanes_tag=str(row.get("lanes", "")) or None,
            )
            results.append({
                "width_m": est.width_m,
                "width_confidence": est.confidence,
                "width_method": est.method,
            })

        width_df = pd.DataFrame(results, index=gdf.index)
        gdf = gdf.copy()
        gdf["width_m"] = width_df["width_m"]
        gdf["width_confidence"] = width_df["width_confidence"]
        gdf["width_method"] = width_df["width_method"]

        return gdf

    # ──────────────────────────────────────────────────────────────────────────
    # Width classification
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def classify_width(width_m: Optional[float]) -> str:
        """
        Classify a road width into a named category.

        Args:
            width_m: Width in metres (or None).

        Returns:
            One of: Narrow, Medium, Wide, Arterial, Highway, Unknown.
        """
        if width_m is None or np.isnan(width_m):
            return "Unknown"
        for lo, hi, label in _WIDTH_BANDS:
            if lo <= width_m < hi:
                return label
        return "Unknown"

    # ──────────────────────────────────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────────────────────────────────

    def compute_width_stats(self, gdf: gpd.GeoDataFrame) -> dict:
        """
        Compute descriptive width statistics for a processed road GeoDataFrame.

        Args:
            gdf: GeoDataFrame with width_m and width_confidence columns.

        Returns:
            Dict with avg_width_m, median_width_m, max_width_m, min_width_m,
            std_width_m, pct_narrow, pct_medium, pct_wide, pct_arterial,
            pct_highway, high_confidence_pct, methodology_note.
        """
        widths = gdf["width_m"].dropna()

        if widths.empty:
            return {
                "avg_width_m": None,
                "median_width_m": None,
                "max_width_m": None,
                "min_width_m": None,
                "std_width_m": None,
                "pct_narrow": None,
                "pct_medium": None,
                "pct_wide": None,
                "pct_arterial": None,
                "pct_highway": None,
                "high_confidence_pct": None,
                "confidence": "UNAVAILABLE",
                "methodology_note": "No width data available for this dataset",
            }

        gdf = gdf.copy()
        gdf["width_class"] = gdf["width_m"].apply(self.classify_width)
        n = len(gdf)

        class_counts = gdf["width_class"].value_counts(normalize=True) * 100

        high_conf = gdf["width_confidence"].isin(["HIGH", "MEDIUM"]).sum()

        # Overall confidence
        high_conf_pct = round(high_conf / n * 100, 1) if n > 0 else 0
        if high_conf_pct >= 60:
            overall_conf = "MEDIUM"
        elif high_conf_pct >= 30:
            overall_conf = "LOW"
        else:
            overall_conf = "ESTIMATED"

        return {
            "avg_width_m": round(float(widths.mean()), 2),
            "median_width_m": round(float(widths.median()), 2),
            "max_width_m": round(float(widths.max()), 2),
            "min_width_m": round(float(widths.min()), 2),
            "std_width_m": round(float(widths.std()), 2),
            "pct_narrow": round(float(class_counts.get("Narrow", 0)), 1),
            "pct_medium": round(float(class_counts.get("Medium", 0)), 1),
            "pct_wide": round(float(class_counts.get("Wide", 0)), 1),
            "pct_arterial": round(float(class_counts.get("Arterial", 0)), 1),
            "pct_highway": round(float(class_counts.get("Highway", 0)), 1),
            "high_confidence_pct": high_conf_pct,
            "confidence": overall_conf,
            "methodology_note": (
                f"{high_conf_pct:.0f}% of widths derived from OSM tags or lane counts. "
                f"{100 - high_conf_pct:.0f}% inferred from highway classification defaults. "
                "All satellite-derived estimates are labelled ESTIMATED separately."
            ),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Satellite transect (low confidence)
    # ──────────────────────────────────────────────────────────────────────────

    def estimate_width_from_imagery(
        self,
        road_geom: LineString,
        image_array: np.ndarray,
        transform,  # rasterio Affine transform
        crs: str,
    ) -> WidthEstimate:
        """
        Estimate road width from a satellite image using perpendicular transects.

        WARNING: This method has significant uncertainty (±3–5m) due to:
        - Image resolution (10m for Sentinel-2, 30m for Landsat)
        - Shadow and spectral confusion at road edges
        - Georeferencing accuracy

        Results are ALWAYS labelled as ESTIMATED confidence.

        Args:
            road_geom: Shapely LineString of the road segment (projected CRS).
            image_array: Single-band numpy array (e.g. road/non-road binary).
            transform: rasterio Affine transform of the image.
            crs: CRS string (e.g. 'EPSG:32643').

        Returns:
            WidthEstimate with confidence='ESTIMATED'.
        """
        try:
            import rasterio.transform as riotransform

            # Sample midpoint of road
            midpoint = road_geom.interpolate(0.5, normalized=True)
            col, row = ~transform * (midpoint.x, midpoint.y)
            col, row = int(col), int(row)

            if (
                row < 0
                or row >= image_array.shape[0]
                or col < 0
                or col >= image_array.shape[1]
            ):
                return WidthEstimate(
                    width_m=None,
                    confidence="ESTIMATED",
                    method="Satellite transect (out of bounds)",
                    notes=["Road midpoint outside image extent"],
                )

            # Perpendicular profile (horizontal scan around midpoint)
            scan_width = 50  # pixels
            half = scan_width // 2
            c_start = max(0, col - half)
            c_end = min(image_array.shape[1], col + half)
            profile = image_array[row, c_start:c_end].astype(float)

            # Find road pixels (assuming road is bright/high value)
            threshold = np.percentile(profile, 70)
            road_pixels = np.sum(profile >= threshold)

            # Convert pixels to metres
            pixel_size_m = abs(transform.a)
            estimated_width = road_pixels * pixel_size_m

            return WidthEstimate(
                width_m=round(estimated_width, 1) if estimated_width > 0 else None,
                confidence="ESTIMATED",
                method="Satellite perpendicular transect",
                notes=[
                    f"Pixel size: {pixel_size_m}m",
                    f"Road pixels detected: {road_pixels}",
                    "Threshold: 70th percentile of transect profile",
                    "Uncertainty: ±3–5m due to image resolution and edge effects",
                    "DO NOT use for precise measurements",
                ],
            )

        except Exception as exc:
            logger.warning("Satellite width estimation failed: %s", exc)
            return WidthEstimate(
                width_m=None,
                confidence="ESTIMATED",
                method="Satellite transect (failed)",
                notes=[f"Error: {exc}"],
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_width_tag(value: str) -> Optional[float]:
        """Parse OSM width tag, handling units like '7.5 m' or '7.5'."""
        if not value:
            return None
        value = str(value).strip().replace(",", ".").replace("m", "").strip()
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        """Parse OSM lanes tag, handling ranges like '2;3' → 2."""
        if not value:
            return None
        value = str(value).split(";")[0].split("-")[0].strip()
        try:
            return int(float(value))
        except ValueError:
            return None
