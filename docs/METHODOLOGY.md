# Methodology — GeoTrack India

> **Version:** 1.0  
> **Last updated:** 2026-10  
> **Maintainer:** GeoTrack India Project Team

This document describes the analytical methodology used in the GeoTrack India geospatial analysis pipeline. It covers road network change detection, road width estimation, vegetation/NDVI analysis, land cover classification, statistical methods, limitations, and the data quality framework.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Road Network Change Detection](#2-road-network-change-detection)
3. [Road Width Estimation](#3-road-width-estimation)
4. [NDVI Computation and Interpretation](#4-ndvi-computation-and-interpretation)
5. [Land Cover Classification](#5-land-cover-classification)
6. [Statistical Analysis Methods](#6-statistical-analysis-methods)
7. [Limitations and Uncertainty Quantification](#7-limitations-and-uncertainty-quantification)
8. [Data Quality Framework](#8-data-quality-framework)

---

## 1. Overview

GeoTrack India analyses decadal changes in the road network, land cover, and built-up area across Indian cities, districts, and states using openly available geospatial datasets. The primary analysis window is **2016–2026** with an intermediate snapshot at **2021**, corresponding to three consistent OSM historical extracts.

All spatial operations use **EPSG:4326** (WGS-84) for storage and **EPSG:32643–32646** (UTM Zone 43–46N) for metric operations such as length, area, and buffer calculations, depending on the region longitude.

The pipeline is structured in three layers:

| Layer | Responsibility |
|---|---|
| **Ingestion** | Fetch raw OSM, satellite, and government data; store in `road_segments`, `land_use_analysis` |
| **Analysis** | Compute change detection, network stats, width distribution; write results to summary tables |
| **API / Cache** | Expose computed results via FastAPI; cache expensive queries in `analysis_cache` |

---

## 2. Road Network Change Detection

### 2.1 Data Acquisition — ohsome API Snapshots

For each study region and each target year (2016, 2021, 2026), the OSM historical state is retrieved using the **ohsome API**:

```
POST https://api.ohsome.org/v1/elements/geometry
body: {
  "bboxes": "<region_bbox>",
  "filter": "type:way and highway:*",
  "time": "<YYYY>-01-01"
}
```

All returned ways are clipped to the region boundary (`ST_Intersection` with `regions.geom`) and stored as individual `road_segments` rows.

### 2.2 Buffer-Based Spatial Matching

New and removed roads are identified by a **15-metre bidirectional buffer proximity test**:

**New roads** (in `year_to`, absent in `year_from`):

```sql
-- Road r2 (year_to) is NEW if no road from year_from is within 15m
SELECT r2.*
FROM road_segments r2
WHERE r2.year = year_to
AND NOT EXISTS (
    SELECT 1 FROM road_segments r1
    WHERE r1.year = year_from
    AND ST_DWithin(r2.geom::geography, r1.geom::geography, 15)
);
```

**Removed roads** (in `year_from`, absent in `year_to`): same logic inverted.

The 15 m threshold was chosen based on:
- OSM positional accuracy (typically ±5–12 m for GPS-traced roads).
- Median road lane width (~3.5 m) — ensures a road displaced by one lane width still matches.
- Empirical calibration against manually labelled road pairs in pilot regions.

### 2.3 Intersection over Union (IoU) for Widening Detection

Road segments that **exist in both snapshots** but have been widened are identified by comparing attribute-based width estimates:

```
widening = road present in BOTH year_from and year_to
           AND width_m(year_to) > width_m(year_from) + 1.5m
```

Because OSM width tagging is sparse, a **confidence-weighted comparison** is used:

| Confidence Pair | Method |
|---|---|
| HIGH–HIGH | Direct `width_m` tag comparison |
| HIGH–MEDIUM or MEDIUM–MEDIUM | Lane-derived width comparison |
| LOW–LOW or any ESTIMATED | Road class default comparison; flagged in `data_quality_notes` |

Geometric IoU is computed experimentally using buffered linestring overlap:

$$
IoU = \frac{\text{Area}(B(r_1, w_1/2) \cap B(r_2, w_2/2))}{\text{Area}(B(r_1, w_1/2) \cup B(r_2, w_2/2))}
$$

where $B(r, d)$ is the Shapely buffer of road geometry $r$ at half-width $d$. IoU < 0.3 flags potential misclassification.

### 2.4 OSM Completeness Caveats

OSM is a **volunteered geographic information** dataset. Apparent road growth between snapshots may reflect:

1. **Genuine new construction** — the primary signal of interest.
2. **OSM mapping backlog clearance** — existing roads digitised by contributors during the study period.
3. **Tag/geometry correction** — re-routed or refined geometries replacing approximate traces.

To partially control for (2) and (3), the analysis:
- Cross-validates growth rates with **MoRTH annual report totals** at state level.
- Applies an **OSM completeness adjustment factor** (ratio of OSM total to MoRTH total per state) when the ratio deviates > 20%.
- Flags regions with `network_completeness_note` where OSM length is implausibly low (< 0.1 km/km²) for the road class mix.

### 2.5 Growth Metrics

| Metric | Formula |
|---|---|
| % Growth | `(total_km_year_to − total_km_year_from) / total_km_year_from × 100` |
| Net addition | `total_km_year_to − total_km_year_from` (km) |
| Absolute new | `new_roads_km` (roads in year_to with no match within 15m in year_from) |
| Absolute removed | `removed_roads_km` (roads in year_from with no match within 15m in year_to) |

---

## 3. Road Width Estimation

Because fewer than 15% of Indian OSM roads carry an explicit `width=*` tag, a **three-tier hierarchical width estimation** strategy is employed:

### Tier 1 — OSM Tagged Width (Confidence: HIGH)

If the OSM way has a `width` tag (e.g., `width=7.5`), this value is used directly.

- Stored as `width_confidence = 'HIGH'`
- Sanity check: values < 1 m or > 100 m are rejected and downgraded to Tier 2.

### Tier 2 — Lane-Derived Width (Confidence: MEDIUM)

If a `lanes` tag exists (e.g., `lanes=2`), width is estimated as:

$$
w = n_{lanes} \times w_{lane} + w_{shoulder}
$$

Default lane widths used (based on IRC:SP:84 and IRC:73 standards):

| Road Type | Lane Width | Shoulder |
|---|---|---|
| National/State Highway | 3.75 m | 2.5 m each side |
| Urban arterial | 3.5 m | 1.0 m each side |
| Urban local / residential | 3.0 m | 0.5 m each side |

- Stored as `width_confidence = 'MEDIUM'`

### Tier 3 — Road Class Default Width (Confidence: LOW / ESTIMATED)

If neither `width` nor `lanes` is tagged, a default width is assigned based on the `highway` tag value:

| OSM `highway` value | Default width (m) | Confidence |
|---|---|---|
| `motorway` | 30.0 | LOW |
| `trunk` | 21.0 | LOW |
| `primary` | 14.0 | LOW |
| `secondary` | 10.5 | LOW |
| `tertiary` | 7.0 | LOW |
| `residential` | 5.5 | ESTIMATED |
| `unclassified` | 5.0 | ESTIMATED |
| `service` | 4.0 | ESTIMATED |
| `track` / `path` | 3.0 | ESTIMATED |

Values are derived from IRC standards and cross-validated against Sentinel-2 road width measurements in 50 pilot segments.

### Satellite-Based Width Measurement (Experimental)

For primary and trunk roads, a **satellite-based width measurement** is performed as validation:

1. Buffer the road centreline by a search radius (30 m).
2. Extract Sentinel-2 10 m pixels in the buffer.
3. Apply spectral indices (NDBI, NBI) to isolate impervious surface pixels.
4. Measure cross-sectional road width by counting consecutive paved pixels perpendicular to the road bearing.

This method has a ±10 m uncertainty at 10 m resolution and is **not used as the primary width** — it serves as a cross-validation flag only.

---

## 4. NDVI Computation and Interpretation

### 4.1 Formula

$$
NDVI = \frac{NIR - Red}{NIR + Red}
$$

- **Landsat 8/9:** Band 5 (NIR, 0.85 µm), Band 4 (Red, 0.65 µm)
- **Sentinel-2:** Band 8 (NIR, 0.84 µm) or Band 8A (0.865 µm) and Band 4 (Red, 0.665 µm)

### 4.2 Preprocessing

1. Cloud masking using the **QA_PIXEL** band (Landsat) or **SCL** scene classification layer (Sentinel-2). Pixels with cloud, cloud shadow, or snow flags are excluded.
2. Temporal compositing: **median composite** across all valid pixels within the dry season (November–May) for each target year.
3. Output clipped to region boundary (`ST_Intersection`).

### 4.3 Interpretation Scale

| NDVI Range | Interpretation |
|---|---|
| < 0.0 | Water, impervious surfaces, bare rock |
| 0.0 – 0.15 | Bare soil, sparsely vegetated, roads/buildings |
| 0.15 – 0.30 | Degraded grassland, shrub, agricultural fallow |
| 0.30 – 0.50 | Moderate vegetation, agriculture (Rabi season), open forest |
| 0.50 – 0.70 | Dense vegetation, active crops, secondary forest |
| > 0.70 | Dense tropical forest, wet cropland |

### 4.4 `green_fraction` Metric

$$
\text{green\_fraction} = \text{vegetation\_pct} + \text{agriculture\_pct}
$$

Used as a proxy for urban greenness. Declining `green_fraction` alongside rising `built_up_pct` indicates urban encroachment on vegetation.

---

## 5. Land Cover Classification

### 5.1 Primary Product

The **ESRI Annual Land Cover (10 m)** product is used as the primary land cover source for 2017–2026. For 2016, the **ESA WorldCover 2020** product is backdated using Landsat 8 NDVI trajectories to estimate the 2016 state.

### 5.2 Class Harmonisation

Both products use different class schemes. The following crosswalk is applied:

| GeoTrack Class | ESRI Class | ESA WorldCover Class |
|---|---|---|
| `built_up_pct` | Built Area | Built-up (50) |
| `vegetation_pct` | Trees + Rangeland | Tree cover (10) + Shrubland (20) + Grassland (30) |
| `agriculture_pct` | Crops | Cropland (40) |
| `water_pct` | Water | Permanent Water (80) |
| `bare_land_pct` | Bare Ground | Bare/Sparse Vegetation (60) |

### 5.3 Pixel Counting

For each region boundary:

1. Rasterise the boundary to a binary mask aligned to the 10 m product grid.
2. Count pixels per class within the mask.
3. Compute percentage: `class_pct = class_pixel_count / total_valid_pixels × 100`.
4. Exclude cloud/no-data pixels from the denominator.

### 5.4 Missing Data Handling

If cloud coverage within the region exceeds **30%** for the target year, the result is flagged as `is_estimated = TRUE` and `estimation_note` records:

- The actual cloud coverage percentage.
- Whether adjacent-year compositing was used.
- Whether a Landsat-based proxy was substituted.

---

## 6. Statistical Analysis Methods

### 6.1 Road Density

$$
\rho_{road} = \frac{\sum_{i} l_i}{A_{region}} \quad [\text{km/km}^2]
$$

where $l_i$ is the length of road segment $i$ and $A_{region}$ is the planar area of the region polygon.

Computed by the PostgreSQL function `calculate_road_density(region_id, year)`.

### 6.2 Network Topology Metrics

Computed using **OSMnx** (Python) and stored in `road_network_stats`:

| Metric | Description |
|---|---|
| `node_count` | Count of graph nodes (OSM intersections + dead ends) |
| `edge_count` | Count of directed graph edges |
| `avg_degree` | Mean node degree (edges per node) |
| `avg_betweenness` | Mean betweenness centrality (normalised) |
| `avg_clustering` | Mean clustering coefficient |
| `intersection_density` | Nodes of degree ≥ 3 per km² |

Graph is **directed** for one-way roads and **undirected** otherwise. Only `highway` ∈ {motorway, trunk, primary, secondary, tertiary, residential, unclassified, service, living_street} are included; paths, tracks, and footways are excluded.

### 6.3 Change Rate Normalisation

To compare growth across regions of different sizes:

$$
\text{growth\_rate\_normalised} = \frac{\Delta \rho}{\rho_{2016}} = \frac{\rho_{2026} - \rho_{2016}}{\rho_{2016}}
$$

This normalises for baseline road density rather than reporting absolute km additions.

### 6.4 Confidence Intervals

Where sample sizes allow, **95% bootstrap confidence intervals** (n=1000 resamples) are computed for:
- Mean road width per region/year.
- Mean NDVI per region/year (pixel sample).
- Proportion of new roads by highway class.

Bootstrapped CI bounds are stored in the `data` JSONB field of `analysis_cache`.

---

## 7. Limitations and Uncertainty Quantification

### 7.1 OSM Completeness Uncertainty

The largest source of systematic error is uneven OSM contributor density. Observed road growth may be an artefact of retrospective digitisation.

**Mitigation:**
- Cross-validate with MoRTH state-level totals.
- Apply completeness adjustment factor where OSM total < 70% of MoRTH total.
- Report raw and adjusted growth figures separately.
- Flag results with `data_quality_notes` when adjustment > 15%.

### 7.2 Width Estimation Uncertainty

| Confidence Level | Estimated Width Error |
|---|---|
| HIGH (OSM tagged) | ±0.5 m |
| MEDIUM (lane-derived) | ±1.5–2.5 m |
| LOW (class default) | ±3.0–5.0 m |
| ESTIMATED | ±5.0–8.0 m |

The mean width at region level will carry a weighted uncertainty based on the proportion of each confidence class in the road network.

### 7.3 Temporal Alignment Uncertainty

OSM snapshots are taken at `YYYY-01-01`. A road completed in October 2025 but not mapped until February 2026 will appear in the 2027 snapshot, not 2026. This creates a typical **3–12 month lag** between physical construction and OSM detection.

### 7.4 Satellite Cloud Contamination

For regions with persistent cloud cover (Kerala coast, Assam, Meghalaya), NDVI and land cover estimates for any given year may be based on a limited number of valid scenes. Monsoon-season composites are avoided; dry-season composites preferred.

### 7.5 Projection and Area Errors

All area calculations use the **UTM projection** appropriate for each region's longitude. Using geographic coordinates (degrees) for area would introduce errors of up to 5% at India's latitudes. The `area_km2` field in `regions` must be pre-computed in the appropriate UTM CRS.

---

## 8. Data Quality Framework

### 8.1 Quality Tiers

Each row of analytical output carries an implicit quality tier based on input data confidence:

| Tier | Criteria | Action |
|---|---|---|
| **GOLD** | OSM completeness ≥ 80%, width confidence ≥ MEDIUM, cloud cover < 10% | Report as primary result |
| **SILVER** | OSM completeness 50–80%, some LOW width confidence, cloud cover 10–30% | Report with caveats |
| **BRONZE** | OSM completeness < 50%, mostly ESTIMATED widths, cloud cover > 30% | Report as indicative only; `is_estimated = TRUE` |

### 8.2 Quality Flags Applied

| Flag | Field | Trigger |
|---|---|---|
| `LOW_OSM_COMPLETENESS` | `network_completeness_note` | OSM/MoRTH ratio < 0.7 |
| `HIGH_CLOUD_COVERAGE` | `estimation_note` | Cloud > 30% for satellite products |
| `WIDTH_ESTIMATED` | `width_confidence = 'ESTIMATED'` | No OSM width or lanes tag |
| `SMALL_SAMPLE` | `data_quality_notes` | Road count < 50 for width stats |
| `TEMPORAL_LAG` | `data_quality_notes` | Region known for OSM mapping backlog |

### 8.3 Cache Invalidation

Entries in `analysis_cache` are invalidated when:
- New `road_segments` rows are ingested for the cached `region_id` and `year`.
- Methodology parameters change (buffer threshold, width defaults).
- The cache entry's `expires_at` timestamp is past.

Cache keys follow the convention: `{region_id}:{analysis_type}:{year_from}:{year_to}:{params_hash}`.

### 8.4 Audit Trail

All analysis runs append to `change_detection_results.analysis_timestamp` and `road_network_stats.created_at`. Old rows are retained — the most recent row per `(region_id, year_from, year_to)` is treated as current. Historical runs allow reproducibility checks.

---

*For data source details, see [DATA_SOURCES.md](./DATA_SOURCES.md).*
