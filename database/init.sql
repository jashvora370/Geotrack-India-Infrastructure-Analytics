-- =============================================================================
-- GeoTrack India Database Schema
-- Requires PostgreSQL 14+ with PostGIS 3.x extension
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy text search on names

-- =============================================================================
-- TABLE: regions
-- Hierarchical spatial units (state → district → city → ward → custom)
-- =============================================================================
CREATE TABLE IF NOT EXISTS regions (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    level         TEXT CHECK (level IN ('state', 'district', 'city', 'ward', 'custom')),
    parent_id     INT REFERENCES regions(id) ON DELETE SET NULL,
    state         TEXT,
    district      TEXT,
    area_km2      FLOAT,
    geom          GEOMETRY(MULTIPOLYGON, 4326),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE regions IS 'Hierarchical administrative / custom spatial units covering India. Geometry stored as MULTIPOLYGON WGS-84.';
COMMENT ON COLUMN regions.level IS 'Granularity level: state > district > city > ward > custom';
COMMENT ON COLUMN regions.parent_id IS 'Self-referencing FK for the region hierarchy tree';
COMMENT ON COLUMN regions.area_km2 IS 'Pre-computed planar area in km² (use for density calculations)';
COMMENT ON COLUMN regions.geom IS 'Boundary stored as MULTIPOLYGON in EPSG:4326';

-- =============================================================================
-- TABLE: road_segments
-- Individual road geometries fetched from OSM / ohsome API per year
-- =============================================================================
CREATE TABLE IF NOT EXISTS road_segments (
    id                    BIGSERIAL PRIMARY KEY,
    osm_id                BIGINT,
    osm_type              TEXT,                       -- 'way' | 'relation'
    region_id             INT REFERENCES regions(id) ON DELETE CASCADE,
    name                  TEXT,
    highway               TEXT,                       -- OSM highway tag value
    surface               TEXT,                       -- OSM surface tag
    lanes                 INT,
    width_m               FLOAT,
    width_confidence      TEXT CHECK (width_confidence IN ('HIGH', 'MEDIUM', 'LOW', 'ESTIMATED')),
    road_classification   TEXT,                       -- e.g. 'primary', 'urban_local', 'NH'
    length_km             FLOAT NOT NULL,
    maxspeed              INT,
    oneway                BOOLEAN DEFAULT FALSE,
    geom                  GEOMETRY(LINESTRING, 4326) NOT NULL,
    year                  INT NOT NULL,
    source                TEXT DEFAULT 'OSM',
    data_quality_note     TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE road_segments IS 'Individual road linestrings per region and year, sourced from OSM (via ohsome API or Overpass). One row per OSM way per year snapshot.';
COMMENT ON COLUMN road_segments.osm_id IS 'Original OSM way/relation ID for provenance tracking';
COMMENT ON COLUMN road_segments.width_m IS 'Estimated or tagged road width in metres';
COMMENT ON COLUMN road_segments.width_confidence IS 'Confidence of width estimate: HIGH=tagged, MEDIUM=lane-derived, LOW=class-derived, ESTIMATED=default';
COMMENT ON COLUMN road_segments.length_km IS 'Geodesic length of the segment in kilometres';
COMMENT ON COLUMN road_segments.year IS 'Snapshot year (e.g. 2016, 2021, 2026)';

-- =============================================================================
-- TABLE: road_network_stats
-- Aggregated network-level statistics per region per year
-- =============================================================================
CREATE TABLE IF NOT EXISTS road_network_stats (
    id                          SERIAL PRIMARY KEY,
    region_id                   INT REFERENCES regions(id) ON DELETE CASCADE,
    year                        INT NOT NULL,
    total_length_km             FLOAT,
    road_count                  INT,
    avg_width_m                 FLOAT,
    road_density_km_per_km2     FLOAT,
    node_count                  INT,
    edge_count                  INT,
    avg_degree                  FLOAT,
    avg_betweenness             FLOAT,
    avg_clustering              FLOAT,
    intersection_density        FLOAT,               -- intersections / km²
    network_completeness_note   TEXT,
    data_source                 TEXT DEFAULT 'OSM+ohsome',
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (region_id, year)
);

COMMENT ON TABLE road_network_stats IS 'Pre-aggregated network topology metrics per region per year. UNIQUE constraint prevents duplicate snapshots.';
COMMENT ON COLUMN road_network_stats.avg_betweenness IS 'Mean betweenness centrality (networkx) — proxy for traffic bottleneck severity';
COMMENT ON COLUMN road_network_stats.avg_clustering IS 'Mean clustering coefficient — measure of local network redundancy';
COMMENT ON COLUMN road_network_stats.intersection_density IS 'Count of road intersections per km²';
COMMENT ON COLUMN road_network_stats.network_completeness_note IS 'Free-text note on known OSM completeness gaps for this region/year';

-- =============================================================================
-- TABLE: change_detection_results
-- Pairwise temporal change metrics between two year snapshots
-- =============================================================================
CREATE TABLE IF NOT EXISTS change_detection_results (
    id                  SERIAL PRIMARY KEY,
    region_id           INT REFERENCES regions(id) ON DELETE CASCADE,
    year_from           INT NOT NULL,
    year_to             INT NOT NULL,
    total_km_year_from  FLOAT,
    total_km_year_to    FLOAT,
    pct_growth          FLOAT,                       -- (year_to - year_from) / year_from * 100
    new_roads_km        FLOAT,
    new_roads_count     INT,
    removed_roads_km    FLOAT,
    removed_roads_count INT,
    widened_km          FLOAT,
    widened_count       INT,
    unchanged_km        FLOAT,
    methodology         TEXT,                        -- e.g. 'buffer_15m_spatial_match'
    data_quality_notes  TEXT,
    analysis_timestamp  TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE change_detection_results IS 'Pairwise change detection results between two OSM snapshots. Captures new, removed, widened and unchanged road segments.';
COMMENT ON COLUMN change_detection_results.pct_growth IS '% growth = (total_km_year_to - total_km_year_from) / total_km_year_from * 100';
COMMENT ON COLUMN change_detection_results.methodology IS 'Short key describing the spatial matching method used (see docs/METHODOLOGY.md)';

-- =============================================================================
-- TABLE: land_use_analysis
-- Satellite-derived land cover / NDVI metrics per region per year
-- =============================================================================
CREATE TABLE IF NOT EXISTS land_use_analysis (
    id                    SERIAL PRIMARY KEY,
    region_id             INT REFERENCES regions(id) ON DELETE CASCADE,
    year                  INT NOT NULL,
    built_up_pct          FLOAT,
    vegetation_pct        FLOAT,
    agriculture_pct       FLOAT,
    water_pct             FLOAT,
    bare_land_pct         FLOAT,
    ndvi_mean             FLOAT,
    ndvi_min              FLOAT,
    ndvi_max              FLOAT,
    ndvi_std              FLOAT,
    green_fraction        FLOAT,                    -- vegetation_pct + agriculture_pct
    data_source           TEXT,
    satellite             TEXT,                     -- e.g. 'Landsat8', 'Sentinel2'
    resolution_m          INT,                      -- pixel resolution in metres
    cloud_coverage_pct    FLOAT,
    is_estimated          BOOLEAN DEFAULT FALSE,
    estimation_note       TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE land_use_analysis IS 'Land cover class fractions and NDVI statistics derived from satellite imagery (Landsat/Sentinel-2/ESA WorldCover).';
COMMENT ON COLUMN land_use_analysis.ndvi_mean IS 'Mean NDVI over region boundary; range [-1, 1]';
COMMENT ON COLUMN land_use_analysis.green_fraction IS 'Combined vegetation + agriculture fraction; proxy for urban greenness';
COMMENT ON COLUMN land_use_analysis.is_estimated IS 'TRUE if values were interpolated / gap-filled due to cloud cover or missing data';

-- =============================================================================
-- TABLE: road_width_analysis
-- Statistical distribution of road widths per region per year
-- =============================================================================
CREATE TABLE IF NOT EXISTS road_width_analysis (
    id              SERIAL PRIMARY KEY,
    region_id       INT REFERENCES regions(id) ON DELETE CASCADE,
    year            INT NOT NULL,
    avg_width_m     FLOAT,
    median_width_m  FLOAT,
    max_width_m     FLOAT,
    min_width_m     FLOAT,
    pct_narrow      FLOAT,      -- < 4 m (single-lane / lane-less)
    pct_medium      FLOAT,      -- 4–7 m (two-lane)
    pct_wide        FLOAT,      -- 7–12 m (multi-lane)
    pct_arterial    FLOAT,      -- 12–20 m (arterial)
    pct_highway     FLOAT,      -- > 20 m (expressway / NH)
    methodology     TEXT NOT NULL,
    confidence      TEXT NOT NULL,
    data_notes      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE road_width_analysis IS 'Aggregated road width distribution statistics per region per year.';
COMMENT ON COLUMN road_width_analysis.pct_narrow IS 'Fraction of road length with width < 4 m';
COMMENT ON COLUMN road_width_analysis.pct_highway IS 'Fraction of road length with width > 20 m';
COMMENT ON COLUMN road_width_analysis.methodology IS 'Width derivation method: OSM_TAGGED | LANE_DERIVED | CLASS_DEFAULT | SATELLITE_MEASURED';
COMMENT ON COLUMN road_width_analysis.confidence IS 'Aggregate confidence: HIGH | MEDIUM | LOW';

-- =============================================================================
-- TABLE: data_sources
-- Registry of all external data sources used by the pipeline
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_sources (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    source_type     TEXT,           -- 'OSM' | 'satellite' | 'government' | 'derived'
    url             TEXT,
    api_endpoint    TEXT,
    data_date_from  DATE,
    data_date_to    DATE,
    coverage        TEXT,
    resolution      TEXT,
    units           TEXT,
    reliability     TEXT,           -- 'High' | 'Medium' | 'Low'
    limitations     TEXT,
    auth_required   BOOLEAN,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE data_sources IS 'Registry of all external data sources used across the GeoTrack India pipeline.';

-- =============================================================================
-- TABLE: analysis_cache
-- Key-value JSON cache for expensive computation results
-- =============================================================================
CREATE TABLE IF NOT EXISTS analysis_cache (
    id          SERIAL PRIMARY KEY,
    cache_key   TEXT UNIQUE NOT NULL,
    data        JSONB NOT NULL,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE analysis_cache IS 'Key-value cache for expensive geospatial analysis results. Entries expire at expires_at; NULL means no expiry.';
COMMENT ON COLUMN analysis_cache.cache_key IS 'Deterministic key — typically region_id:analysis_type:year or similar';
COMMENT ON COLUMN analysis_cache.data IS 'Serialised JSON result blob';

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Spatial indexes
CREATE INDEX idx_road_segments_geom    ON road_segments USING GIST (geom);
CREATE INDEX idx_regions_geom          ON regions       USING GIST (geom);

-- B-tree indexes for common query patterns
CREATE INDEX idx_road_segments_region_year ON road_segments (region_id, year);
CREATE INDEX idx_road_segments_highway     ON road_segments (highway);
CREATE INDEX idx_road_segments_osm_id      ON road_segments (osm_id);
CREATE INDEX idx_regions_level             ON regions (level);
CREATE INDEX idx_regions_parent_id         ON regions (parent_id);
CREATE INDEX idx_land_use_region_year      ON land_use_analysis (region_id, year);
CREATE INDEX idx_rna_region_year           ON road_network_stats (region_id, year);
CREATE INDEX idx_change_region_years       ON change_detection_results (region_id, year_from, year_to);
CREATE INDEX idx_cache_expires             ON analysis_cache (expires_at);

-- GIN index for JSONB cache queries
CREATE INDEX idx_cache_data ON analysis_cache USING GIN (data);

-- =============================================================================
-- POSTGIS FUNCTIONS
-- =============================================================================

-- Function: calculate_road_density
-- Returns total road km per km² for a region/year pair
CREATE OR REPLACE FUNCTION calculate_road_density(p_region_id INT, p_year INT)
RETURNS FLOAT AS $$
DECLARE
    total_length FLOAT;
    area         FLOAT;
BEGIN
    SELECT SUM(rs.length_km), r.area_km2
    INTO total_length, area
    FROM road_segments rs
    JOIN regions r ON r.id = rs.region_id
    WHERE rs.region_id = p_region_id
      AND rs.year       = p_year
    GROUP BY r.area_km2;

    IF area IS NOT NULL AND area > 0 THEN
        RETURN COALESCE(total_length, 0) / area;
    ELSE
        RETURN 0;
    END IF;
END;
$$ LANGUAGE plpgsql
   STABLE
   PARALLEL SAFE;

COMMENT ON FUNCTION calculate_road_density(INT, INT) IS
  'Returns road density (km road / km² area) for a given region and year. Returns 0 when area is NULL or 0.';

-- Function: find_new_roads
-- Returns roads present in year_to but not within 15m of any road in year_from
-- Uses geography cast for accurate metre-based distance calculation
CREATE OR REPLACE FUNCTION find_new_roads(
    p_region_id  INT,
    p_year_from  INT,
    p_year_to    INT
)
RETURNS TABLE (
    id         BIGINT,
    geom       GEOMETRY,
    length_km  FLOAT,
    highway    TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT r2.id, r2.geom, r2.length_km, r2.highway
    FROM road_segments r2
    WHERE r2.region_id = p_region_id
      AND r2.year      = p_year_to
      AND NOT EXISTS (
          SELECT 1
          FROM road_segments r1
          WHERE r1.region_id = p_region_id
            AND r1.year      = p_year_from
            AND ST_DWithin(
                r2.geom::geography,
                r1.geom::geography,
                15   -- 15 metre buffer threshold
            )
      );
END;
$$ LANGUAGE plpgsql
   STABLE
   PARALLEL SAFE;

COMMENT ON FUNCTION find_new_roads(INT, INT, INT) IS
  'Identifies road segments present in year_to that have no corresponding road within 15 m in year_from. Uses ST_DWithin on geography for accurate distance.';

-- Function: get_region_bbox
-- Returns the bounding box of a region as a geometry for use in API filters
CREATE OR REPLACE FUNCTION get_region_bbox(p_region_id INT)
RETURNS GEOMETRY AS $$
    SELECT ST_Envelope(geom) FROM regions WHERE id = p_region_id;
$$ LANGUAGE sql
   STABLE
   PARALLEL SAFE;

COMMENT ON FUNCTION get_region_bbox(INT) IS
  'Returns the axis-aligned bounding box of a region geometry (POLYGON, EPSG:4326).';

-- Function: refresh_network_stats
-- Upserts computed stats for a region/year into road_network_stats
CREATE OR REPLACE FUNCTION refresh_network_stats(p_region_id INT, p_year INT)
RETURNS VOID AS $$
DECLARE
    v_total_length  FLOAT;
    v_road_count    INT;
    v_avg_width     FLOAT;
    v_density       FLOAT;
BEGIN
    SELECT
        SUM(length_km),
        COUNT(*),
        AVG(width_m)
    INTO v_total_length, v_road_count, v_avg_width
    FROM road_segments
    WHERE region_id = p_region_id AND year = p_year;

    v_density := calculate_road_density(p_region_id, p_year);

    INSERT INTO road_network_stats (
        region_id, year,
        total_length_km, road_count,
        avg_width_m, road_density_km_per_km2
    )
    VALUES (
        p_region_id, p_year,
        v_total_length, v_road_count,
        v_avg_width, v_density
    )
    ON CONFLICT (region_id, year) DO UPDATE
        SET total_length_km          = EXCLUDED.total_length_km,
            road_count               = EXCLUDED.road_count,
            avg_width_m              = EXCLUDED.avg_width_m,
            road_density_km_per_km2  = EXCLUDED.road_density_km_per_km2,
            created_at               = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_network_stats(INT, INT) IS
  'Computes and upserts basic network stats (total length, road count, avg width, density) for a region/year into road_network_stats.';

-- =============================================================================
-- SEED: data_sources
-- Pre-populate registry with all known external data sources
-- =============================================================================

INSERT INTO data_sources
    (name, source_type, url, api_endpoint, data_date_from, data_date_to,
     coverage, resolution, units, reliability, limitations, auth_required)
VALUES
-- OpenStreetMap / ohsome
(
    'OpenStreetMap (OSM) via ohsome API',
    'OSM',
    'https://www.openstreetmap.org',
    'https://api.ohsome.org/v1',
    '2007-01-01',
    NULL,                           -- continuously updated
    'Global (India fully covered)',
    'Vector (sub-metre)',
    'WGS-84 coordinates, lengths in km',
    'High',
    'Completeness varies by region; rural/semi-urban areas may be under-mapped. Contributor bias toward urban centres. No official width tags for most Indian roads — widths inferred from lanes or road class.',
    FALSE
),
-- Landsat 8
(
    'Landsat 8 (OLI/TIRS)',
    'satellite',
    'https://www.usgs.gov/landsat-missions/landsat-8',
    'https://landsatoncloud.usgs.gov/stac/v0/collections/landsat-c2l2-sr',
    '2013-02-11',
    NULL,
    'Global (India fully covered)',
    '30 m (multispectral), 15 m (panchromatic), 100 m (thermal)',
    'Reflectance (unitless, 0–1 scaled)',
    'High',
    'Cloud cover in monsoon season (June–September) limits usable scenes. 16-day revisit cycle. Band 6 (SWIR) saturation in high-temperature surfaces.',
    FALSE
),
-- Landsat 9
(
    'Landsat 9 (OLI-2/TIRS-2)',
    'satellite',
    'https://www.usgs.gov/landsat-missions/landsat-9',
    'https://landsatoncloud.usgs.gov/stac/v0/collections/landsat-c2l2-sr',
    '2021-10-31',
    NULL,
    'Global (India fully covered)',
    '30 m (multispectral), 15 m (panchromatic)',
    'Reflectance (unitless, 0–1 scaled)',
    'High',
    'Cloud cover limitations same as Landsat 8. Use alongside L8 to improve temporal coverage. 16-day revisit (8-day combined with L8).',
    FALSE
),
-- Sentinel-2
(
    'Sentinel-2 (MSI) — ESA Copernicus',
    'satellite',
    'https://sentinel.esa.int/web/sentinel/missions/sentinel-2',
    'https://catalogue.dataspace.copernicus.eu/odata/v1',
    '2015-06-23',
    NULL,
    'Global land (India fully covered)',
    '10 m (B2/B3/B4/B8), 20 m (B5/B6/B7/B8A/B11/B12), 60 m (B1/B9/B10)',
    'Top-of-Atmosphere / Surface Reflectance (L1C/L2A)',
    'High',
    'Two satellites (2A+2B) give 5-day revisit. Monsoon cloud cover limits usable imagery June–September. No thermal band. Atmospheric correction (Sen2Cor) required for L2A.',
    FALSE
),
-- GHSL
(
    'Global Human Settlement Layer (GHSL) — EC JRC',
    'derived',
    'https://ghsl.jrc.ec.europa.eu',
    'https://ghsl.jrc.ec.europa.eu/download.php',
    '1975-01-01',
    '2030-12-31',   -- projected layers available
    'Global',
    '10 m / 100 m / 1 km (product-dependent)',
    'Built-up area fraction (0–1), population count',
    'High',
    'Built-up classification may conflate large rooftops with roads. 2020 epoch is most accurate; 1975 and 1990 have higher commission errors. Does not distinguish road type.',
    FALSE
),
-- ESA WorldCover
(
    'ESA WorldCover 10 m 2020/2021',
    'derived',
    'https://esa-worldcover.org',
    'https://services.terrascope.be/wms/v2',
    '2020-01-01',
    '2021-12-31',
    'Global land',
    '10 m',
    'Land cover class (integer code)',
    'High',
    'Urban/built-up class may include large paved areas. Limited temporal coverage (2 epochs: 2020, 2021). Does not capture annual or seasonal change.',
    FALSE
),
-- ESRI Annual Land Cover
(
    'ESRI Annual Land Cover (10 m)',
    'derived',
    'https://livingatlas.arcgis.com/landcover',
    'https://io.biodiversityresearch.com/api/v1/landcover',
    '2017-01-01',
    NULL,
    'Global land',
    '10 m',
    'Land cover class (integer code)',
    'High',
    'Annual product enables temporal analysis. Some class confusion between crop and bare land. Trained on Sentinel-2 — cloud contamination periods may reduce quality.',
    FALSE
),
-- OGD India
(
    'Open Government Data (OGD) India Platform',
    'government',
    'https://data.gov.in',
    'https://api.data.gov.in/resource',
    '2012-01-01',
    NULL,
    'India (national + state datasets)',
    'Varies by dataset (tabular to district-level spatial)',
    'Varies (km, count, %, INR)',
    'Medium',
    'Dataset completeness varies by state and ministry. Update frequency inconsistent. Spatial data often available only at district level. Some datasets require institutional access.',
    FALSE
),
-- MoRTH
(
    'Ministry of Road Transport & Highways (MoRTH) — Annual Report',
    'government',
    'https://morth.nic.in',
    NULL,
    '2000-01-01',
    NULL,
    'India (national highway network)',
    'Tabular (state/NH-level summaries)',
    'km of road length, INR (expenditure)',
    'High',
    'Annual report data — updated once per year. Granular road-level spatial data not publicly released. NH numbers have been renumbered since 2016, causing discontinuities in time-series.',
    FALSE
),
-- NHAI
(
    'National Highways Authority of India (NHAI)',
    'government',
    'https://nhai.gov.in',
    NULL,
    '1995-01-01',
    NULL,
    'India (national highway corridors)',
    'Tabular + limited vector (project-level)',
    'km length, project status',
    'High',
    'Project-level data not always spatially precise. No open API. Most data available through PDF reports or the NHAI One portal with login.',
    TRUE
),
-- ISRO Bhuvan
(
    'ISRO Bhuvan — National Remote Sensing Centre (NRSC)',
    'satellite',
    'https://bhuvan.nrsc.gov.in',
    'https://bhuvan-app3.nrsc.gov.in/api',
    '2000-01-01',
    NULL,
    'India (full national coverage)',
    '2.5 m (Cartosat) to 56 m (AWiFS)',
    'DN / surface reflectance / thematic classes',
    'Medium',
    'API access requires institutional registration with NRSC. Some high-resolution products restricted to government users. Temporal archive sparser than Landsat/Sentinel for open access.',
    TRUE
),
-- WorldPop
(
    'WorldPop — University of Southampton',
    'derived',
    'https://www.worldpop.org',
    'https://hub.worldpop.org/rest/data',
    '2000-01-01',
    '2030-12-31',
    'Global (India covered at district level)',
    '100 m / 1 km',
    'Population count per pixel',
    'Medium',
    'Modelled estimates — uncertainty increases in rapidly changing urban fringe areas. 2020 census not yet integrated (uses 2011 India census as base). Does not capture intra-urban density variation well at coarse resolution.',
    FALSE
)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- GRANT minimal privileges (adjust roles as needed for production)
-- =============================================================================

-- Example: grant read-only access to an API service role
-- CREATE ROLE geotrack_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO geotrack_readonly;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO geotrack_readonly;
