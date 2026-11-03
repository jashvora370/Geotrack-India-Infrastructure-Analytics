# 🛣️ Roadies

### 10-Year Geospatial Road Infrastructure Change Detection & Analytics Platform (2016–2026)

> An academic research platform analysing how road infrastructure in India has evolved between 2016 and 2026, using OpenStreetMap historical data, satellite imagery, and geospatial analytics.

---

## Study Area

**Primary Region: Pune Metropolitan Region, Maharashtra**  
**Bounding Box:** 73.75°E, 18.35°N → 74.05°E, 18.65°N  
**Analysis Period:** 2016–2026

Pune was selected because it has:
- Among the highest OSM data density in India (verifiable via ohsome completeness metrics)
- Documented major road construction events (Ring Road, Metro corridors, flyovers) enabling ground-truth validation
- Clear urban expansion measurable via Sentinel-2 and GHSL
- Single metropolitan jurisdiction simplifying administrative data integration

---

## Architecture

```
geotrack-india/
├── frontend/        # Next.js 14 + Tailwind CSS + Recharts + Leaflet
├── backend/         # FastAPI + GeoPandas + OSMnx + NetworkX
├── data_pipeline/   # Data collection and processing scripts
├── database/        # PostgreSQL + PostGIS schema
└── docs/            # Data sources and methodology documentation
```

---

## Quick Start

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop | 4.x+ | For PostgreSQL/PostGIS |
| Python | 3.11+ | For backend & pipeline |
| Node.js | 20+ | For frontend |
| Git | Any | |

### 1. Clone and setup

```bash
git clone <repo-url>
cd geotrack-india
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials
```

### 2. Start the database

```bash
cd database
docker-compose up -d
# Wait for PostGIS to be ready (check with: docker logs geotrack_db)
```

### 3. Install and run backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API docs: http://localhost:8000/docs

### 4. Run the data pipeline

```bash
cd data_pipeline
# Install deps (same venv as backend)
python pipeline_runner.py --region "Pune" --state "Maharashtra" --level city --skip-gee
```

> **Note:** Use `--skip-gee` if you don't have Google Earth Engine credentials.  
> Without GEE, NDVI and satellite analysis will show "Data unavailable".  
> OSM historical data (ohsome API) and GHSL built-up data work without any credentials.

### 5. Install and run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

---

## Data Sources

| Source | What We Use | Authentication | URL |
|--------|------------|----------------|-----|
| **ohsome API** (HeiGIT) | Historical OSM road data 2016–2026 | None | https://api.ohsome.org/v1 |
| **OSMnx / Overpass** | Current road network, topology | None | https://overpass-api.de |
| **Landsat 8/9** (via GEE) | NDVI, land cover 2016–2026 | GEE account | https://earthengine.google.com |
| **Sentinel-2** (via GEE) | High-res imagery 2017–2026 | GEE account | https://earthengine.google.com |
| **GHSL** (JRC) | Built-up area 1975–2030 | None | https://ghsl.jrc.ec.europa.eu |
| **ESA WorldCover** | Land cover 2020/2021 | None | https://esa-worldcover.org |
| **OGD India** | Government datasets | API key | https://data.gov.in |

Full documentation: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)

---

## Credentials Setup

### Google Earth Engine (Optional but recommended)

1. Register at https://signup.earthengine.google.com
2. Wait for approval (usually 1–2 days for academic use)
3. Authenticate: `python -c "import ee; ee.Authenticate()"`
4. Or create a service account for production use

### OGD India API (Optional)

1. Register at https://data.gov.in/user/register
2. Get your API key from your profile
3. Add to `backend/.env` as `OGD_API_KEY`

---

## Data Quality & Honesty Framework

> ⚠️ **IMPORTANT**: This project prioritises analytical accuracy over visual completeness.

Every data point in this platform carries one of these confidence labels:

| Label | Meaning |
|-------|---------|
| **HIGH** | Direct measurement from authoritative source |
| **MEDIUM** | Derived from reliable data with minor assumptions |
| **LOW** | Estimated using indirect methods or limited data |
| **ESTIMATED** | Computed from a model or extrapolation — treat as indicative only |
| **UNAVAILABLE** | Data not available for this parameter/region/year |

### OSM Completeness Caveat

OpenStreetMap data reflects **mapping activity**, not physical construction. A road appearing in 2019 OSM data may have been physically built in 2014 but not yet mapped by OSM contributors until 2019.

This platform uses the **ohsome completeness API** to flag regions with known rapid mapping growth and adjusts the change detection confidence accordingly.

### Satellite Width Estimation Caveat

Road width estimation from satellite imagery is approximate due to:
- Shadow and occlusion from buildings and trees
- Spectral confusion between road surface and adjacent paving
- Georeferencing accuracy (±5m for Sentinel-2, ±15m for Landsat)

All satellite-based width estimates are labelled **LOW confidence** and the methodology is displayed alongside the data.

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/health` | Health check |
| GET | `/regions/states` | List Indian states |
| GET | `/regions/districts?state=Maharashtra` | List districts |
| GET | `/regions/boundary?name=Pune&level=city` | Region boundary GeoJSON |
| POST | `/road-network/analyze` | Trigger road network analysis |
| GET | `/road-network/stats/{region_id}` | Network stats all years |
| GET | `/road-network/changes/{region_id}` | Change detection results |
| GET | `/road-network/segments/{region_id}/{year}` | Road segments GeoJSON |
| GET | `/road-network/ohsome-timeseries/{region_id}` | Year-by-year OSM length |
| GET | `/analytics/dashboard/{region_id}` | All KPI data |
| GET | `/analytics/insights/{region_id}` | Auto-generated insights |
| POST | `/reports/pdf` | Generate PDF report |
| POST | `/reports/csv` | Generate CSV export |
| POST | `/reports/excel` | Generate Excel export |

Full interactive docs: http://localhost:8000/docs

---

## Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 0 — Data Analysis | ✅ Done | Study area selection, data source evaluation |
| 1 — Architecture | ✅ Done | Project structure, DB schema, Docker setup |
| 2 — OSM Pipeline | ✅ Done | ohsome API + OSMnx data collection |
| 3 — Change Detection | ✅ Done | Spatial matching, IOU, completeness correction |
| 4 — Satellite Analysis | ✅ Done | GEE imagery, NDVI, GHSL integration |
| 5 — Road Width | ✅ Done | OSM-attribute + satellite width estimation |
| 6 — FastAPI Backend | ✅ Done | All API endpoints |
| 7 — Next.js Frontend | ✅ Done | Full UI with maps and charts |
| 8 — Report Generation | ✅ Done | PDF, CSV, Excel exports |
| 9 — Testing | 🔄 Ongoing | Data validation, API testing |
| 10 — Documentation | 🔄 Ongoing | Dataset docs, methodology, setup guide |

---

## Methodology Summary

### Road Network Change Detection

1. Fetch historical OSM snapshots for 2016 and 2026 via ohsome API
2. Convert to GeoDataFrames, reproject to UTM Zone 43N (EPSG:32643)
3. For each 2026 road segment: search within 15m buffer for matching 2016 segment
4. Unmatched 2026 segments → **New Roads**
5. Unmatched 2016 segments → **Removed Roads** (or recently unmapped)
6. Matched pairs with width increase >1m → **Widened Roads**
7. Apply OSM completeness correction factor (from ohsome stats API)

### Road Width Estimation

Priority order:
1. `width=*` tag in OSM → HIGH confidence
2. `lanes=*` × standard lane width → MEDIUM confidence
3. Highway type default width → LOW confidence
4. Satellite imagery transect → LOW confidence (flagged separately)

### NDVI Calculation

NDVI = (NIR - RED) / (NIR + RED)

- Landsat 8: Band 5 (NIR) and Band 4 (RED)
- Sentinel-2: Band 8 (NIR) and Band 4 (RED)
- Annual cloud-free composites using median reducer
- Green fraction = percentage of pixels with NDVI > 0.3

---

## Academic Citation

If using this platform for academic work, please cite the data sources:

```
- OpenStreetMap contributors (ohsome API, HeiGIT, 2024)
- USGS/NASA Landsat 8/9 Collection 2
- ESA Sentinel-2 (Copernicus Programme)
- JRC GHSL — Global Human Settlement Layer
- ESA WorldCover 2021
```

---

## Limitations

1. **OSM completeness**: Historical OSM data may underrepresent roads that existed but were not yet mapped
2. **Satellite resolution**: Landsat (30m) and Sentinel-2 (10m) cannot detect lane-level changes
3. **Cloud cover**: Monsoon season (June–September) imagery has higher cloud masking rates
4. **Government data**: MoRTH/NHAI data availability is inconsistent and may lag physical changes
5. **Width accuracy**: Satellite-based width estimates have ±3–5m uncertainty
6. **Temporal gaps**: ohsome API provides annual snapshots; changes within a year are not captured

---

## License

This project is developed for academic research purposes.  
Data licences apply per source (see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)).

- OSM data: ODbL
- Landsat/Sentinel-2: Public domain / Copernicus DAs
- GHSL: CC BY 4.0

---

## Contact

GeoTrack India — Academic Research Project  
Developed as part of an in-house internship programme
