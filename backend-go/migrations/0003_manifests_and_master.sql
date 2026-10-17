-- =====================================================================
-- Processing manifests + dashboard master view
-- =====================================================================

create table if not exists processing_manifest (
    id              bigserial primary key,
    source          text not null,       -- 'sentinel-2' | 'chirps' | 'rf'
    period_id       text not null,       -- 'YYYY-MM'
    observation_date date,
    processed_at    timestamptz not null default now(),
    status          text not null check (status in ('success','failed','pending')),
    outputs         jsonb,
    input_ids       jsonb,
    cloud_pct       double precision,
    qc              jsonb,
    notes           text,
    unique (source, period_id)
);
create index if not exists manifest_source_period on processing_manifest (source, period_id);

-- One row per (tehsil, period) — mirrors drought_monitoring_master.csv.
create table if not exists master_row (
    id                        bigserial primary key,
    district                  text not null default 'Latur',
    tehsil                    text not null,
    observation_period        text not null,     -- 'YYYY-MM'
    year                      int,
    month                     int,
    monthly_rainfall_mm       double precision,
    chirps_data_through       date,
    spi_1                     double precision,
    spi_3                     double precision,
    spi_6                     double precision,
    spi_12                    double precision,
    spi_reference_period      text,
    ndvi                      double precision,
    evi                       double precision,
    pci                       double precision,
    vhi                       double precision,
    multi_index_drought_score double precision,
    rf_drought_class          text,
    rf_confidence             double precision,
    drought_area_km2          double precision,
    drought_percentage        double precision,
    total_tehsil_area_km2     double precision,
    sentinel2_observation_date date,
    sentinel2_cloud_percentage double precision,
    data_quality_status       text,
    processing_timestamp      timestamptz,
    model_version             text,
    processing_run_id         text,
    unique (tehsil, observation_period)
);
create index if not exists master_period on master_row (observation_period);
create index if not exists master_tehsil on master_row (tehsil);

-- Reads: public. Writes: service_role only.
alter table processing_manifest enable row level security;
alter table master_row          enable row level security;
drop policy if exists "public read" on processing_manifest;
create policy "public read" on processing_manifest for select using (true);
drop policy if exists "public read" on master_row;
create policy "public read" on master_row          for select using (true);
