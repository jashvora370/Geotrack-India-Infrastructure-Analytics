"""
GeoTrack India — PostGIS Data Loader
=====================================
Loads processed GeoDataFrames and analytical metrics into PostgreSQL / PostGIS.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class PostGISLoader:
    """Loads GeoDataFrames and analytical summary tables into PostgreSQL / PostGIS."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)

    def load_road_segments(
        self,
        gdf: gpd.GeoDataFrame,
        region_id: int,
        year: int,
        source: str = "ohsome",
    ) -> int:
        """
        Store road segments in the database.
        Converts geometries to WKT text or PostGIS geometry.
        """
        if gdf.empty:
            logger.warning("Empty GeoDataFrame provided to load_road_segments.")
            return 0

        df = gdf.copy()
        if df.crs is not None and df.crs.to_epsg() != 4326:
            df = df.to_crs("EPSG:4326")

        # Prepare columns matching schema
        df["region_id"] = region_id
        df["year"] = year
        df["source"] = source
        df["geometry"] = df.geometry.apply(lambda g: g.wkt if g is not None else None)

        if "osm_id" not in df.columns:
            if "osmid" in df.columns:
                df["osm_id"] = df["osmid"]
            elif "@id" in df.columns:
                df["osm_id"] = df["@id"].astype(str).str.replace("way/", "", regex=False)
            else:
                df["osm_id"] = range(1, len(df) + 1)

        keep_cols = [
            "osm_id", "region_id", "name", "highway", "surface", "lanes",
            "width_m", "geometry", "year", "source", "length_km"
        ]
        available_cols = [c for c in keep_cols if c in df.columns]
        upload_df = pd.DataFrame(df[available_cols])

        # Write to road_segments
        try:
            upload_df.to_sql("road_segments", self.engine, if_exists="append", index=False, chunksize=1000)
            logger.info("Successfully loaded %d road segments for year %d into PostGIS.", len(upload_df), year)
            return len(upload_df)
        except Exception as exc:
            logger.error("Failed to load road segments: %s", exc)
            return 0

    def load_change_detection_results(self, result: Dict[str, Any]) -> bool:
        """Insert or update change detection KPI record."""
        sql = text("""
            INSERT INTO change_detection_results (
                region_id, year_from, year_to, new_roads_km, removed_roads_km,
                widened_roads_km, unchanged_km, pct_growth, segments_added,
                segments_removed, data_quality_note
            ) VALUES (
                :region_id, :year_from, :year_to, :new_roads_km, :removed_roads_km,
                :widened_roads_km, :unchanged_km, :pct_growth, :segments_added,
                :segments_removed, :data_quality_note
            )
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(sql, result)
            logger.info("Change detection result stored.")
            return True
        except Exception as exc:
            logger.error("Failed to store change detection result: %s", exc)
            return False

    def load_network_metrics(self, region_id: int, year: int, metrics: Dict[str, Any]) -> bool:
        """Insert network level stats."""
        sql = text("""
            INSERT INTO road_networks (
                region_id, year, total_length_km, road_count, avg_width_m,
                density, avg_degree, avg_betweenness, avg_clustering
            ) VALUES (
                :region_id, :year, :total_length_km, :road_count, :avg_width_m,
                :density, :avg_degree, :avg_betweenness, :avg_clustering
            ) ON CONFLICT (region_id, year) DO UPDATE SET
                total_length_km = EXCLUDED.total_length_km,
                road_count = EXCLUDED.road_count,
                density = EXCLUDED.density,
                avg_degree = EXCLUDED.avg_degree;
        """)
        params = {
            "region_id": region_id,
            "year": year,
            "total_length_km": metrics.get("total_length_km", 0.0),
            "road_count": metrics.get("road_count", metrics.get("edge_count", 0)),
            "avg_width_m": metrics.get("avg_width_m", 0.0),
            "density": metrics.get("road_density_km_per_km2", 0.0),
            "avg_degree": metrics.get("avg_degree", 0.0),
            "avg_betweenness": metrics.get("avg_betweenness", 0.0),
            "avg_clustering": metrics.get("avg_clustering", 0.0),
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(sql, params)
            return True
        except Exception as exc:
            logger.error("Failed to store network metrics: %s", exc)
            return False
