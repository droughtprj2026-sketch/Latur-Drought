-- =====================================================================
-- Convenience: load Latur tehsils from a GeoJSON uploaded to the
-- Supabase SQL editor. Replace the placeholder json with your real file.
--
-- Example (one-off):
--   insert into tehsils (name, geom)
--   select
--       feat->'properties'->>'TEHSIL' as name,
--       ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(feat->'geometry'), 4326)) as geom
--   from (
--     select jsonb_array_elements(
--       '{"type":"FeatureCollection","features":[ ... ]}'::jsonb -> 'features'
--     ) as feat
--   ) t
--   on conflict (name) do update set geom = excluded.geom;
-- =====================================================================

-- Example upsert function for repeated loads:
create or replace function upsert_tehsils_from_geojson(gj jsonb)
returns integer language plpgsql as $$
declare
    inserted int;
begin
    with payload as (
        select jsonb_array_elements(gj -> 'features') as feat
    )
    insert into tehsils (name, geom)
    select coalesce(
               feat->'properties'->>'TEHSIL',
               feat->'properties'->>'name',
               feat->'properties'->>'NAME'
           ) as name,
           ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(feat->'geometry'), 4326)) as geom
    from payload
    on conflict (name) do update set geom = excluded.geom;

    get diagnostics inserted = row_count;
    return inserted;
end
$$;
