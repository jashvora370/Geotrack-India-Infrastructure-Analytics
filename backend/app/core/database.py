# app/core/database.py
"""
Database engine setup for GeoTrack India.

Provides:
- Async SQLAlchemy engine (asyncpg) for FastAPI endpoints.
- Sync SQLAlchemy engine (psycopg2) for GeoPandas / pandas operations
  that require synchronous DB access (e.g., read_postgis / to_postgis).
- PostGIS-aware session factories.
- Dependency-injection helper `get_db()` for FastAPI routes.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import create_engine

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Declarative base – shared by all ORM models
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Async engine (asyncpg) — used by FastAPI endpoints
# ─────────────────────────────────────────────────────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sync engine (psycopg2) — used by GeoPandas read_postgis / to_postgis
# ─────────────────────────────────────────────────────────────────────────────

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# PostGIS bootstrap
# ─────────────────────────────────────────────────────────────────────────────

async def ensure_postgis_extension() -> None:
    """
    Run ``CREATE EXTENSION IF NOT EXISTS postgis`` on first connection.

    Called from the FastAPI startup event so that the PostGIS extension is
    always available before any model tables are created.
    """
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology"))
        logger.info("PostGIS extensions verified/created.")


# ─────────────────────────────────────────────────────────────────────────────
# Table creation helper
# ─────────────────────────────────────────────────────────────────────────────

async def create_tables() -> None:
    """
    Create all ORM-mapped tables that do not yet exist.

    Imports the model modules here to register them with ``Base.metadata``
    before calling ``create_all``.
    """
    # Ensure models are imported so their metadata is registered.
    import app.models.road_segment  # noqa: F401
    import app.models.analysis_result  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

async def check_db_connection() -> bool:
    """
    Execute a trivial query to verify the database is reachable.

    Returns:
        True if the connection succeeds, False otherwise.
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK.")
        return True
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions outside of FastAPI routes.

    Usage::

        async with get_db_context() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
