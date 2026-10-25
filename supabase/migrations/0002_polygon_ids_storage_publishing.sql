-- =============================================================================
-- 0002  Polygon-id keys, publishing tables, Storage bucket
--
-- Run after supabase/schema.sql (SQL editor, or `supabase db push`). Idempotent.
--
-- Why:
--  * schema.sql keys villages by (tehsil, village). Three pairs of villages share a
--    name inside one tehsil (Anandwadi, Hatkarwadi, Kamshetwadi), so seeding with
--    ON CONFLICT DO NOTHING silently dropped 3 of 954. Polygon id is the real key.
--  * The dashboard's big derived files (village history ~20 MB, baselines, district
--    series) belong in Supabase Storage, not in git.
--  * Every pipeline run should leave an auditable row.
-- =============================================================================

BEGIN;

-- ---- 1. villages: key on polygon id ---------------------------------------
ALTER TABLE public.villages ADD COLUMN IF NOT EXISTS polygon_id INT;
ALTER TABLE public.villages DROP CONSTRAINT IF EXISTS uq_village_per_tehsil;
CREATE UNIQUE INDEX IF NOT EXISTS uq_villages_polygon_id ON public.villages (polygon_id);

-- ---- 1b. remove defaults that invented values --------------------------------------
-- schema.sql pre-filled master_row.component_contributions with {"PCI": .5, "VCI": .25, "TCI": .25} (a formula
-- the pipeline never used) and a fixed spi_reference_period. A row must carry what was computed, or NULL.
ALTER TABLE public.master_row ALTER COLUMN component_contributions DROP DEFAULT;
ALTER TABLE public.master_row ALTER COLUMN spi_reference_period DROP DEFAULT;
ALTER TABLE public.master_row ALTER COLUMN composite_formula_version DROP DEFAULT;
ALTER TABLE public.realtime_observations ALTER COLUMN source DROP DEFAULT;

-- ---- 2. one row per village and month, keyed on polygon id ------------------
CREATE TABLE IF NOT EXISTS public.village_monthly (
    village_id   INT  NOT NULL,            -- = polygon id in latur_villages*.geojson
    period       TEXT NOT NULL CHECK (period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    cdi          NUMERIC(6, 4) CHECK (cdi BETWEEN 0 AND 1),
    cdi_class    TEXT CHECK (cdi_class IN ('None','D0','D1','D2','D3','D4','ND')),
    ndvi         NUMERIC(7, 4),
    evi          NUMERIC(7, 4),
    vci          NUMERIC(6, 2),
    vhi          NUMERIC(6, 2),
    pci          NUMERIC(6, 2),
    tci          NUMERIC(6, 2),           -- temperature condition index
    smi          NUMERIC(6, 2),           -- soil moisture index (Sentinel-1 VV, relative)
    lst_c        NUMERIC(5, 2),           -- daytime land-surface temperature, deg C (Landsat 8/9)
    vv_db        NUMERIC(6, 2),           -- Sentinel-1 VV backscatter, dB
    rain_mm      NUMERIC(8, 2),
    spi1         NUMERIC(7, 3),
    spi3         NUMERIC(7, 3),
    spi6         NUMERIC(7, 3),
    spi12        NUMERIC(7, 3),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (village_id, period)
);
CREATE INDEX IF NOT EXISTS idx_village_monthly_period ON public.village_monthly (period);

-- ---- 3. pipeline run log ---------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    id            BIGSERIAL PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ,
    ok            BOOLEAN NOT NULL,
    ingested      JSONB NOT NULL DEFAULT '[]'::jsonb,   -- periods ingested this run
    steps         JSONB NOT NULL DEFAULT '[]'::jsonb,
    git_sha       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON public.pipeline_runs (started_at DESC);

-- ---- 4. Row Level Security: public read, service_role write -----------------
ALTER TABLE public.village_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_runs   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public Read Village Monthly Id" ON public.village_monthly;
CREATE POLICY "Public Read Village Monthly Id" ON public.village_monthly
    FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Service Role Village Monthly Id" ON public.village_monthly;
CREATE POLICY "Service Role Village Monthly Id" ON public.village_monthly
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Public Read Pipeline Runs" ON public.pipeline_runs;
CREATE POLICY "Public Read Pipeline Runs" ON public.pipeline_runs
    FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Service Role Pipeline Runs" ON public.pipeline_runs;
CREATE POLICY "Service Role Pipeline Runs" ON public.pipeline_runs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- anon must never write: strip default grants, then give back SELECT only.
REVOKE ALL ON public.village_monthly, public.pipeline_runs FROM anon, authenticated;
GRANT SELECT ON public.village_monthly, public.pipeline_runs TO anon, authenticated;
GRANT ALL ON public.village_monthly, public.pipeline_runs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.pipeline_runs_id_seq TO service_role;

-- ---- 5. RPCs the frontend can call with the anon key -----------------------
-- Summary counts for one month (period is required: no default month).
DROP FUNCTION IF EXISTS public.get_realtime_drought_summary(TEXT);
CREATE OR REPLACE FUNCTION public.get_realtime_drought_summary(p_period TEXT)   -- period is required, no default month
RETURNS JSONB LANGUAGE sql STABLE AS $$
    SELECT jsonb_build_object(
        'observation_period', p_period,
        'villages', COUNT(*),
        'assessed', COUNT(cdi),
        'mean_cdi', ROUND(AVG(cdi), 3),
        'd0_count', COUNT(*) FILTER (WHERE cdi_class = 'D0'),
        'd1_count', COUNT(*) FILTER (WHERE cdi_class = 'D1'),
        'd2_count', COUNT(*) FILTER (WHERE cdi_class = 'D2'),
        'd3_count', COUNT(*) FILTER (WHERE cdi_class = 'D3'),
        'd4_count', COUNT(*) FILTER (WHERE cdi_class = 'D4'))
    FROM public.village_monthly WHERE period = p_period;
$$;
GRANT EXECUTE ON FUNCTION public.get_realtime_drought_summary(TEXT) TO anon, authenticated;

-- One month for every village (map snapshot) - ~954 rows.
CREATE OR REPLACE FUNCTION public.get_period_snapshot(p_period TEXT)
RETURNS SETOF public.village_monthly
LANGUAGE sql STABLE AS $$
    SELECT * FROM public.village_monthly WHERE period = p_period ORDER BY village_id;
$$;

-- Full history of one village (~130 rows).
CREATE OR REPLACE FUNCTION public.get_village_series(p_village_id INT)
RETURNS SETOF public.village_monthly
LANGUAGE sql STABLE AS $$
    SELECT * FROM public.village_monthly WHERE village_id = p_village_id ORDER BY period;
$$;

-- Tehsil league table for a month.
CREATE OR REPLACE FUNCTION public.get_tehsil_summary(p_period TEXT)
RETURNS TABLE (tehsil TEXT, villages BIGINT, assessed BIGINT, mean_cdi NUMERIC,
               in_drought BIGINT, d2_plus BIGINT)
LANGUAGE sql STABLE AS $$
    SELECT v.tehsil,
           COUNT(*),
           COUNT(m.cdi),
           ROUND(AVG(m.cdi), 3),
           COUNT(*) FILTER (WHERE m.cdi_class IN ('D0','D1','D2','D3','D4')),
           COUNT(*) FILTER (WHERE m.cdi_class IN ('D2','D3','D4'))
    FROM public.villages v
    LEFT JOIN public.village_monthly m ON m.village_id = v.polygon_id AND m.period = p_period
    WHERE v.polygon_id IS NOT NULL            -- ignore legacy name-keyed rows from the old seed
    GROUP BY v.tehsil
    ORDER BY AVG(m.cdi) DESC NULLS LAST;
$$;

GRANT EXECUTE ON FUNCTION public.get_period_snapshot(TEXT), public.get_village_series(INT),
                          public.get_tehsil_summary(TEXT) TO anon, authenticated;

-- ---- 6. Storage bucket for published data files ------------------------------
-- Public read (the files are open data); only service_role may write.
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('drought-data', 'drought-data', true, 52428800,
        ARRAY['application/json', 'application/geo+json', 'text/csv'])
ON CONFLICT (id) DO UPDATE
    SET public = EXCLUDED.public,
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "drought-data public read" ON storage.objects;
CREATE POLICY "drought-data public read" ON storage.objects
    FOR SELECT TO anon, authenticated USING (bucket_id = 'drought-data');

DROP POLICY IF EXISTS "drought-data service write" ON storage.objects;
CREATE POLICY "drought-data service write" ON storage.objects
    FOR ALL TO service_role USING (bucket_id = 'drought-data') WITH CHECK (bucket_id = 'drought-data');

COMMIT;
