-- Optional personal fields; existing rows, permissions and RLS remain unchanged.
BEGIN;
ALTER TABLE public.players ADD COLUMN IF NOT EXISTS birth_date date;
ALTER TABLE public.players ADD COLUMN IF NOT EXISTS nationality text;
NOTIFY pgrst, 'reload schema';
COMMIT;
