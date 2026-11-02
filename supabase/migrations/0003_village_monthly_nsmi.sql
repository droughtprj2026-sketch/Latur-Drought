-- cdi-v2026.12: NSMI (Sentinel-2 SWIR soil moisture) is a composite input and is now published per village-month;
-- PCI (a precipitation min-max index that duplicated SPI) is no longer computed or published.
--
-- Run once in the Supabase SQL editor BEFORE the next pipeline publish (the publisher sends `nsmi`;
-- PostgREST rejects a column that does not exist, which fails the run on purpose).
--
-- The `pci` column is left in place: old rows keep their value, new rows leave it NULL. Drop it later with
--   ALTER TABLE public.village_monthly DROP COLUMN pci;
-- once nothing reads it.
BEGIN;

ALTER TABLE public.village_monthly ADD COLUMN IF NOT EXISTS nsmi NUMERIC(7, 4);
COMMENT ON COLUMN public.village_monthly.nsmi IS 'Normalised soil moisture index, Sentinel-2 SWIR B11-B12 (composite input from cdi-v2026.12)';
COMMENT ON COLUMN public.village_monthly.pci IS 'RETIRED in cdi-v2026.12: no longer computed or published';

COMMIT;
