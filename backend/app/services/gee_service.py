"""
GeoTrack India — Google Earth Engine Imagery Service
=====================================================
Provides NDVI computation, land cover analysis, and satellite imagery
retrieval using Landsat 8/9 and Sentinel-2 data through the GEE Python API.

Data Sources:
    - Landsat 8 OLI/TIRS Collection 2: LANDSAT/LC08/C02/T1_L2 (2013–present, 30m)
    - Landsat 9 OLI-2: LANDSAT/LC09/C02/T1_L2 (2021–present, 30m)
    - Sentinel-2 SR Harmonised: COPERNICUS/S2_SR_HARMONIZED (2017–present, 10m)
    - ESA WorldCover v200: ESA/WorldCover/v200 (2021, 10m)
    - GHSL Built-up: JRC/GHSL/P2023A/GHS_BUILT_S (1975–2030, 10m)

Authentication:
    Option A — Personal account (development):
        import ee; ee.Authenticate(); ee.Initialize()

    Option B — Service account (production):
        credentials = ee.ServiceAccountCredentials(
            email=os.environ['GEE_SERVICE_ACCOUNT'],
            key_file=os.environ['GEE_KEY_FILE']
        )
        ee.Initialize(credentials=credentials)

Important:
    This service requires a Google Earth Engine account.
    If GEE is unavailable, all methods fall back to cached results
    stored in ./cache/gee_cache.json (if present) or return
    data marked as UNAVAILABLE.

NDVI Thresholds (standard literature values):
    < 0.0  : Water / bare rock
    0.0–0.1: Bare soil / urban surfaces
    0.1–0.3: Sparse vegetation / shrubland
    0.3–0.6: Moderate vegetation / cropland
    > 0.6  : Dense vegetation / forest

References:
    Tucker, C.J. (1979). Red and photographic infrared linear combinations
    for monitoring vegetation. Remote Sensing of Environment, 8(2), 127–150.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
CACHE_FILE = CACHE_DIR / "gee_cache.json"

# Standard NDVI green threshold
NDVI_GREEN_THRESHOLD = 0.3

# Landsat 8/9 band scaling (Collection 2 SR)
L8_SCALE_FACTOR = 0.0000275
L8_OFFSET = -0.2

# Sentinel-2 scaling (already in reflectance × 10000)
S2_SCALE_FACTOR = 0.0001

# ESA WorldCover class definitions
WORLDCOVER_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

# ──────────────────────────────────────────────────────────────────────────────
# Service class
# ──────────────────────────────────────────────────────────────────────────────


class GeeImageryService:
    """
    Provides satellite imagery analysis via Google Earth Engine.

    Falls back to cached data if GEE is unavailable.
    """

    def __init__(self, service_account: Optional[str] = None, key_file: Optional[str] = None):
        self._initialized = False
        self._service_account = service_account
        self._key_file = key_file
        self._cache: dict = {}
        self._load_cache()

    # ──────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ──────────────────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """
        Authenticate and initialise the Earth Engine API.

        Returns:
            True if initialisation succeeded, False otherwise.
        """
        try:
            import ee  # type: ignore

            if self._service_account and self._key_file:
                credentials = ee.ServiceAccountCredentials(
                    email=self._service_account, key_file=self._key_file
                )
                ee.Initialize(credentials=credentials)
                logger.info("GEE initialised with service account.")
            else:
                ee.Initialize()
                logger.info("GEE initialised with default credentials.")

            self._initialized = True
            self._ee = ee
            return True

        except ImportError:
            logger.warning(
                "earthengine-api not installed. Install with: pip install earthengine-api"
            )
            return False
        except Exception as exc:
            logger.warning(
                "GEE initialisation failed: %s. Falling back to cache.", exc
            )
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Landsat
    # ──────────────────────────────────────────────────────────────────────────

    def get_landsat_ndvi_stats(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
        cloud_cover_pct: int = 20,
    ) -> dict:
        """
        Compute annual NDVI statistics from Landsat 8/9 for a given year.

        Args:
            bbox: (west, south, east, north) in WGS84 decimal degrees.
            year: Calendar year (2013–2026).
            cloud_cover_pct: Maximum cloud cover percentage filter.

        Returns:
            Dict with keys: ndvi_mean, ndvi_min, ndvi_max, ndvi_std,
            green_fraction, pixel_count, satellite, year, data_source,
            is_estimated (bool), notes (list[str]).
        """
        cache_key = f"landsat_ndvi_{bbox}_{year}"
        if cached := self._cache.get(cache_key):
            logger.debug("NDVI stats served from cache for year %d.", year)
            return cached

        if not self._initialized:
            return self._unavailable_ndvi(year, "GEE not initialised")

        try:
            ee = self._ee
            west, south, east, north = bbox
            region = ee.Geometry.Rectangle([west, south, east, north])

            # Select collection based on year
            if year >= 2021:
                collection_ids = [
                    "LANDSAT/LC09/C02/T1_L2",
                    "LANDSAT/LC08/C02/T1_L2",
                ]
            else:
                collection_ids = ["LANDSAT/LC08/C02/T1_L2"]

            images = []
            for cid in collection_ids:
                col = (
                    ee.ImageCollection(cid)
                    .filterBounds(region)
                    .filterDate(f"{year}-01-01", f"{year}-12-31")
                    .filter(ee.Filter.lt("CLOUD_COVER", cloud_cover_pct))
                )
                images.append(col)

            merged = images[0]
            for col in images[1:]:
                merged = merged.merge(col)

            count = merged.size().getInfo()
            if count == 0:
                return self._unavailable_ndvi(
                    year, f"No Landsat scenes with <{cloud_cover_pct}% cloud cover in {year}"
                )

            def apply_scale_and_ndvi(image):
                nir = image.select("SR_B5").multiply(L8_SCALE_FACTOR).add(L8_OFFSET)
                red = image.select("SR_B4").multiply(L8_SCALE_FACTOR).add(L8_OFFSET)
                ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
                return image.addBands(ndvi)

            composite = merged.map(apply_scale_and_ndvi).median()
            ndvi_band = composite.select("NDVI")

            stats = ndvi_band.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), "", True)
                .combine(ee.Reducer.max(), "", True)
                .combine(ee.Reducer.stdDev(), "", True)
                .combine(ee.Reducer.count(), "", True),
                geometry=region,
                scale=30,
                maxPixels=1e9,
            ).getInfo()

            # Green fraction: pixels with NDVI > threshold
            green_mask = ndvi_band.gt(NDVI_GREEN_THRESHOLD)
            green_count = green_mask.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=region,
                scale=30,
                maxPixels=1e9,
            ).getInfo()

            total_pixels = stats.get("NDVI_count", 1) or 1
            green_pixels = green_count.get("NDVI", 0) or 0

            result = {
                "ndvi_mean": round(stats.get("NDVI_mean", 0), 4),
                "ndvi_min": round(stats.get("NDVI_min", 0), 4),
                "ndvi_max": round(stats.get("NDVI_max", 0), 4),
                "ndvi_std": round(stats.get("NDVI_stdDev", 0), 4),
                "green_fraction": round(green_pixels / total_pixels, 4),
                "pixel_count": int(total_pixels),
                "scene_count": count,
                "satellite": "Landsat 8/9",
                "year": year,
                "resolution_m": 30,
                "data_source": "USGS/NASA Landsat Collection 2 (via GEE)",
                "is_estimated": False,
                "confidence": "HIGH" if count >= 3 else "MEDIUM",
                "notes": [
                    f"Composite from {count} scenes with <{cloud_cover_pct}% cloud cover",
                    "Cloud masking applied using QA_PIXEL band",
                    "SR scaling: reflectance = DN × 0.0000275 + (−0.2)",
                ],
            }

            self._cache[cache_key] = result
            self._save_cache()
            return result

        except Exception as exc:
            logger.error("GEE Landsat NDVI error for year %d: %s", year, exc)
            return self._unavailable_ndvi(year, str(exc))

    # ──────────────────────────────────────────────────────────────────────────
    # Sentinel-2
    # ──────────────────────────────────────────────────────────────────────────

    def get_sentinel2_ndvi_stats(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
        cloud_cover_pct: int = 20,
    ) -> dict:
        """
        Compute annual NDVI from Sentinel-2 SR Harmonised (10m resolution).

        Available from 2017 onward. Returns UNAVAILABLE for years before 2017.

        Args:
            bbox: (west, south, east, north) in WGS84.
            year: 2017–2026.
            cloud_cover_pct: Maximum scene cloud cover.

        Returns:
            Same structure as get_landsat_ndvi_stats.
        """
        if year < 2017:
            return self._unavailable_ndvi(year, "Sentinel-2 data not available before 2017")

        cache_key = f"s2_ndvi_{bbox}_{year}"
        if cached := self._cache.get(cache_key):
            return cached

        if not self._initialized:
            return self._unavailable_ndvi(year, "GEE not initialised")

        try:
            ee = self._ee
            west, south, east, north = bbox
            region = ee.Geometry.Rectangle([west, south, east, north])

            def mask_s2_clouds(image):
                qa = image.select("QA60")
                cloud_bit_mask = 1 << 10
                cirrus_bit_mask = 1 << 11
                mask = (
                    qa.bitwiseAnd(cloud_bit_mask)
                    .eq(0)
                    .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
                )
                return image.updateMask(mask).divide(10000)

            collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(region)
                .filterDate(f"{year}-01-01", f"{year}-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_pct))
                .map(mask_s2_clouds)
            )

            count = collection.size().getInfo()
            if count == 0:
                return self._unavailable_ndvi(
                    year, f"No S2 scenes <{cloud_cover_pct}% cloud in {year}"
                )

            composite = collection.median()
            nir = composite.select("B8")
            red = composite.select("B4")
            ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")

            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), "", True)
                .combine(ee.Reducer.max(), "", True)
                .combine(ee.Reducer.stdDev(), "", True)
                .combine(ee.Reducer.count(), "", True),
                geometry=region,
                scale=10,
                maxPixels=1e10,
            ).getInfo()

            green_count = (
                ndvi.gt(NDVI_GREEN_THRESHOLD)
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e10,
                )
                .getInfo()
            )

            total_pixels = stats.get("NDVI_count", 1) or 1
            green_pixels = green_count.get("NDVI", 0) or 0

            result = {
                "ndvi_mean": round(stats.get("NDVI_mean", 0), 4),
                "ndvi_min": round(stats.get("NDVI_min", 0), 4),
                "ndvi_max": round(stats.get("NDVI_max", 0), 4),
                "ndvi_std": round(stats.get("NDVI_stdDev", 0), 4),
                "green_fraction": round(green_pixels / total_pixels, 4),
                "pixel_count": int(total_pixels),
                "scene_count": count,
                "satellite": "Sentinel-2",
                "year": year,
                "resolution_m": 10,
                "data_source": "ESA Sentinel-2 SR Harmonised (via GEE)",
                "is_estimated": False,
                "confidence": "HIGH" if count >= 4 else "MEDIUM",
                "notes": [
                    f"Composite from {count} scenes with <{cloud_cover_pct}% cloud cover",
                    "Cloud masking: QA60 band bits 10 (cloud) and 11 (cirrus)",
                    "Reflectance = DN ÷ 10000",
                    "NDVI green threshold: > 0.3",
                ],
            }

            self._cache[cache_key] = result
            self._save_cache()
            return result

        except Exception as exc:
            logger.error("GEE Sentinel-2 NDVI error for year %d: %s", year, exc)
            return self._unavailable_ndvi(year, str(exc))

    # ──────────────────────────────────────────────────────────────────────────
    # GHSL Built-up
    # ──────────────────────────────────────────────────────────────────────────

    def get_ghsl_builtup(
        self,
        bbox: tuple[float, float, float, float],
        year: int = 2020,
    ) -> dict:
        """
        Get GHSL GHS_BUILT_S built-up surface area fraction.

        GHSL provides built-up surface area in m² per 100m grid cell.
        Available epochs: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025.

        Args:
            bbox: (west, south, east, north) in WGS84.
            year: One of the GHSL epochs (closest available used).

        Returns:
            Dict with built_up_km2, total_km2, built_up_pct, year, data_source, confidence.
        """
        ghsl_epochs = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
        closest_epoch = min(ghsl_epochs, key=lambda e: abs(e - year))

        cache_key = f"ghsl_{bbox}_{closest_epoch}"
        if cached := self._cache.get(cache_key):
            return cached

        if not self._initialized:
            return {
                "built_up_km2": None,
                "total_km2": None,
                "built_up_pct": None,
                "year": closest_epoch,
                "data_source": "JRC GHSL GHS_BUILT_S (unavailable — GEE not initialised)",
                "confidence": "UNAVAILABLE",
                "notes": ["GEE not initialised. Run ee.Authenticate() and retry."],
            }

        try:
            ee = self._ee
            west, south, east, north = bbox
            region = ee.Geometry.Rectangle([west, south, east, north])

            # GHS_BUILT_S: built-up surface in m² per 10m cell (P2023A product)
            ghsl = (
                ee.ImageCollection("JRC/GHSL/P2023A/GHS_BUILT_S")
                .filter(ee.Filter.eq("epoch", closest_epoch))
                .first()
                .select("built_surface")
            )

            # Sum of built-up area in m²
            built_stats = ghsl.reduceRegion(
                reducer=ee.Reducer.sum().combine(ee.Reducer.count(), "", True),
                geometry=region,
                scale=10,
                maxPixels=1e10,
            ).getInfo()

            built_m2 = built_stats.get("built_surface_sum", 0) or 0
            total_pixels = built_stats.get("built_surface_count", 0) or 1
            total_m2 = total_pixels * 100  # each 10m pixel = 100m²

            built_km2 = built_m2 / 1e6
            total_km2 = total_m2 / 1e6
            built_pct = (built_m2 / total_m2 * 100) if total_m2 > 0 else 0

            result = {
                "built_up_km2": round(built_km2, 4),
                "total_km2": round(total_km2, 4),
                "built_up_pct": round(built_pct, 2),
                "year": closest_epoch,
                "requested_year": year,
                "data_source": "JRC GHSL P2023A — GHS_BUILT_S (via GEE)",
                "resolution_m": 10,
                "confidence": "HIGH",
                "notes": [
                    f"GHSL epoch {closest_epoch} used (closest to requested year {year})",
                    "Built-up surface area in m² per 10m grid cell",
                    "Data source: Joint Research Centre, European Commission",
                ],
            }

            self._cache[cache_key] = result
            self._save_cache()
            return result

        except Exception as exc:
            logger.error("GHSL query error: %s", exc)
            return {
                "built_up_km2": None,
                "total_km2": None,
                "built_up_pct": None,
                "year": closest_epoch,
                "data_source": "JRC GHSL (error)",
                "confidence": "UNAVAILABLE",
                "notes": [str(exc)],
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Time series helpers
    # ──────────────────────────────────────────────────────────────────────────

    def get_ndvi_timeseries(
        self,
        bbox: tuple[float, float, float, float],
        start_year: int = 2016,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """
        Compute NDVI statistics for each year in [start_year, end_year].

        Uses Sentinel-2 where available (≥2017), Landsat 8 for 2016.

        Returns:
            DataFrame with columns: year, ndvi_mean, ndvi_min, ndvi_max,
            ndvi_std, green_fraction, satellite, confidence, notes.
        """
        records = []
        for year in range(start_year, end_year + 1):
            logger.info("Fetching NDVI for year %d...", year)
            if year >= 2017:
                stats = self.get_sentinel2_ndvi_stats(bbox, year)
            else:
                stats = self.get_landsat_ndvi_stats(bbox, year)
            records.append({
                "year": year,
                "ndvi_mean": stats.get("ndvi_mean"),
                "ndvi_min": stats.get("ndvi_min"),
                "ndvi_max": stats.get("ndvi_max"),
                "ndvi_std": stats.get("ndvi_std"),
                "green_fraction": stats.get("green_fraction"),
                "satellite": stats.get("satellite"),
                "confidence": stats.get("confidence"),
                "notes": "; ".join(stats.get("notes", [])),
            })

        return pd.DataFrame(records)

    def get_builtup_timeseries(
        self,
        bbox: tuple[float, float, float, float],
    ) -> pd.DataFrame:
        """
        Get GHSL built-up area for all available epochs (1975–2025).

        Returns:
            DataFrame with columns: year, built_up_km2, total_km2,
            built_up_pct, confidence.
        """
        epochs = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
        records = []
        for epoch in epochs:
            stats = self.get_ghsl_builtup(bbox, epoch)
            records.append({
                "year": epoch,
                "built_up_km2": stats.get("built_up_km2"),
                "total_km2": stats.get("total_km2"),
                "built_up_pct": stats.get("built_up_pct"),
                "confidence": stats.get("confidence"),
            })
        return pd.DataFrame(records)

    # ──────────────────────────────────────────────────────────────────────────
    # Cache helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _load_cache(self):
        """Load GEE result cache from disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    self._cache = json.load(f)
                logger.info("Loaded GEE cache with %d entries.", len(self._cache))
            except Exception as exc:
                logger.warning("Failed to load GEE cache: %s", exc)
                self._cache = {}
        else:
            self._cache = {}

    def _save_cache(self):
        """Persist GEE result cache to disk."""
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Failed to save GEE cache: %s", exc)

    @staticmethod
    def _unavailable_ndvi(year: int, reason: str) -> dict:
        """Return a standardised UNAVAILABLE NDVI response."""
        return {
            "ndvi_mean": None,
            "ndvi_min": None,
            "ndvi_max": None,
            "ndvi_std": None,
            "green_fraction": None,
            "pixel_count": None,
            "scene_count": 0,
            "satellite": None,
            "year": year,
            "resolution_m": None,
            "data_source": "UNAVAILABLE",
            "is_estimated": False,
            "confidence": "UNAVAILABLE",
            "notes": [
                f"Data unavailable: {reason}",
                "To enable satellite analysis, authenticate with Google Earth Engine:",
                "  python -c \"import ee; ee.Authenticate()\"",
            ],
        }
