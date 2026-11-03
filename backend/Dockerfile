# ---------------------------------------------------------------------------- #
# GeoTrack India — Backend Docker Image
# Base: python:3.11-slim
# System dependencies: GDAL, GEOS, PROJ (required by Shapely, Fiona, rasterio)
# ---------------------------------------------------------------------------- #

FROM python:3.11-slim

# Set non-interactive frontend for apt to avoid prompts during build
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install geospatial system libraries and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        libproj-dev \
        gcc \
        g++ \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Export GDAL version so Python GDAL bindings can match
RUN gdal-config --version

# Install Python dependencies (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose API port
EXPOSE 8000

# Default production command (override in docker-compose for dev --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
