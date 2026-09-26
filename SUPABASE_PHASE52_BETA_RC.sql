-- SecretariatPro Phase 52 / Beta RC
-- 1) Matches can be administrative-only (not exposed to Live).
-- 2) Workspace owner selects sport mode (floorball / handball).
-- Run once in Supabase SQL Editor.

begin;

alter table public.matches
  add column if not exists broadcast_enabled boolean not null default true;

comment on column public.matches.broadcast_enabled is
  'When false the match is maintained in Manager for results/events/statistics but is never offered as an operable Live match.';

alter table public.sp_workspaces
  add column if not exists sport_mode text not null default 'floorball';

alter table public.sp_workspaces
  drop constraint if exists sp_workspaces_sport_mode_check;

alter table public.sp_workspaces
  add constraint sp_workspaces_sport_mode_check
  check (sport_mode in ('floorball','handball'));

comment on column public.sp_workspaces.sport_mode is
  'Sport ruleset selected by the workspace owner. Producers receive it read-only in SecretariatPro Live.';

create index if not exists sp_matches_broadcast_idx
  on public.matches(workspace_id, competition_id, broadcast_enabled, match_date);

commit;
