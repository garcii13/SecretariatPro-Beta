BEGIN;
CREATE TABLE IF NOT EXISTS public.sp_roster_groups (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 workspace_id uuid NOT NULL REFERENCES public.sp_workspaces(id) ON DELETE CASCADE,
 competition_id uuid NOT NULL REFERENCES public.competitions(id) ON DELETE CASCADE,
 team_id uuid NOT NULL REFERENCES public.teams(id) ON DELETE CASCADE,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workspace_id,competition_id,team_id)
);
ALTER TABLE public.sp_roster_groups ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
 CREATE POLICY roster_groups_read ON public.sp_roster_groups FOR SELECT TO authenticated USING (public.sp_is_workspace_member(workspace_id));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
 CREATE POLICY roster_groups_manage ON public.sp_roster_groups FOR ALL TO authenticated
 USING (public.sp_has_workspace_role(workspace_id, ARRAY['owner','competition_manager']))
 WITH CHECK (public.sp_has_workspace_role(workspace_id, ARRAY['owner','competition_manager'])
 AND EXISTS (SELECT 1 FROM public.teams t WHERE t.id=team_id AND t.workspace_id=sp_roster_groups.workspace_id)
 AND EXISTS (SELECT 1 FROM public.competitions c WHERE c.id=competition_id AND c.workspace_id=sp_roster_groups.workspace_id));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.sp_roster_groups TO authenticated;
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS time_confirmed boolean NOT NULL DEFAULT true;
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS scheduled_date date;
NOTIFY pgrst, 'reload schema';
COMMIT;
