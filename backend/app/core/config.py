# app/core/config.py
"""
Application configuration using Pydantic Settings.
Reads all environment variables from .env file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration class for GeoTrack India.

    All values are read from environment variables or the .env file.
    Defaults are provided for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = (
        "postgresql+asyncpg://geotrack:geotrack@localhost:5432/geotrack_db"
    )
    SYNC_DATABASE_URL: str = (
        "postgresql://geotrack:geotrack@localhost:5432/geotrack_db"
    )

    # ------------------------------------------------------------------ #
    # Google Earth Engine
    # ------------------------------------------------------------------ #
    GEE_SERVICE_ACCOUNT: Optional[str] = None
    GEE_KEY_FILE: Optional[str] = None

    # ------------------------------------------------------------------ #
    # External API keys
    # ------------------------------------------------------------------ #
    OGD_API_KEY: Optional[str] = None
    BHUVAN_TOKEN: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Application settings
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Roadies"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS_ORIGINS can be a JSON-encoded list or a comma-separated string.
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> List[str]:
        """Allow CORS_ORIGINS to be provided as a JSON array string."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    CACHE_TTL_SECONDS: int = 3600

    # ------------------------------------------------------------------ #
    # File system paths
    # ------------------------------------------------------------------ #
    DATA_DIR: Path = Path("./data")
    CACHE_DIR: Path = Path("./cache")

    @field_validator("DATA_DIR", "CACHE_DIR", mode="before")
    @classmethod
    def make_path(cls, v: object) -> Path:
        """Convert string paths to Path objects and create them if missing."""
        p = Path(str(v))
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------ #
    # Derived / computed helpers
    # ------------------------------------------------------------------ #
    @property
    def is_production(self) -> bool:
        """Return True when DEBUG is False."""
        return not self.DEBUG


# Singleton instance – import this everywhere.
settings = Settings()
