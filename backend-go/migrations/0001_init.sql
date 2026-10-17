-- =====================================================================
-- Latur Drought Monitoring — initial schema
-- Apply to a Supabase project (or local Postgres via docker-compose).
-- =====================================================================

create extension if not exists postgis;

-- ---------------------------------------------------------------------
-- Tehsils (district subdivisions). Loaded once from the shapefile.
-- ---------------------------------------------------------------------
create table if not exists tehsils (
    id          serial primary key,
    name        text   not null unique,
    geom        geometry(MultiPolygon, 4326) not null
);
create index if not exists tehsils_geom_idx on tehsils using gist (geom);

-- ---------------------------------------------------------------------
-- District-mean monthly index time series (feeds the chart endpoints).
-- ---------------------------------------------------------------------
create table if not exists monthly_index (
    id            bigserial primary key,
    index_name    text not null,  -- 'spi1','spi3','spi6','spi12','ndvi','evi','ndmi','vci','vhi','pci','cdi'
    year          int  not null,
    month         int  not null check (month between 1 and 12),
    value         double precision,
    class_label   text,
    pct_area_dry  double precision,
    updated_at    timestamptz not null default now(),
    unique (index_name, year, month)
);
create index if not exists monthly_index_lookup on monthly_index (index_name, year, month);

-- ---------------------------------------------------------------------
-- Per-pixel index values (feeds the map endpoints).
-- One row per (index, year, month, pixel).
-- ---------------------------------------------------------------------
create table if not exists pixel_index (
    id          bigserial primary key,
    index_name  text not null,
    year        int  not null,
    month       int  not null check (month between 1 and 12),
    pixel_id    int  not null,
    lon         double precision,
    lat         double precision,
    value       double precision,
    geom        geometry(Polygon, 4326)
);
create index if not exists pixel_index_lookup on pixel_index (index_name, year, month);
create index if not exists pixel_index_geom_idx on pixel_index using gist (geom);

-- ---------------------------------------------------------------------
-- Row-level security — public reads, service_role writes.
-- ---------------------------------------------------------------------
alter table tehsils       enable row level security;
alter table monthly_index enable row level security;
alter table pixel_index   enable row level security;

drop policy if exists "public read" on tehsils;
create policy "public read" on tehsils       for select using (true);

drop policy if exists "public read" on monthly_index;
create policy "public read" on monthly_index for select using (true);

drop policy if exists "public read" on pixel_index;
create policy "public read" on pixel_index   for select using (true);

-- Writes default to service_role only; no insert/update policies for anon.
