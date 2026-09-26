-- Apply after the existing multi-tenant migrations, before distributing beta.1.
-- RLS already restricts writes to owner/competition_manager. This trigger also
-- enforces the paid workspace scope when clients call Supabase directly.
begin;
create or replace function public.sp_validate_visual_scope()
returns trigger language plpgsql set search_path = public as $$
begin
  if new.competition_id is not null then
    if not exists (select 1 from public.sp_workspaces w
                   where w.id = new.workspace_id and w.visual_identity_mode = 'competition') then
      raise exception 'La cuenta no permite identidades por competición';
    end if;
    if not exists (select 1 from public.competitions c
                   where c.id = new.competition_id and c.workspace_id = new.workspace_id) then
      raise exception 'La competición no pertenece al espacio';
    end if;
  end if;
  new.locked := true;
  return new;
end;
$$;
drop trigger if exists sp_visual_scope_guard on public.sp_visual_themes;
create trigger sp_visual_scope_guard before insert or update on public.sp_visual_themes
for each row execute function public.sp_validate_visual_scope();
commit;
