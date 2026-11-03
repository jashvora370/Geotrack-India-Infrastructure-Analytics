# app/models/analysis_result.py
"""
SQLAlchemy ORM models for analysis result storage.

Models:
    ChangeDetectionResult – Change statistics between two road network snapshots.
    LandUseAnalysis       – Land-use / land-cover composition derived from satellite data.
    RoadWidthAnalysis     – Statistical width breakdown for a region in a given year.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# ChangeDetectionResult
# ─────────────────────────────────────────────────────────────────────────────

class ChangeDetectionResult(Base):
    """
    Stores the outcome of a road network change-detection run.

    Values are derived by the :class:`~app.services.change_detection.RoadChangeDetector`
    service after spatially joining two annual road network snapshots.

    Attributes:
        id                  Primary key.
        region_id           FK to ``region_boundaries.id``.
        year_from           Start year of the comparison window.
        year_to             End year of the comparison window.
        new_roads_km        Length (km) of roads present in year_to but not year_from.
        removed_roads_km    Length (km) of roads present in year_from but not year_to.
        widened_roads_km    Length (km) of roads that were widened between the two years.
        unchanged_km        Length (km) of roads with no detected change.
        pct_growth          Percentage growth in total road length.
        segments_added      Count of newly added road segments.
        segments_removed    Count of removed road segments.
        data_quality_note   Free-text caveat (e.g. OSM completeness warning).
        created_at          Row insertion timestamp.
    """

    __tablename__ = "change_detection_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("region_boundaries.id", ondelete="CASCADE"), index=True
    )
    year_from: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    new_roads_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    removed_roads_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    widened_roads_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unchanged_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    segments_added: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    segments_removed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_quality_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ChangeDetectionResult region_id={self.region_id} "
            f"{self.year_from}→{self.year_to}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LandUseAnalysis
# ─────────────────────────────────────────────────────────────────────────────

class LandUseAnalysis(Base):
    """
    Land-use / land-cover (LULC) composition for a region in a given year.

    Percentages are derived from satellite imagery (e.g. Sentinel-2, Landsat)
    processed through Google Earth Engine.  NDVI statistics characterise
    vegetation health.

    Attributes:
        id              Primary key.
        region_id       FK to ``region_boundaries.id``.
        year            Year of the satellite observation.
        built_up_pct    Percentage of built-up / impervious area.
        vegetation_pct  Percentage of vegetated area.
        agriculture_pct Percentage of agricultural land.
        water_pct       Percentage of water bodies.
        bare_land_pct   Percentage of bare / exposed soil.
        ndvi_mean       Mean NDVI value across the region.
        ndvi_min        Minimum NDVI value.
        ndvi_max        Maximum NDVI value.
        data_source     Satellite product name (e.g. ``Sentinel-2 L2A``).
        resolution_m    Spatial resolution of the source imagery in metres.
        created_at      Row insertion timestamp.
    """

    __tablename__ = "land_use_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("region_boundaries.id", ondelete="CASCADE"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    built_up_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vegetation_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    agriculture_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    water_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bare_land_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ndvi_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ndvi_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ndvi_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    resolution_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<LandUseAnalysis region_id={self.region_id} year={self.year}>"


# ─────────────────────────────────────────────────────────────────────────────
# RoadWidthAnalysis
# ─────────────────────────────────────────────────────────────────────────────

class RoadWidthAnalysis(Base):
    """
    Statistical summary of road widths within a region for a given year.

    Width estimates come from OSM ``width`` tags, IRC standards applied to
    ``highway`` type and ``lanes`` count, or remote-sensing measurements.

    Percentage bands:
        * narrow   < 7 m   (single-lane / rural)
        * medium   7–14 m  (2-lane district road)
        * wide     14–30 m (4-lane arterial)
        * arterial > 30 m  (urban arterial / expressway)

    Attributes:
        id              Primary key.
        region_id       FK to ``region_boundaries.id``.
        year            Year of the analysis.
        avg_width_m     Mean road width in metres.
        max_width_m     Maximum road width in metres.
        min_width_m     Minimum road width in metres.
        pct_narrow      Percentage of narrow roads.
        pct_medium      Percentage of medium roads.
        pct_wide        Percentage of wide roads.
        pct_arterial    Percentage of arterial / expressway roads.
        pct_highway     Percentage of roads tagged as ``motorway`` / ``trunk``.
        methodology     Short description of width estimation method.
        confidence      Overall confidence score (0–1).
        created_at      Row insertion timestamp.
    """

    __tablename__ = "road_width_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("region_boundaries.id", ondelete="CASCADE"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    avg_width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_narrow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_medium: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_wide: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_arterial: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pct_highway: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RoadWidthAnalysis region_id={self.region_id} year={self.year}>"
