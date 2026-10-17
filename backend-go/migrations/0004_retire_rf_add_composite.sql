-- =====================================================================
-- Retire the Random Forest. Replace with the composite CDI classifier.
-- =====================================================================

-- 1. Drop RF columns from the master table (if the earlier migration ran).
alter table master_row drop column if exists rf_drought_class;
alter table master_row drop column if exists rf_confidence;
alter table master_row drop column if exists model_version;

-- 2. Add village column (nullable at tehsil-only rows), composite class,
--    component contributions (JSON), and the formula-version string.
alter table master_row add column if not exists village text;
alter table master_row add column if not exists vci  double precision;
alter table master_row add column if not exists composite_drought_score   double precision;
alter table master_row add column if not exists composite_drought_class   text;
alter table master_row add column if not exists component_contributions   jsonb;
alter table master_row add column if not exists composite_formula_version text;

-- 3. Rename total_tehsil_area_km2 -> total_polygon_area_km2 (idempotent).
do $$
begin
  if exists (select 1 from information_schema.columns
             where table_name = 'master_row' and column_name = 'total_tehsil_area_km2') then
    alter table master_row rename column total_tehsil_area_km2 to total_polygon_area_km2;
  end if;
end$$;

-- 4. Uniqueness now includes village (nullable).
alter table master_row drop constraint if exists master_row_tehsil_observation_period_key;
create unique index if not exists master_row_unique_period_polygon
    on master_row (tehsil, coalesce(village, ''), observation_period);
