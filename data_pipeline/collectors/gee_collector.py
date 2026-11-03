"""
Google Earth Engine Imagery Collector
======================================
Fetches Landsat 8/9 and Sentinel-2 imagery for NDVI and land cover analysis.

Prerequisites:
  1. Install earthengine-api: pip install earthengine-api
  2. Authenticate: python -c "import ee; ee.Authenticate()"
  3. Or use service account: ee.Initialize(credentials=...)

Data sources:
  - Landsat 8 OLI/TIRS: LANDSAT/LC08/C02/T1_L2 (2013-present, 30m resolution)
  - Landsat 9 OLI-2/TIRS-2: LANDSAT/LC09/C02/T1_L2 (2021-present, 30m resolution)
  - Sentinel-2 MSI: COPERNICUS/S2_SR_HARMONIZED (2017-present, 10m resolution)
  - ESA WorldCover: ESA/WorldCover/v200 (2021, 10m)
  - GHSL Built-up: JRC/GHSL/P2023A/GHS_BUILT_S (1975-2030, 10m)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Attempt to import earthengine-api lazily so the module can be imported even
# when the package is not installed.
try:
    import ee  # type: ignore

    _EE_AVAILABLE = True
except ImportError:
    _EE_AVAILABLE = False
    logger.warning(
        "earthengine-api not installed. GeeCollector will operate in fallback mode. "
        "Install with: pip install earthengine-api"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LANDSAT8_COLLECTION = "LANDSAT/LC08/C02/T1_L2"
_LANDSAT9_COLLECTION = "LANDSAT/LC09/C02/T1_L2"
_S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
_ESA_WORLDCOVER = "ESA/WorldCover/v200"
_GHSL_BUILT_S = "JRC/GHSL/P2023A/GHS_BUILT_S"

# Land class values in ESA WorldCover
_ESA_CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def _bbox_to_ee_geometry(bbox: tuple[float, float, float, float]) -> "ee.Geometry.Rectangle":
    """Convert (west, south, east, north) to an ee.Geometry.Rectangle."""
    west, south, east, north = bbox
    return ee.Geometry.Rectangle([west, south, east, north])


def _load_fallback_cache(cache_path: str | Path) -> dict[str, Any]:
    """Load pre-computed stats from a JSON cache file."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


class GeeCollector:
    """
    Collects satellite imagery and derived indices from Google Earth Engine.

    When GEE is unavailable (not installed, not authenticated, or quota
    exceeded) the collector transparently falls back to pre-computed stats
    stored in ``./cache/gee_cache.json``.

    Parameters
    ----------
    cache_dir : str or Path
        Directory containing ``gee_cache.json`` for fallback mode.
    """

    def __init__(self, cache_dir: str | Path = "./cache") -> None:
        self._initialized = False
        self._fallback_mode = not _EE_AVAILABLE
        self._cache_dir = Path(cache_dir)
        self._cache: dict[str, Any] = {}
        if self._fallback_mode:
            logger.warning("GeeCollector starting in fallback mode (GEE not available).")
            self._cache = _load_fallback_cache(self._cache_dir / "gee_cache.json")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def initialize(
        self,
        service_account: Optional[str] = None,
        key_file: Optional[str] = None,
        project: Optional[str] = None,
    ) -> bool:
        """
        Authenticate and initialise the GEE API.

        Parameters
        ----------
        service_account : str, optional
            Service account email address.
        key_file : str, optional
            Path to the service-account JSON key file.
        project : str, optional
            GCP project ID to use for GEE calls.

        Returns
        -------
        bool
            True if initialisation succeeded; False otherwise.
        """
        if not _EE_AVAILABLE:
            logger.error("earthengine-api is not installed; cannot initialise GEE.")
            return False

        try:
            if service_account and key_file:
                credentials = ee.ServiceAccountCredentials(service_account, key_file)
                ee.Initialize(credentials=credentials, project=project)
                logger.info("GEE initialised with service account: %s", service_account)
            else:
                ee.Initialize(project=project)
                logger.info("GEE initialised with user credentials.")
            self._initialized = True
            self._fallback_mode = False
            return True
        except Exception as exc:  # includes ee.EEException
            logger.error("GEE initialisation failed: %s. Switching to fallback mode.", exc)
            self._fallback_mode = True
            self._cache = _load_fallback_cache(self._cache_dir / "gee_cache.json")
            return False

    def _require_gee(self) -> bool:
        """Return True if GEE is usable; log warning and return False otherwise."""
        if not self._initialized or self._fallback_mode:
            logger.warning("GEE is unavailable; returning cached/fallback result.")
            return False
        return True

    # ------------------------------------------------------------------
    # Landsat composites
    # ------------------------------------------------------------------

    def get_landsat_composite(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
        cloud_pct: float = 20.0,
    ) -> Optional["ee.Image"]:
        """
        Build a cloud-free annual Landsat composite for *year*.

        Uses Landsat 9 when available (2022+), otherwise Landsat 8.
        Applies Collection 2 SR scaling factors:
          - Optical: DN × 0.0000275 − 0.2
          - Thermal: DN × 0.00341802 + 149.0

        Parameters
        ----------
        bbox : tuple
            (west, south, east, north).
        year : int
            Target year.
        cloud_pct : float
            Maximum cloud cover percentage for scene filtering.

        Returns
        -------
        ee.Image or None
            Scaled image with bands including NDVI, or None on error.
        """
        if not self._require_gee():
            return None
        try:
            region = _bbox_to_ee_geometry(bbox)
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            collection_id = _LANDSAT9_COLLECTION if year >= 2022 else _LANDSAT8_COLLECTION

            def apply_scale_factors(image: "ee.Image") -> "ee.Image":
                optical = image.select("SR_B.").multiply(0.0000275).add(-0.2)
                thermal = image.select("ST_B.*").multiply(0.00341802).add(149.0)
                return image.addBands(optical, None, True).addBands(thermal, None, True)

            collection = (
                ee.ImageCollection(collection_id)
                .filterBounds(region)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt("CLOUD_COVER", cloud_pct))
                .map(apply_scale_factors)
            )
            composite = collection.median().clip(region)
            # Landsat 8/9: NIR = SR_B5, Red = SR_B4
            ndvi = composite.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
            composite = composite.addBands(ndvi)
            logger.info("Landsat composite built for year=%d (collection=%s)", year, collection_id)
            return composite
        except Exception as exc:
            logger.error("get_landsat_composite failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Sentinel-2 composites
    # ------------------------------------------------------------------

    def get_sentinel2_composite(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
        cloud_pct: float = 20.0,
    ) -> Optional["ee.Image"]:
        """
        Build a cloud-free annual Sentinel-2 SR composite for *year*.

        Applies SCL-based cloud masking and BOA scaling (÷ 10000).

        Parameters
        ----------
        bbox : tuple
        year : int
        cloud_pct : float

        Returns
        -------
        ee.Image or None
        """
        if not self._require_gee():
            return None
        try:
            region = _bbox_to_ee_geometry(bbox)
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            def mask_s2_clouds(image: "ee.Image") -> "ee.Image":
                scl = image.select("SCL")
                mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
                return image.updateMask(mask).divide(10000)

            collection = (
                ee.ImageCollection(_S2_COLLECTION)
                .filterBounds(region)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
                .map(mask_s2_clouds)
            )
            composite = collection.median().clip(region)
            # S2: NIR = B8, Red = B4
            ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
            composite = composite.addBands(ndvi)
            logger.info("Sentinel-2 composite built for year=%d", year)
            return composite
        except Exception as exc:
            logger.error("get_sentinel2_composite failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # NDVI statistics
    # ------------------------------------------------------------------

    def compute_ndvi_stats(
        self,
        image: "ee.Image",
        region: "ee.Geometry",
    ) -> dict[str, float]:
        """
        Compute NDVI statistics for *image* within *region*.

        Parameters
        ----------
        image : ee.Image
            Image containing an 'NDVI' band.
        region : ee.Geometry

        Returns
        -------
        dict
            Keys: mean_ndvi, min_ndvi, max_ndvi, std_ndvi, green_fraction.
        """
        if not self._require_gee():
            return {
                "mean_ndvi": float("nan"),
                "min_ndvi": float("nan"),
                "max_ndvi": float("nan"),
                "std_ndvi": float("nan"),
                "green_fraction": float("nan"),
            }
        try:
            ndvi_band = image.select("NDVI")
            stats = ndvi_band.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), "", True)
                .combine(ee.Reducer.max(), "", True)
                .combine(ee.Reducer.stdDev(), "", True),
                geometry=region,
                scale=30,
                maxPixels=1e10,
            ).getInfo()
            mean_ndvi = stats.get("NDVI_mean", float("nan"))
            # Green fraction: pixels with NDVI > 0.3
            green_mask = ndvi_band.gt(0.3)
            area_stats = (
                green_mask.multiply(ee.Image.pixelArea())
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=30,
                    maxPixels=1e10,
                )
                .getInfo()
            )
            total_area = ee.Image.pixelArea().reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=region,
                scale=30,
                maxPixels=1e10,
            ).getInfo()
            green_area = area_stats.get("NDVI", 0.0) or 0.0
            total = total_area.get("area", 1.0) or 1.0
            return {
                "mean_ndvi": mean_ndvi if mean_ndvi is not None else float("nan"),
                "min_ndvi": stats.get("NDVI_min", float("nan")),
                "max_ndvi": stats.get("NDVI_max", float("nan")),
                "std_ndvi": stats.get("NDVI_stdDev", float("nan")),
                "green_fraction": green_area / total,
            }
        except Exception as exc:
            logger.error("compute_ndvi_stats failed: %s", exc)
            return {
                "mean_ndvi": float("nan"),
                "min_ndvi": float("nan"),
                "max_ndvi": float("nan"),
                "std_ndvi": float("nan"),
                "green_fraction": float("nan"),
            }

    # ------------------------------------------------------------------
    # GHSL built-up fraction
    # ------------------------------------------------------------------

    def get_land_cover_ghsl(
        self,
        bbox: tuple[float, float, float, float],
        year: int,
    ) -> dict[str, float]:
        """
        Retrieve GHSL built-up fraction for *year* within *bbox*.

        The GHS_BUILT_S layer provides built-up surface area in m² per pixel.

        Parameters
        ----------
        bbox : tuple
        year : int
            One of: 1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025.

        Returns
        -------
        dict
            Keys: year, built_up_km2, total_km2, built_up_pct.
        """
        if not self._require_gee():
            cache_key = f"ghsl_{year}_{'_'.join(str(int(v)) for v in bbox)}"
            return self._cache.get(cache_key, {"year": year, "built_up_km2": float("nan"), "total_km2": float("nan"), "built_up_pct": float("nan")})
        try:
            region = _bbox_to_ee_geometry(bbox)
            # GHSL epoch bands are named by year string
            ghsl = ee.ImageCollection(_GHSL_BUILT_S).filterBounds(region)
            # Select image closest to requested year
            image = ghsl.filter(ee.Filter.calendarRange(year, year, "year")).first()
            if image is None:
                image = ghsl.sort("system:time_start", False).first()

            built_sum = image.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=region,
                scale=100,
                maxPixels=1e10,
            ).getInfo()
            total_area = (
                ee.Image.pixelArea()
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=100,
                    maxPixels=1e10,
                )
                .getInfo()
            )
            built_m2 = list(built_sum.values())[0] if built_sum else 0.0
            total_m2 = total_area.get("area", 1.0) or 1.0
            built_km2 = built_m2 / 1e6
            total_km2 = total_m2 / 1e6
            return {
                "year": year,
                "built_up_km2": built_km2,
                "total_km2": total_km2,
                "built_up_pct": 100.0 * built_km2 / total_km2 if total_km2 > 0 else 0.0,
            }
        except Exception as exc:
            logger.error("get_land_cover_ghsl failed: %s", exc)
            return {"year": year, "built_up_km2": float("nan"), "total_km2": float("nan"), "built_up_pct": float("nan")}

    # ------------------------------------------------------------------
    # ESA WorldCover
    # ------------------------------------------------------------------

    def get_esaWorldCover(
        self,
        bbox: tuple[float, float, float, float],
    ) -> dict[str, float]:
        """
        Compute ESA WorldCover 2021 land cover class fractions within *bbox*.

        Returns
        -------
        dict
            Mapping of class name → fractional area (0–1).
        """
        if not self._require_gee():
            return self._cache.get("esa_worldcover", {})
        try:
            region = _bbox_to_ee_geometry(bbox)
            worldcover = ee.ImageCollection(_ESA_WORLDCOVER).first().clip(region)
            total_area = (
                ee.Image.pixelArea()
                .reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=region,
                    scale=10,
                    maxPixels=1e12,
                )
                .getInfo()
                .get("area", 1.0)
            )
            result: dict[str, float] = {}
            for class_val, class_name in _ESA_CLASS_NAMES.items():
                mask = worldcover.eq(class_val)
                class_area = (
                    mask.multiply(ee.Image.pixelArea())
                    .reduceRegion(
                        reducer=ee.Reducer.sum(),
                        geometry=region,
                        scale=10,
                        maxPixels=1e12,
                    )
                    .getInfo()
                )
                area_m2 = list(class_area.values())[0] if class_area else 0.0
                result[class_name] = area_m2 / max(total_area, 1)
            logger.info("ESA WorldCover fractions computed for %d classes", len(result))
            return result
        except Exception as exc:
            logger.error("get_esaWorldCover failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Land cover change
    # ------------------------------------------------------------------

    def compute_land_cover_change(
        self,
        bbox: tuple[float, float, float, float],
        year1: int,
        year2: int,
    ) -> dict[str, Any]:
        """
        Compute GHSL built-up change statistics between *year1* and *year2*.

        Parameters
        ----------
        bbox : tuple
        year1 : int
        year2 : int

        Returns
        -------
        dict
            Keys: built_up_km2_year1, built_up_km2_year2, change_km2,
            change_pct, built_up_pct_year1, built_up_pct_year2.
        """
        stats1 = self.get_land_cover_ghsl(bbox, year1)
        stats2 = self.get_land_cover_ghsl(bbox, year2)
        bu1 = stats1.get("built_up_km2", float("nan"))
        bu2 = stats2.get("built_up_km2", float("nan"))
        change_km2 = bu2 - bu1 if not (np.isnan(bu1) or np.isnan(bu2)) else float("nan")
        change_pct = (change_km2 / bu1 * 100.0) if bu1 and bu1 != 0 else float("nan")
        return {
            "built_up_km2_year1": bu1,
            "built_up_km2_year2": bu2,
            "change_km2": change_km2,
            "change_pct": change_pct,
            "built_up_pct_year1": stats1.get("built_up_pct", float("nan")),
            "built_up_pct_year2": stats2.get("built_up_pct", float("nan")),
        }

    # ------------------------------------------------------------------
    # Thumbnails
    # ------------------------------------------------------------------

    def export_thumbnail(
        self,
        image: "ee.Image",
        bbox: tuple[float, float, float, float],
        output_path: str | Path,
        year: int,
        dimensions: int = 512,
    ) -> None:
        """
        Export a false-colour RGB thumbnail as PNG.

        Parameters
        ----------
        image : ee.Image
        bbox : tuple
        output_path : str or Path
        year : int
        dimensions : int
            Width (and height) of the output PNG in pixels.
        """
        import io

        import requests
        from PIL import Image as PILImage  # type: ignore

        if not self._require_gee():
            logger.warning("Cannot export thumbnail: GEE unavailable.")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            region = _bbox_to_ee_geometry(bbox)
            url = image.getThumbURL(
                {
                    "bands": ["SR_B4", "SR_B3", "SR_B2"],
                    "region": region,
                    "dimensions": dimensions,
                    "format": "png",
                    "min": 0.0,
                    "max": 0.3,
                    "gamma": 1.4,
                }
            )
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            img = PILImage.open(io.BytesIO(response.content))
            img.save(str(output_path))
            logger.info("Thumbnail saved → %s (year=%d)", output_path, year)
        except Exception as exc:
            logger.error("export_thumbnail failed for year=%d: %s", year, exc)

    # ------------------------------------------------------------------
    # NDVI time-series
    # ------------------------------------------------------------------

    def get_yearly_ndvi_timeseries(
        self,
        bbox: tuple[float, float, float, float],
        start_year: int = 2016,
        end_year: int = 2026,
    ) -> pd.DataFrame:
        """
        Build a DataFrame of yearly mean NDVI statistics.

        When GEE is unavailable, returns data from the local cache.

        Parameters
        ----------
        bbox : tuple
        start_year : int
        end_year : int

        Returns
        -------
        pd.DataFrame
            Columns: year, mean_ndvi, min_ndvi, max_ndvi, std_ndvi, green_fraction.
        """
        cache_key = f"ndvi_timeseries_{'_'.join(str(int(v)) for v in bbox)}"
        if not self._require_gee():
            cached = self._cache.get(cache_key)
            if cached:
                logger.info("Returning cached NDVI timeseries (%d rows)", len(cached))
                return pd.DataFrame(cached)
            logger.warning("No cached NDVI data found; returning empty DataFrame.")
            return pd.DataFrame(
                columns=["year", "mean_ndvi", "min_ndvi", "max_ndvi", "std_ndvi", "green_fraction"]
            )

        region = _bbox_to_ee_geometry(bbox)
        rows = []
        for year in range(start_year, end_year + 1):
            logger.info("Computing NDVI stats for year=%d", year)
            try:
                if year >= 2017:
                    image = self.get_sentinel2_composite(bbox, year)
                else:
                    image = self.get_landsat_composite(bbox, year)
                if image is None:
                    logger.warning("No composite available for year=%d; skipping.", year)
                    continue
                stats = self.compute_ndvi_stats(image, region)
                stats["year"] = year
                rows.append(stats)
            except Exception as exc:
                logger.error("NDVI computation failed for year=%d: %s", year, exc)

        df = pd.DataFrame(rows)
        if not df.empty and "year" in df.columns:
            df = df[["year", "mean_ndvi", "min_ndvi", "max_ndvi", "std_ndvi", "green_fraction"]]
        logger.info("NDVI timeseries: %d years collected", len(df))
        return df
