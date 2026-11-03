# app/models/road_segment.py
"""
SQLAlchemy ORM models for road network data.

Models:
    RoadSegment     – Individual road way extracted from OSM / ohsome.
    RoadNetwork     – Aggregated network-level metrics per region and year.
    RegionBoundary  – Administrative boundary records (state / district / city / ward).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# RoadSegment
# ─────────────────────────────────────────────────────────────────────────────

class RoadSegment(Base):
    """
    Represents a single OSM road way.

    Geometry is stored as WKT text (EPSG:4326) so that the table can be
    used without a PostGIS geometry column type in environments where the
    PostGIS extension may not be available.  Spatial operations should
    re-parse the WKT into Shapely geometries via GeoPandas.

    Attributes:
        osm_id          OpenStreetMap way ID (primary key).
        osm_type        Element type, e.g. ``way`` or ``relation``.
        name            Human-readable road name (may be NULL).
        highway         OSM ``highway`` tag value (e.g. ``primary``, ``trunk``).
        surface         OSM ``surface`` tag (e.g. ``asphalt``, ``unpaved``).
        lanes           Number of traffic lanes (may be NULL).
        width_m         Measured / estimated road width in metres.
        geometry        WKT representation of the LineString geometry.
        bbox            Bounding box as ``minx,miny,maxx,maxy`` string.
        year            Survey / snapshot year.
        source          Data source label (``osm``, ``ohsome``, ``bhuvan``).
        confidence      Confidence score (0–1) for width estimates.
        length_km       Pre-computed length in kilometres.
        created_at      Row insertion timestamp.
    """

    __tablename__ = "road_segments"

    osm_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    osm_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    highway: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    surface: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lanes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geometry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bbox: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    length_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RoadSegment osm_id={self.osm_id} highway={self.highway} year={self.year}>"


# ─────────────────────────────────────────────────────────────────────────────
# RoadNetwork
# ─────────────────────────────────────────────────────────────────────────────

class RoadNetwork(Base):
    """
    Aggregated road network metrics for a region in a given year.

    Metrics are derived from NetworkX graph analysis of the OSM / ohsome
    road network snapshot.

    Attributes:
        id                  Primary key.
        region_id           FK to :class:`RegionBoundary`.
        year                Snapshot year.
        total_length_km     Sum of all road lengths in km.
        road_count          Number of road segments.
        avg_width_m         Average width across segments with width data.
        density             Road density in km per km².
        avg_degree          Mean node degree in the primal graph.
        avg_betweenness     Mean normalised betweenness centrality.
        avg_clustering      Mean local clustering coefficient.
        created_at          Row insertion timestamp.
    """

    __tablename__ = "road_networks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("region_boundaries.id", ondelete="CASCADE"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_length_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    road_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_degree: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_betweenness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_clustering: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    region: Mapped["RegionBoundary"] = relationship("RegionBoundary", back_populates="networks")

    def __repr__(self) -> str:
        return f"<RoadNetwork region_id={self.region_id} year={self.year}>"


# ─────────────────────────────────────────────────────────────────────────────
# RegionBoundary
# ─────────────────────────────────────────────────────────────────────────────

class RegionBoundary(Base):
    """
    Administrative boundary record for Indian regions.

    Levels follow the Indian administrative hierarchy:
        state → district → city → ward

    Geometry is stored as WKT (EPSG:4326) polygon.

    Attributes:
        id          Primary key.
        name        Region name (e.g. ``Pune``, ``Maharashtra``).
        level       Administrative level string: ``state``, ``district``,
                    ``city``, or ``ward``.
        parent_id   Self-referential FK to the parent region (nullable for states).
        geometry    WKT polygon of the boundary.
        area_km2    Pre-computed area in km².
        state       State name (denormalised for quick filtering).
        district    District name (denormalised, nullable).
        created_at  Row insertion timestamp.
    """

    __tablename__ = "region_boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("region_boundaries.id", ondelete="SET NULL"), nullable=True
    )
    geometry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    area_km2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    networks: Mapped[list["RoadNetwork"]] = relationship(
        "RoadNetwork", back_populates="region", cascade="all, delete-orphan"
    )
    children: Mapped[list["RegionBoundary"]] = relationship(
        "RegionBoundary", foreign_keys=[parent_id]
    )

    def __repr__(self) -> str:
        return f"<RegionBoundary name={self.name!r} level={self.level}>"
