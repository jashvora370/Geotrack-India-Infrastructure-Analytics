# 🛠️ GeoTrack India — Setup & Deployment Guide

This document describes how to set up, configure, and execute the complete GeoTrack India platform.

---

## 1. System Requirements

* **Operating System:** Windows 10/11, Ubuntu 22.04 LTS, or macOS (Apple Silicon / Intel)
* **Python:** 3.10 or 3.11 (with GDAL and GEOS native libraries)
* **Node.js:** v18 or v20 LTS
* **Database:** PostgreSQL 14+ with PostGIS 3.x extension (or Docker)
* **RAM:** Minimum 8 GB (16 GB recommended for raster buffer processing)

---

## 2. Quick Start with Docker (Recommended)

The simplest way to start the entire stack (Database, Backend, and Frontend):

```bash
cd geotrack-india

# 1. Prepare backend environment
cp backend/.env.example backend/.env

# 2. Build and launch containers
docker-compose up --build
```

Services will be accessible at:
* **Frontend Analytics Dashboard:** `http://localhost:3000`
* **FastAPI Backend & Interactive Swagger Docs:** `http://localhost:8000/docs`
* **PostgreSQL / PostGIS Database:** `localhost:5432`

---

## 3. Manual Local Setup

### Step A: Database (PostGIS)

If running PostgreSQL locally or via standalone Docker:

```bash
cd database
docker-compose up -d
```

Verify PostGIS extension:
```sql
psql -U geotrack -d geotrack_db -h localhost -c "SELECT PostGIS_Version();"
```

The database schema will automatically initialise from [database/init.sql](database/init.sql).

---

### Step B: Backend (FastAPI + GeoPandas)

```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Step C: Data Pipeline Execution

To pull historical OSM snapshots, process road cross-sections, and run change detection:

```bash
cd data_pipeline

# Run change detection for Pune Metropolitan Region (2016 -> 2026)
python pipeline_runner.py --region "Pune" --state "Maharashtra" --level city --skip-gee
```

Options:
* `--skip-gee`: Skips Google Earth Engine authentication and runs with cached Sentinel/Landsat indices.
* `--years 2016 2021 2026`: Customizes the snapshot intervals.
* `--bbox 73.75,18.35,74.05,18.65`: Overrides bounding box coordinates.

---

### Step D: Frontend (Next.js 14)

```bash
cd frontend

# Install npm packages
npm install

# Start Next.js development server
npm run dev
```

Visit `http://localhost:3000` in your browser.

---

## 4. API Authentication & Keys

| Key | Purpose | Required? | How to Obtain |
|-----|---------|-----------|---------------|
| `GEE_SERVICE_ACCOUNT` | Google Earth Engine Python SDK | Optional | [earthengine.google.com](https://earthengine.google.com) |
| `OGD_API_KEY` | data.gov.in Government portal | Optional | [data.gov.in](https://data.gov.in/user/register) |
| `BHUVAN_TOKEN` | ISRO Bhuvan WMS | Optional | [bhuvan.nrsc.gov.in](https://bhuvan.nrsc.gov.in) |
| `ohsome API` | OSM Historical element queries | **No Auth Needed** | Public HeiGIT endpoint |

---

## 5. Verification Checklist

* [x] **Backend API:** `GET http://localhost:8000/health` returns status: healthy.
* [x] **Regions Endpoint:** `GET http://localhost:8000/api/v1/regions/states` lists Indian states.
* [x] **Change Detection:** `GET http://localhost:8000/api/v1/road-network/changes/1001` returns 10-year metrics.
* [x] **Report Generation:** `GET http://localhost:8000/api/v1/reports/pdf/1001` generates downloadable PDF.
* [x] **GIS Map:** Interactive Leaflet viewer renders polylines and allows classification toggling.
