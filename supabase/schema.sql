-- =============================================================================
-- Supabase (PostgreSQL + PostGIS) Database Schema for Latur Drought Monitoring
-- Target: Supabase Cloud / Self-hosted PostgreSQL 15+ with PostGIS
-- =============================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Tehsils (Sub-districts) Table
CREATE TABLE IF NOT EXISTS public.tehsils (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    geom GEOMETRY(MultiPolygon, 4326),
    area_km2 NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Villages Table (954 revenue villages)
CREATE TABLE IF NOT EXISTS public.villages (
    id SERIAL PRIMARY KEY,
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL,
    village_code TEXT,
    geom GEOMETRY(MultiPolygon, 4326),
    area_km2 NUMERIC(8, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_village_per_tehsil UNIQUE (tehsil, village)
);

-- 4. Monthly Index Table (District aggregate timeseries)
CREATE TABLE IF NOT EXISTS public.monthly_index (
    id BIGSERIAL PRIMARY KEY,
    index_name TEXT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    value NUMERIC(10, 4),
    class_label TEXT,
    pct_area_dry NUMERIC(5, 2),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_monthly_index UNIQUE (index_name, year, month)
);

-- 5. Village SPI Table (Detailed 954 village CHIRPS multi-scale SPI records)
CREATE TABLE IF NOT EXISTS public.village_spi (
    id BIGSERIAL PRIMARY KEY,
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL,
    observation_period TEXT NOT NULL, -- e.g. '2026-08'
    year INT NOT NULL,
    month INT NOT NULL,
    spi_1 NUMERIC(8, 4),
    spi_3 NUMERIC(8, 4),
    spi_6 NUMERIC(8, 4),
    spi_12 NUMERIC(8, 4),
    monthly_rainfall_mm NUMERIC(8, 2),
    ndvi NUMERIC(8, 4),
    evi NUMERIC(8, 4),
    vci NUMERIC(8, 2),
    vhi NUMERIC(8, 2),
    pci NUMERIC(8, 2),
    composite_drought_score NUMERIC(8, 4),
    composite_drought_class TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_village_obs UNIQUE (tehsil, village, observation_period)
);

-- 6. Master Row Table (Denormalized Master Operational Table)
CREATE TABLE IF NOT EXISTS public.master_row (
    id BIGSERIAL PRIMARY KEY,
    district TEXT NOT NULL DEFAULT 'Latur',
    tehsil TEXT NOT NULL,
    village TEXT NOT NULL DEFAULT '',
    observation_period TEXT NOT NULL, -- e.g. '2026-08'
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
    component_contributions JSONB DEFAULT '{}'::jsonb,
    composite_formula_version TEXT DEFAULT 'cdi-v2026.10',
    drought_area_km2 NUMERIC(10, 2),
    drought_percentage NUMERIC(5, 2),
    total_polygon_area_km2 NUMERIC(10, 2),
    sentinel2_observation_date TEXT,
    sentinel2_cloud_percentage NUMERIC(5, 2),
    data_quality_status TEXT DEFAULT 'spi_verified_sentinel_pending',
    processing_timestamp TIMESTAMPTZ DEFAULT NOW(),
    processing_run_id TEXT,
    CONSTRAINT uq_master_row UNIQUE (tehsil, village, observation_period)
);

-- 7. Processing Manifest Table
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
-- Indexes for High Performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_tehsils_geom ON public.tehsils USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_villages_geom ON public.villages USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_village_spi_lookup ON public.village_spi (tehsil, village, observation_period);
CREATE INDEX IF NOT EXISTS idx_village_spi_period ON public.village_spi (observation_period);
CREATE INDEX IF NOT EXISTS idx_village_spi_date ON public.village_spi (year, month);

CREATE INDEX IF NOT EXISTS idx_master_row_lookup ON public.master_row (tehsil, village, observation_period);
CREATE INDEX IF NOT EXISTS idx_master_row_period ON public.master_row (observation_period);
CREATE INDEX IF NOT EXISTS idx_master_row_tehsil ON public.master_row (tehsil);

CREATE INDEX IF NOT EXISTS idx_monthly_index_lookup ON public.monthly_index (index_name, year, month);

-- =============================================================================
-- Row Level Security (RLS) Configuration
-- Allows public anonymous read access for Next.js frontend;
-- Restricts write operations to service_role (backend/pipeline).
-- =============================================================================

ALTER TABLE public.tehsils ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.villages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monthly_index ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.village_spi ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_row ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_manifest ENABLE ROW LEVEL SECURITY;

-- Anonymous & Authenticated Read Policies
CREATE POLICY "Public Read Tehsils" ON public.tehsils
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Public Read Villages" ON public.villages
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Public Read Monthly Index" ON public.monthly_index
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Public Read Village SPI" ON public.village_spi
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Public Read Master Row" ON public.master_row
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "Public Read Manifest" ON public.processing_manifest
    FOR SELECT TO anon, authenticated USING (true);

-- =============================================================================
-- Spatial Helper RPC Functions (for fast GeoJSON serving from Supabase)
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

-- Function: Get Villages as GeoJSON FeatureCollection by Tehsil
CREATE OR REPLACE FUNCTION public.get_villages_geojson(p_tehsil TEXT DEFAULT NULL)
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(jsonb_agg(
            jsonb_build_object(
                'type', 'Feature',
                'properties', jsonb_build_object(
                    'village', village,
                    'tehsil', tehsil,
                    'area_km2', area_km2
                ),
                'geometry', ST_AsGeoJSON(geom)::jsonb
            )
        ), '[]'::jsonb)
    )
    FROM public.villages
    WHERE (p_tehsil IS NULL OR LOWER(tehsil) = LOWER(p_tehsil));
$$;
