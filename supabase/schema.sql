-- =============================================================================
-- Supabase (PostgreSQL 15+ with PostGIS) Comprehensive Drought Schema
-- Supports:
--   1. Historical Multi-Scale Pipeline Data (954 Villages + 10 Tehsils, 2016–2026)
--   2. Near-Realtime Earth Observation Satellite Ingestion (Sentinel-2 + CHIRPS)
--   3. Spatial RPC Functions for Sub-millisecond GeoJSON & Timeseries Serving
-- =============================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Administrative Tehsils Table (10 Administrative Sub-districts)
CREATE TABLE IF NOT EXISTS public.tehsils (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    geom GEOMETRY(MultiPolygon, 4326),
    area_km2 NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Cadastral Revenue Villages Table (954 Villages)
CREATE TABLE IF NOT EXISTS public.villages (
    id SERIAL PRIMARY KEY,
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL,
    village_code TEXT,
    centroid_lat NUMERIC(9, 6),
    centroid_lon NUMERIC(9, 6),
    geom GEOMETRY(MultiPolygon, 4326),
    area_km2 NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_village_per_tehsil UNIQUE (tehsil, village)
);

-- 4. Tehsil Monthly Historical Metrics Table (10 Tehsils x 128 Months)
CREATE TABLE IF NOT EXISTS public.tehsil_monthly_metrics (
    id BIGSERIAL PRIMARY KEY,
    district TEXT NOT NULL DEFAULT 'Latur',
    tehsil TEXT NOT NULL,
    observation_period TEXT NOT NULL, -- e.g. '2016-01' to '2026-10'
    year INT NOT NULL,
    month INT NOT NULL,
    monthly_rainfall_mm NUMERIC(8, 2),
    spi_1 NUMERIC(8, 4),
    spi_3 NUMERIC(8, 4),
    spi_6 NUMERIC(8, 4),
    spi_12 NUMERIC(8, 4),
    mean_ndvi NUMERIC(8, 4),
    mean_evi NUMERIC(8, 4),
    mean_vci NUMERIC(8, 2),
    mean_vhi NUMERIC(8, 2),
    mean_pci NUMERIC(8, 2),
    composite_drought_score NUMERIC(8, 4),
    composite_drought_class TEXT,
    pct_area_dry NUMERIC(5, 2),
    total_drought_area_km2 NUMERIC(10, 2),
    active_villages_count INT DEFAULT 0,
    drought_villages_count INT DEFAULT 0,
    data_quality_status TEXT DEFAULT 'success',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_tehsil_period UNIQUE (tehsil, observation_period)
);

-- 5. Village Historical Pipeline Data Table (954 Villages x 128 Months Continuous)
CREATE TABLE IF NOT EXISTS public.village_monthly_metrics (
    id BIGSERIAL PRIMARY KEY,
    district TEXT NOT NULL DEFAULT 'Latur',
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL,
    observation_period TEXT NOT NULL, -- e.g. '2016-01' to '2026-10'
    year INT NOT NULL,
    month INT NOT NULL,
    monthly_rainfall_mm NUMERIC(8, 2),
    spi_1 NUMERIC(8, 4),
    spi_3 NUMERIC(8, 4),
    spi_6 NUMERIC(8, 4),
    spi_12 NUMERIC(8, 4),
    ndvi NUMERIC(8, 4),
    evi NUMERIC(8, 4),
    vci NUMERIC(8, 2),
    vhi NUMERIC(8, 2),
    tci NUMERIC(8, 2),
    pci NUMERIC(8, 2),
    composite_drought_score NUMERIC(8, 4),
    composite_drought_class TEXT,
    baseline_ndvi NUMERIC(8, 4),
    baseline_vci NUMERIC(8, 2),
    baseline_spi3 NUMERIC(8, 4),
    composite_anomaly NUMERIC(8, 4),
    data_quality_status TEXT DEFAULT 'success', -- 'success' | 'chirps_only'
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_village_monthly_obs UNIQUE (tehsil, village, observation_period)
);

-- 6. Near-Realtime Satellite Observations Table (Live GEE S2 + CHIRPS Streaming)
CREATE TABLE IF NOT EXISTS public.realtime_observations (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'Sentinel-2 MSI Level-2A',
    granule_id TEXT,
    sensing_time TIMESTAMPTZ NOT NULL,
    observation_period TEXT NOT NULL, -- e.g. '2026-10'
    tehsil TEXT NOT NULL,
    village TEXT,
    cloud_percentage NUMERIC(5, 2),
    ndvi NUMERIC(8, 4),
    evi NUMERIC(8, 4),
    vci NUMERIC(8, 2),
    vhi NUMERIC(8, 2),
    tci NUMERIC(8, 2),
    pci NUMERIC(8, 2),
    spi_1 NUMERIC(8, 4),
    spi_3 NUMERIC(8, 4),
    composite_drought_score NUMERIC(8, 4),
    composite_drought_class TEXT,
    gee_tile_url TEXT,
    raw_band_stats JSONB DEFAULT '{}'::jsonb,
    data_quality_status TEXT DEFAULT 'live_verified',
    ingestion_timestamp TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_realtime_entry UNIQUE (tehsil, village, observation_period, sensing_time)
);

-- 7. Master Row Table (Repository Master Mirror for Administrative Compatibility)
CREATE TABLE IF NOT EXISTS public.master_row (
    id BIGSERIAL PRIMARY KEY,
    district TEXT NOT NULL DEFAULT 'Latur',
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL DEFAULT '',
    observation_period TEXT NOT NULL, -- e.g. '2026-10'
    observation_date TEXT,
    year INT NOT NULL,
    month INT NOT NULL,
    monthly_rainfall_mm NUMERIC(8, 2),
    chirps_data_through TEXT,
    spi_1 NUMERIC(8, 4),
    spi_3 NUMERIC(8, 4),
    spi_6 NUMERIC(8, 4),
    spi_12 NUMERIC(8, 4),
    spi_reference_period TEXT DEFAULT '2016-2026',
    ndvi NUMERIC(8, 4),
    evi NUMERIC(8, 4),
    vci NUMERIC(8, 2),
    vhi NUMERIC(8, 2),
    pci NUMERIC(8, 2),
    composite_drought_score NUMERIC(8, 4),
    composite_drought_class TEXT,
    component_contributions JSONB DEFAULT '{"PCI": 0.50, "VCI": 0.25, "TCI": 0.25}'::jsonb,
    composite_formula_version TEXT DEFAULT 'cdi-v2026.10',
    drought_area_km2 NUMERIC(10, 2),
    drought_percentage NUMERIC(5, 2),
    total_polygon_area_km2 NUMERIC(10, 2),
    sentinel2_observation_date TEXT,
    sentinel2_cloud_percentage NUMERIC(5, 2),
    data_quality_status TEXT DEFAULT 'success',
    processing_timestamp TIMESTAMPTZ DEFAULT NOW(),
    processing_run_id TEXT,
    lon NUMERIC(9, 6),
    lat NUMERIC(9, 6),
    CONSTRAINT uq_master_row_entry UNIQUE (tehsil, village, observation_period)
);

-- 8. Processing Manifest Table (Incremental Tracking)
CREATE TABLE IF NOT EXISTS public.processing_manifest (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    period_id TEXT NOT NULL,
    observation_date TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    outputs JSONB,
    input_ids JSONB,
    cloud_pct NUMERIC(5, 2),
    qc JSONB,
    notes TEXT,
    CONSTRAINT uq_manifest_entry UNIQUE (source, period_id)
);

-- =============================================================================
-- Indexes for Sub-millisecond Spatial & Temporal Queries
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_tehsils_geom ON public.tehsils USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_villages_geom ON public.villages USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_tehsil_monthly_lookup ON public.tehsil_monthly_metrics (tehsil, observation_period);
CREATE INDEX IF NOT EXISTS idx_tehsil_monthly_date ON public.tehsil_monthly_metrics (year, month);

CREATE INDEX IF NOT EXISTS idx_village_monthly_lookup ON public.village_monthly_metrics (tehsil, village, observation_period);
CREATE INDEX IF NOT EXISTS idx_village_monthly_period ON public.village_monthly_metrics (observation_period);
CREATE INDEX IF NOT EXISTS idx_village_monthly_date ON public.village_monthly_metrics (year, month);

CREATE INDEX IF NOT EXISTS idx_realtime_lookup ON public.realtime_observations (tehsil, village, observation_period);
CREATE INDEX IF NOT EXISTS idx_realtime_time ON public.realtime_observations (sensing_time DESC);

CREATE INDEX IF NOT EXISTS idx_master_row_lookup ON public.master_row (tehsil, village, observation_period);
CREATE INDEX IF NOT EXISTS idx_master_row_period ON public.master_row (observation_period);

-- =============================================================================
-- Row Level Security (RLS) Configuration
-- =============================================================================
ALTER TABLE public.tehsils ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.villages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tehsil_monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.village_monthly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.realtime_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_row ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_manifest ENABLE ROW LEVEL SECURITY;

-- Public Anonymous Read Policies
CREATE POLICY "Public Read Tehsils" ON public.tehsils FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Villages" ON public.villages FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Tehsil Monthly" ON public.tehsil_monthly_metrics FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Village Monthly" ON public.village_monthly_metrics FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Realtime" ON public.realtime_observations FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Master Row" ON public.master_row FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Public Read Manifest" ON public.processing_manifest FOR SELECT TO anon, authenticated USING (true);

-- Service Role Full Management Policies
CREATE POLICY "Service Role Tehsils" ON public.tehsils FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Villages" ON public.villages FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Tehsil Monthly" ON public.tehsil_monthly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Village Monthly" ON public.village_monthly_metrics FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Realtime" ON public.realtime_observations FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Master Row" ON public.master_row FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service Role Manifest" ON public.processing_manifest FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =============================================================================
-- Spatial Helper RPC Functions for Live Frontend Consumption
-- =============================================================================

-- Function: Get Tehsil Boundaries as GeoJSON FeatureCollection
CREATE OR REPLACE FUNCTION public.get_tehsils_geojson()
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'properties', jsonb_build_object('name', name, 'TEHSIL', name, 'area_km2', area_km2),
                'geometry', ST_AsGeoJSON(geom)::jsonb
            )
        ), '[]'::jsonb)
    )
    FROM public.tehsils;
$$;

-- Function: Get Realtime Active Status for Latur District
CREATE OR REPLACE FUNCTION public.get_realtime_drought_summary(p_period TEXT DEFAULT '2026-10')
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'observation_period', p_period,
        'monitored_villages', COUNT(*),
        'mean_spi3', ROUND(AVG(spi_3)::numeric, 3),
        'mean_ndvi', ROUND(AVG(ndvi)::numeric, 3),
        'mean_cdi', ROUND(AVG(composite_drought_score)::numeric, 3),
        'd0_count', COUNT(*) FILTER (WHERE composite_drought_class = 'D0'),
        'd1_count', COUNT(*) FILTER (WHERE composite_drought_class = 'D1'),
        'd2_count', COUNT(*) FILTER (WHERE composite_drought_class = 'D2'),
        'd3_count', COUNT(*) FILTER (WHERE composite_drought_class = 'D3'),
        'd4_count', COUNT(*) FILTER (WHERE composite_drought_class = 'D4')
    )
    INTO v_result
    FROM public.village_monthly_metrics
    WHERE observation_period = p_period;

    RETURN v_result;
END;
$$;
