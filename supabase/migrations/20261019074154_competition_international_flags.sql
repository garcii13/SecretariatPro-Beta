-- Competition metadata owns international mode; team flags remain separate from crests.
alter table public.competitions add column if not exists is_international boolean;
alter table public.teams add column if not exists flag_url text;

-- Preserve the effective published identity, scoped to the same workspace.
-- Only NULL rows are migrated; a later explicit choice of false is never reversed.
update public.competitions c
set is_international = coalesce((
  select coalesce(t.config #> '{appearance,team_identity,international}',
                  t.config #> '{team_identity,international}', 'false'::jsonb) = 'true'::jsonb
  from public.sp_visual_themes t
  where t.workspace_id = c.workspace_id and t.published
    and (t.competition_id = c.id or t.competition_id is null)
  order by (t.competition_id is not null) desc, t.version desc, t.updated_at desc, t.id
  limit 1
), false)
where c.is_international is null;

alter table public.competitions alter column is_international set default false;
alter table public.competitions alter column is_international set not null;

-- Copy existing attachments without deleting the historical theme or changing a crest.
with legacy_flags as (
  select distinct on (team.id) team.id, flags.value as url
  from public.teams team
  join public.sp_visual_themes t on t.workspace_id = team.workspace_id
  cross join lateral jsonb_each_text(case
    when jsonb_typeof(t.config #> '{appearance,team_identity,flags}') = 'object'
      then t.config #> '{appearance,team_identity,flags}'
    when jsonb_typeof(t.config #> '{team_identity,flags}') = 'object'
      then t.config #> '{team_identity,flags}'
    else '{}'::jsonb end) flags
  where flags.key = team.id::text and flags.value ~ '^https?://[^/[:space:]]+'
    and length(flags.value) <= 4096
  order by team.id, t.published desc, t.updated_at desc, t.version desc, t.id
)
update public.teams team set flag_url = legacy_flags.url
from legacy_flags where team.id = legacy_flags.id and team.flag_url is null;

-- Existing grants, restrictive tenant guards and role policies still apply.
notify pgrst, 'reload schema';
