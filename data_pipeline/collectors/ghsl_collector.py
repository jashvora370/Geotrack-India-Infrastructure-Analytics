"""
GHSL Built-up Data Collector
==============================
Downloads Global Human Settlement Layer (GHSL) GHS_BUILT_S tiles for India,
clips them to the study area, and computes built-up fraction per epoch year.

Data source:
  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/

Tiles for India (Mollweide grid):
  - R8_C31  (western India — covers e.g. Pune, Mumbai, Gujarat)
  - R8_C32  (central India — covers e.g. Bhopal, parts of Maharashtra)

Epochs available:
  1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025

Resolution: 100 m (Mollweide EPSG:54009)

Usage::

    from collectors.ghsl_collector import GhslCollector

    collector = GhslCollector(data_dir="./data/ghsl")
    df = collector.collect_built_up_timeseries(
        bbox=(73.75, 18.35, 74.05, 18.65),
        tiles=["R8_C31"],
    )
    print(df)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GHSL_BASE_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_BUILT_S_GLOBE_R2023A/GHS_BUILT_S_E{year}_GLOBE_R2023A_54009_100/V1-0/"
    "tiles/GHS_BUILT_S_E{year}_GLOBE_R2023A_54009_100_V1_0_{tile}.zip"
)

INDIA_TILES = ["R8_C31", "R8_C32"]

GHSL_EPOCHS = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]

# Mollweide CRS used by GHSL tiles
GHSL_CRS = "ESRI:54009"

# UTM Zone 43N — used for area calculations over Pune/Maharashtra
PROJECTED_CRS = "EPSG:32643"

RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2.0


def _build_session() -> requests.Session:
    """Build a requests.Session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=RETRY_ATTEMPTS,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _bbox_wgs84_to_mollweide(
    bbox_wgs84: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """
    Reproject a WGS-84 bounding box to Mollweide (ESRI:54009).

    Returns (west, south, east, north) in Mollweide metres.
    """
    try:
        from pyproj import Transformer  # type: ignore

        transformer = Transformer.from_crs("EPSG:4326", GHSL_CRS, always_xy=True)
        west, south, east, north = bbox_wgs84
        # Project the four corners and take the extremes
        xs, ys = transformer.transform(
            [west, east, west, east], [south, south, north, north]
        )
        return min(xs), min(ys), max(xs), max(ys)
    except ImportError:
        raise ImportError("pyproj is required for GHSL CRS reprojection. pip install pyproj")


class GhslCollector:
    """
    Downloads and processes GHSL GHS_BUILT_S tiles to compute built-up
    statistics for a user-defined bounding box.

    Parameters
    ----------
    data_dir : str or Path
        Directory where downloaded tiles and clipped GeoTIFFs are cached.
    """

    def __init__(self, data_dir: str | Path = "./data/ghsl") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._session = _build_session()
        logger.info("GhslCollector initialised (data_dir=%s)", self.data_dir)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_tile(self, year: int, tile: str) -> Optional[Path]:
        """
        Download a GHSL tile ZIP and extract the GeoTIFF.

        Parameters
        ----------
        year : int
            GHSL epoch year (e.g. 2020).
        tile : str
            Tile identifier, e.g. 'R8_C31'.

        Returns
        -------
        Path or None
            Path to the extracted .tif file, or None on failure.
        """
        try:
            import zipfile
        except ImportError:
            pass  # stdlib — always available

        url = GHSL_BASE_URL.format(year=year, tile=tile)
        zip_dest = self.data_dir / f"GHS_BUILT_S_{year}_{tile}.zip"
        tif_dir = self.data_dir / f"{year}_{tile}"

        # Check if already extracted
        existing_tifs = list(tif_dir.glob("*.tif")) if tif_dir.exists() else []
        if existing_tifs:
            logger.debug("Tile already cached: %s", existing_tifs[0])
            return existing_tifs[0]

        logger.info("Downloading GHSL tile: year=%d, tile=%s", year, tile)
        try:
            with self._session.get(url, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(zip_dest, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        fh.write(chunk)
                        downloaded += len(chunk)
            logger.info("Downloaded %.1f MB → %s", zip_dest.stat().st_size / 1e6, zip_dest)
        except Exception as exc:
            logger.error("Failed to download GHSL tile %s/%d: %s", tile, year, exc)
            return None

        # Extract
        tif_dir.mkdir(exist_ok=True)
        try:
            import zipfile

            with zipfile.ZipFile(zip_dest, "r") as zf:
                zf.extractall(tif_dir)
            zip_dest.unlink(missing_ok=True)
            tif_files = list(tif_dir.glob("*.tif"))
            if tif_files:
                logger.info("Extracted → %s", tif_files[0])
                return tif_files[0]
            logger.error("No .tif found in ZIP for tile=%s year=%d", tile, year)
            return None
        except Exception as exc:
            logger.error("Extraction failed for tile=%s year=%d: %s", tile, year, exc)
            return None

    # ------------------------------------------------------------------
    # Clip to study area
    # ------------------------------------------------------------------

    def clip_to_bbox(
        self,
        tif_path: Path,
        bbox_wgs84: tuple[float, float, float, float],
        output_path: Path,
    ) -> Optional[Path]:
        """
        Clip a GHSL GeoTIFF to a WGS-84 bounding box and save the result.

        Uses rasterio with windowed reading; no in-memory resampling.

        Parameters
        ----------
        tif_path : Path
        bbox_wgs84 : tuple
            (west, south, east, north) in WGS-84.
        output_path : Path

        Returns
        -------
        Path or None
        """
        try:
            import rasterio  # type: ignore
            from rasterio.mask import mask as rio_mask  # type: ignore
            from shapely.geometry import box, mapping  # type: ignore

            west, south, east, north = bbox_wgs84
            # Build a WGS-84 polygon and reproject to GHSL CRS for masking
            from pyproj import Transformer  # type: ignore

            transformer = Transformer.from_crs("EPSG:4326", GHSL_CRS, always_xy=True)
            xs, ys = transformer.transform(
                [west, east, west, east], [south, south, north, north]
            )
            mol_bbox = box(min(xs), min(ys), max(xs), max(ys))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(str(tif_path)) as src:
                out_image, out_transform = rio_mask(src, [mapping(mol_bbox)], crop=True)
                out_meta = src.meta.copy()
                out_meta.update(
                    {
                        "driver": "GTiff",
                        "height": out_image.shape[1],
                        "width": out_image.shape[2],
                        "transform": out_transform,
                    }
                )
                with rasterio.open(str(output_path), "w", **out_meta) as dest:
                    dest.write(out_image)
            logger.info("Clipped GeoTIFF → %s", output_path)
            return output_path
        except Exception as exc:
            logger.error("clip_to_bbox failed for %s: %s", tif_path, exc)
            return None

    # ------------------------------------------------------------------
    # Built-up statistics
    # ------------------------------------------------------------------

    def compute_built_up_stats(
        self,
        clipped_tif: Path,
        year: int,
    ) -> dict[str, float]:
        """
        Compute built-up area statistics from a clipped GHSL GeoTIFF.

        The GHS_BUILT_S layer encodes built-up surface area in m² per 100 m pixel.
        Pixels with NoData value (−32768 or 0) are excluded.

        Parameters
        ----------
        clipped_tif : Path
        year : int

        Returns
        -------
        dict
            Keys: year, built_up_km2, total_km2, built_up_pct.
        """
        try:
            import rasterio  # type: ignore

            with rasterio.open(str(clipped_tif)) as src:
                data = src.read(1).astype("float32")
                nodata = src.nodata if src.nodata is not None else -32768
                pixel_area_m2 = abs(src.transform.a * src.transform.e)  # pixel width × height

            # Mask nodata
            valid_mask = (data != nodata) & (data >= 0)
            total_pixels = int(valid_mask.sum())
            total_m2 = total_pixels * pixel_area_m2
            total_km2 = total_m2 / 1e6

            # Built-up pixels: value > 0 (built-up area in m²)
            built_mask = valid_mask & (data > 0)
            built_sum_m2 = float(data[built_mask].sum())
            built_km2 = built_sum_m2 / 1e6

            built_pct = 100.0 * built_km2 / total_km2 if total_km2 > 0 else 0.0
            return {
                "year": year,
                "built_up_km2": round(built_km2, 4),
                "total_km2": round(total_km2, 4),
                "built_up_pct": round(built_pct, 4),
            }
        except Exception as exc:
            logger.error("compute_built_up_stats failed for %s: %s", clipped_tif, exc)
            return {"year": year, "built_up_km2": float("nan"), "total_km2": float("nan"), "built_up_pct": float("nan")}

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def collect_built_up_timeseries(
        self,
        bbox: tuple[float, float, float, float],
        tiles: Optional[list[str]] = None,
        epochs: Optional[list[int]] = None,
    ) -> pd.DataFrame:
        """
        Download, clip and compute built-up statistics for multiple tiles and epochs.

        If multiple tiles overlap the study area, their built-up values are summed.

        Parameters
        ----------
        bbox : tuple
            (west, south, east, north) in WGS-84.
        tiles : list of str, optional
            GHSL tile IDs; defaults to INDIA_TILES = ['R8_C31', 'R8_C32'].
        epochs : list of int, optional
            Years to process; defaults to GHSL_EPOCHS.

        Returns
        -------
        pd.DataFrame
            Columns: year, built_up_km2, total_km2, built_up_pct.
        """
        if tiles is None:
            tiles = INDIA_TILES
        if epochs is None:
            epochs = GHSL_EPOCHS

        rows: list[dict] = []
        for year in epochs:
            combined_built_km2 = 0.0
            combined_total_km2 = 0.0
            tile_count = 0
            for tile in tiles:
                tif_path = self.download_tile(year, tile)
                if tif_path is None:
                    logger.warning("Skipping tile=%s year=%d (download failed)", tile, year)
                    continue
                clip_path = self.data_dir / f"clipped_{year}_{tile}.tif"
                clipped = self.clip_to_bbox(tif_path, bbox, clip_path)
                if clipped is None:
                    logger.warning("Skipping tile=%s year=%d (clip failed)", tile, year)
                    continue
                stats = self.compute_built_up_stats(clipped, year)
                combined_built_km2 += stats.get("built_up_km2", 0.0) or 0.0
                # Take the largest total_km2 (tiles overlap at boundary)
                combined_total_km2 = max(combined_total_km2, stats.get("total_km2", 0.0) or 0.0)
                tile_count += 1

            if tile_count == 0:
                logger.warning("No valid tiles for year=%d; recording NaN.", year)
                rows.append({"year": year, "built_up_km2": float("nan"), "total_km2": float("nan"), "built_up_pct": float("nan")})
            else:
                pct = 100.0 * combined_built_km2 / combined_total_km2 if combined_total_km2 > 0 else 0.0
                rows.append(
                    {
                        "year": year,
                        "built_up_km2": round(combined_built_km2, 4),
                        "total_km2": round(combined_total_km2, 4),
                        "built_up_pct": round(pct, 4),
                    }
                )
                logger.info(
                    "Year %d: built-up=%.2f km² (%.2f%% of %.2f km²)",
                    year, combined_built_km2, pct, combined_total_km2,
                )

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("year").reset_index(drop=True)
        return df
