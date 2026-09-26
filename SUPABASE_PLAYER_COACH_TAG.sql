ALTER TABLE public.players ADD COLUMN IF NOT EXISTS is_coach boolean NOT NULL DEFAULT false;
NOTIFY pgrst, 'reload schema';
