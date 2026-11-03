# Data Sources — GeoTrack India

> **Last updated:** 2026-10  
> **Maintainer:** GeoTrack India Project Team

This document describes every external data source used in the GeoTrack India analysis pipeline. Sources cover road network data, satellite imagery, land cover products, government statistics, and derived population datasets.

---

## Table of Contents

1. [OpenStreetMap / ohsome API](#1-openstreetmap--ohsome-api)
2. [Landsat 8 / 9 (USGS)](#2-landsat-8--9-usgs)
3. [Sentinel-2 (ESA Copernicus)](#3-sentinel-2-esa-copernicus)
4. [GHSL — Global Human Settlement Layer](#4-ghsl--global-human-settlement-layer)
5. [ESA WorldCover (10 m)](#5-esa-worldcover-10-m)
6. [ESRI Annual Land Cover (10 m)](#6-esri-annual-land-cover-10-m)
7. [OGD India — Open Government Data Platform](#7-ogd-india--open-government-data-platform)
8. [MoRTH — Ministry of Road Transport & Highways](#8-morth--ministry-of-road-transport--highways)
9. [NHAI — National Highways Authority of India](#9-nhai--national-highways-authority-of-india)
10. [ISRO Bhuvan / NRSC](#10-isro-bhuvan--nrsc)
11. [WorldPop — University of Southampton](#11-worldpop--university-of-southampton)

---

## 1. OpenStreetMap / ohsome API

| Field | Value |
|---|---|
| **Full Name** | OpenStreetMap (OSM) via ohsome History API |
| **URL** | https://www.openstreetmap.org |
| **API Endpoint** | `https://api.ohsome.org/v1` |
| **Data Date Range** | 2007-01-01 → present (continuously updated) |
| **Coverage** | Global; India fully covered |
| **Resolution** | Vector (sub-metre accuracy for contributed geometries) |
| **Units** | WGS-84 coordinates (EPSG:4326); lengths in kilometres |
| **Reliability** | ⭐⭐⭐ High (urban) / ⭐⭐ Medium (rural) |
| **Auth Required** | No (public API) |

### How It Is Used
- Primary source for all road network geometries (`road_segments` table).
- ohsome API is queried at historical snapshots (2016, 2021, 2026) to retrieve consistent temporal cuts of the OSM database.
- Road attributes extracted: `highway`, `lanes`, `width`, `maxspeed`, `surface`, `oneway`, `name`.
- Change detection is performed by spatially comparing snapshots.

### Known Limitations
- **Completeness bias:** Coverage is denser in metropolitan areas (Mumbai, Delhi, Bengaluru, Chennai) and sparser in rural Tier-3 districts.
- **Width tagging:** Fewer than 15% of Indian road ways have an explicit `width=*` tag; widths are mostly inferred from `lanes` or road class defaults.
- **Temporal lag:** OSM edits sometimes reflect ground truth with a delay of months to years in rapidly developing areas.
- **Attribute inconsistency:** `highway` tag values vary between mappers (e.g., `residential` vs. `unclassified` are often interchangeable in India).

---

## 2. Landsat 8 / 9 (USGS)

| Field | Value |
|---|---|
| **Full Name** | Landsat 8 OLI/TIRS · Landsat 9 OLI-2/TIRS-2 |
| **URL** | https://www.usgs.gov/landsat-missions |
| **API Endpoint** | `https://landsatoncloud.usgs.gov/stac/v0` |
| **Data Date Range** | Landsat 8: 2013-02-11 → present; Landsat 9: 2021-10-31 → present |
| **Coverage** | Global; full India coverage every 8–16 days |
| **Resolution** | 30 m (multispectral B1–B7, B9), 15 m (panchromatic B8), 100 m (thermal B10/B11) |
| **Units** | Surface Reflectance (Collection 2 Level-2, dimensionless 0–1 range) |
| **Reliability** | ⭐⭐⭐ High |
| **Auth Required** | No (EarthExplorer / STAC endpoint; free account for bulk download) |

### How It Is Used
- NDVI computation: `NDVI = (Band 5 NIR − Band 4 Red) / (Band 5 NIR + Band 4 Red)`.
- Built-up area detection (urban heat proxy via SWIR bands).
- Land cover change analysis for multi-decadal temporal comparisons (2013–2026).
- Used when Sentinel-2 coverage is unavailable (pre-2015) or cloud-contaminated.

### Known Limitations
- **Cloud cover:** June–September monsoon season severely limits usable scenes over India. Best dry-season mosaics used (Oct–May).
- **Resolution:** 30 m is insufficient to map individual lane widths or footpaths.
- **Saturation:** SWIR bands can saturate over bright urban surfaces.
- **Geometric accuracy:** ±12 m (1σ) — adequate for regional analysis but not sub-road level.

---

## 3. Sentinel-2 (ESA Copernicus)

| Field | Value |
|---|---|
| **Full Name** | Sentinel-2 MSI (Multispectral Instrument), ESA Copernicus Programme |
| **URL** | https://sentinel.esa.int/web/sentinel/missions/sentinel-2 |
| **API Endpoint** | `https://catalogue.dataspace.copernicus.eu/odata/v1` |
| **Data Date Range** | 2015-06-23 → present |
| **Coverage** | Global land; India revisit every 5 days (S2A + S2B combined) |
| **Resolution** | 10 m (B2 Blue, B3 Green, B4 Red, B8 NIR), 20 m (B5/B6/B7/B8A/B11/B12), 60 m (B1/B9/B10) |
| **Units** | Surface Reflectance L2A (dimensionless, scaled 0–10000 in product; normalised to 0–1 in pipeline) |
| **Reliability** | ⭐⭐⭐ High |
| **Auth Required** | No (Copernicus Data Space Ecosystem) |

### How It Is Used
- High-resolution NDVI and green fraction mapping at 10 m.
- Input to ESA WorldCover and ESRI Land Cover products.
- Direct land use classification for years 2016 onward.
- Road footprint extraction experiments (20 m resolution — experimental).

### Known Limitations
- **Cloud cover:** Same monsoon limitations as Landsat; 5-day revisit helps build cleaner composites.
- **No thermal band:** Cannot directly measure land surface temperature (use Landsat TIRS for that).
- **Pre-2015 gap:** No S2 data before June 2015; Landsat 7/8 used for earlier epochs.
- **Atmospheric correction:** Sen2Cor (L2A) can introduce artefacts in hazy/dusty conditions common over the Indo-Gangetic Plain.

---

## 4. GHSL — Global Human Settlement Layer

| Field | Value |
|---|---|
| **Full Name** | Global Human Settlement Layer — European Commission Joint Research Centre (JRC) |
| **URL** | https://ghsl.jrc.ec.europa.eu |
| **API / Download** | https://ghsl.jrc.ec.europa.eu/download.php |
| **Data Date Range** | 1975, 1990, 2000, 2015, 2020 (epochs); 2025/2030 projections available |
| **Coverage** | Global |
| **Resolution** | 10 m (GHS-BUILT-S), 100 m (GHS-POP, GHS-SMOD), 1 km (GHS-SMOD coarse) |
| **Units** | Built-up surface fraction (0–1), population count (inh), settlement classification code |
| **Reliability** | ⭐⭐⭐ High |
| **Auth Required** | No |

### How It Is Used
- Built-up area fraction (`built_up_pct`) at district and city level.
- Urban expansion quantification between epochs.
- Cross-validation for OSM road density (more roads expected in high GHS-BUILT areas).

### Known Limitations
- Built-up classification fuses roads, rooftops and paved surfaces — cannot distinguish road from building.
- 2020 epoch is most recent and most accurate; 1975 epoch has significant commission errors in India.
- Population grids are modelled — disaggregation method introduces uncertainty at sub-district scale.

---

## 5. ESA WorldCover (10 m)

| Field | Value |
|---|---|
| **Full Name** | ESA WorldCover 10 m — 2020 & 2021 editions |
| **URL** | https://esa-worldcover.org |
| **API** | https://services.terrascope.be/wms/v2 (WMS/WMTS) |
| **Data Date Range** | 2020 (v100), 2021 (v200) |
| **Coverage** | Global land |
| **Resolution** | 10 m |
| **Units** | Thematic land cover class (11 classes: Tree Cover, Shrubland, Grassland, Cropland, Built-up, Bare/Sparse Vegetation, Snow/Ice, Permanent Water, Herbaceous Wetland, Mangroves, Moss/Lichen) |
| **Reliability** | ⭐⭐⭐ High (OA ~75% globally; higher in India) |
| **Auth Required** | No |

### How It Is Used
- Baseline land cover classification for 2020 and 2021 analysis years.
- `vegetation_pct`, `agriculture_pct`, `water_pct`, `built_up_pct` fractions derived from class pixel counts within region boundary.
- Cross-validation for NDVI-based estimates.

### Known Limitations
- Only two temporal epochs (2020, 2021) — cannot track change across the full 2016–2026 window.
- Built-up class includes roads, rail and industrial surfaces.
- Mangrove and wetland classes underperform in some deltaic regions of India.

---

## 6. ESRI Annual Land Cover (10 m)

| Field | Value |
|---|---|
| **Full Name** | ESRI Annual Land Cover (Sentinel-2 derived, 10 m) |
| **URL** | https://livingatlas.arcgis.com/landcover |
| **API** | https://io.biodiversityresearch.com/api/v1/landcover |
| **Data Date Range** | 2017 → present (annual) |
| **Coverage** | Global land |
| **Resolution** | 10 m |
| **Units** | Thematic land cover class (9 classes: Water, Trees, Flooded Vegetation, Crops, Built Area, Bare Ground, Snow/Ice, Clouds, Rangeland) |
| **Reliability** | ⭐⭐⭐ High |
| **Auth Required** | No (ArcGIS Living Atlas — free account for raster access) |

### How It Is Used
- Annual time series (2017–2026) for land cover change detection.
- Primary source for `agriculture_pct`, `vegetation_pct`, `built_up_pct` over the study period.
- Enables year-on-year comparison unlike WorldCover's biennial cadence.

### Known Limitations
- Trained on Sentinel-2 — inherits monsoon cloud cover limitations.
- Some confusion between Bare Ground and Built Area in sparsely vegetated urban outskirts.
- "Crops" class in Rabi/Kharif transition periods may intermittently reclassify to Bare Ground.
- ArcGIS Living Atlas account required for large-area raster downloads.

---

## 7. OGD India — Open Government Data Platform

| Field | Value |
|---|---|
| **Full Name** | Open Government Data (OGD) India Platform |
| **URL** | https://data.gov.in |
| **API Endpoint** | `https://api.data.gov.in/resource/<resource-id>?api-key=<key>` |
| **Data Date Range** | 2012-01-01 → present (dataset-dependent) |
| **Coverage** | India — national and state-level datasets |
| **Resolution** | Tabular (state / district level); some datasets at tehsil level |
| **Units** | Varies: km (road length), count, INR (expenditure), % |
| **Reliability** | ⭐⭐ Medium |
| **Auth Required** | Yes (free API key from data.gov.in) |

### How It Is Used
- Supplementary road length statistics for cross-validation against OSM totals.
- District-level infrastructure indicators.
- Population and urbanisation statistics from Census 2011 and SECC datasets.

### Known Limitations
- Dataset completeness is uneven — many datasets stop at 2020 or earlier.
- Spatial data is mostly tabular or at coarse administrative resolution.
- No programmatic discovery of new datasets — manual catalogue browsing required.
- Some state-level data unavailable or redacted.

---

## 8. MoRTH — Ministry of Road Transport & Highways

| Field | Value |
|---|---|
| **Full Name** | Ministry of Road Transport & Highways (MoRTH) Annual Report |
| **URL** | https://morth.nic.in |
| **API Endpoint** | None (PDF reports only) |
| **Data Date Range** | 2000-01-01 → present |
| **Coverage** | India — national highway and state highway network |
| **Resolution** | Tabular (state-level and NH corridor summaries) |
| **Units** | km (road length), INR crore (expenditure), number of projects |
| **Reliability** | ⭐⭐⭐ High (for national highways) |
| **Auth Required** | No |

### How It Is Used
- Official ground-truth totals for national highway length per state per year.
- Expenditure data to correlate with road network growth observed in OSM.
- Validation of change detection results at state level.

### Known Limitations
- No open spatial API — data must be scraped or manually extracted from annual PDF reports.
- NH numbers were renumbered in 2016 (NH restructuring), breaking historical time series.
- State highway data is less reliable than NH data.
- Project-level spatial extents not publicly released.

---

## 9. NHAI — National Highways Authority of India

| Field | Value |
|---|---|
| **Full Name** | National Highways Authority of India (NHAI) |
| **URL** | https://nhai.gov.in |
| **API Endpoint** | Limited (NHAI One portal — login required) |
| **Data Date Range** | 1995-01-01 → present |
| **Coverage** | India — NHAI-managed national highway corridors |
| **Resolution** | Project-level (corridor + chainage) |
| **Units** | km, project status code, INR |
| **Reliability** | ⭐⭐⭐ High (for NHAI projects) |
| **Auth Required** | Yes (NHAI One portal institutional account) |

### How It Is Used
- Identifying NHAI corridor alignment for expressway change detection validation.
- Cross-referencing new road construction events detected in OSM change analysis.

### Known Limitations
- No open spatial data API; project boundaries available only as approximate corridors.
- Project status updates lag actual construction completion by 3–12 months.
- Data restricted to NHAI projects; does not cover state PWD roads or rural roads (PMGSY).

---

## 10. ISRO Bhuvan / NRSC

| Field | Value |
|---|---|
| **Full Name** | ISRO Bhuvan — National Remote Sensing Centre (NRSC) |
| **URL** | https://bhuvan.nrsc.gov.in |
| **API Endpoint** | `https://bhuvan-app3.nrsc.gov.in/api` (registration required) |
| **Data Date Range** | 2000-01-01 → present |
| **Coverage** | India (full national coverage with Indian satellite missions) |
| **Resolution** | 0.5–2.5 m (Cartosat-3), 2.5 m (Cartosat-1), 5 m (LISS-IV), 23.5 m (LISS-III), 56 m (AWiFS) |
| **Units** | Digital Number (DN) / Surface Reflectance / Thematic class |
| **Reliability** | ⭐⭐ Medium (public access layers) / ⭐⭐⭐ High (restricted Cartosat) |
| **Auth Required** | Yes (NRSC institutional registration) |

### How It Is Used
- High-resolution Cartosat imagery used for visual validation of detected road changes.
- Bhuvan thematic layers (LULC at 1:50,000 scale) used for cross-validation.
- AWiFS time series as supplementary vegetation index data.

### Known Limitations
- High-resolution products (Cartosat) restricted to government and approved institutional users.
- API documentation is sparse; access subject to NRSC policy changes.
- Processing pipeline uses Indian standard coordinate system (VGI2000) — reprojection to WGS-84 required.
- Temporal archive access slower than Landsat/Sentinel public cloud endpoints.

---

## 11. WorldPop — University of Southampton

| Field | Value |
|---|---|
| **Full Name** | WorldPop — Population Distribution Models, University of Southampton |
| **URL** | https://www.worldpop.org |
| **API Endpoint** | `https://hub.worldpop.org/rest/data` |
| **Data Date Range** | 2000 → 2030 (annual modelled estimates) |
| **Coverage** | Global; India at district and grid level |
| **Resolution** | 100 m / 1 km |
| **Units** | Population count per pixel |
| **Reliability** | ⭐⭐ Medium |
| **Auth Required** | No |

### How It Is Used
- Population pressure per region to contextualise road density growth.
- Per-capita road length metric: total road length (km) / population.
- Cross-validation for built-up area classification (high population → higher expected built-up fraction).

### Known Limitations
- Modelled estimates — accuracy drops in rapidly urbanising areas between census years.
- India 2011 census remains the primary calibration dataset; 2026 data is extrapolated.
- 100 m grid conflates population across mixed urban-rural fringes.
- Does not capture seasonal migrant worker population patterns common in Indian cities.

---

## Reliability Rating Key

| Rating | Meaning |
|---|---|
| ⭐⭐⭐ High | Primary authoritative source; validated against ground truth; regularly updated |
| ⭐⭐ Medium | Useful but with known systematic gaps or sparse update cadence |
| ⭐ Low | Indicative only; heavy caveats; not used as primary evidence |

---

*For methodology on how these sources are combined and uncertainty is quantified, see [METHODOLOGY.md](./METHODOLOGY.md).*
