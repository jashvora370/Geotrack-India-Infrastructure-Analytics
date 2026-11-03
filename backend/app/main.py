"""
GeoTrack India — FastAPI Main Application
==========================================
Main application entry point configuring routers, CORS middleware,
lifespan startup/shutdown, and API health checks.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes.regions import router as regions_router
from app.api.routes.road_network import router as road_network_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.reports import router as reports_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("geotrack")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: database checks and cache preparation."""
    logger.info("Starting up GeoTrack India API (%s)...", settings.APP_VERSION)
    # Attempt DB connectivity test (non-blocking if DB not yet started)
    try:
        from app.core.database import check_db_connection
        db_ok = await check_db_connection()
        if db_ok:
            logger.info("Connected to PostgreSQL / PostGIS database.")
        else:
            logger.warning("PostgreSQL not immediately available. Running with file/cache fallbacks.")
    except Exception as exc:
        logger.warning("DB check exception: %s. Continuing in standalone/offline mode.", exc)

    yield

    logger.info("Shutting down Roadies API...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "10-Year Geospatial Road Infrastructure Change Detection & Analytics Platform (2016–2026)\n\n"
        "Integrates OpenStreetMap history (ohsome API), OSMnx, Sentinel-2, Landsat 8/9, "
        "and JRC Global Human Settlement Layer for authentic Indian road infrastructure analysis."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS:
    for o in settings.CORS_ORIGINS:
        if o not in origins:
            origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time-Sec header to measure response latency."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response


# Register Routers with /api/v1 prefix
app.include_router(regions_router, prefix="/api/v1")
app.include_router(road_network_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")

# Also register without prefix so any client calls to /regions etc work directly
app.include_router(regions_router)
app.include_router(road_network_router)
app.include_router(analytics_router)
app.include_router(reports_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check and version verification."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "study_area": "Pune Metropolitan Region, Maharashtra",
        "reference_period": "2016–2026",
        "timestamp": time.time(),
    }


@app.get("/", tags=["Root"])
async def root():
    """Welcome and quick documentation link."""
    return {
        "message": "Welcome to Roadies API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.APP_VERSION,
    }
