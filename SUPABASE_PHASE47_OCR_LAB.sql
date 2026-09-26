-- SecretariatPro · Fase 47
-- Consentimiento voluntario y recogida privada de muestras OCR para OCR Lab.
-- Ejecutar UNA VEZ en Supabase > SQL Editor con permisos de propietario.
-- Requiere la Fase 35 (sp_workspaces, sp_workspace_members y helpers RLS).

begin;

create extension if not exists pgcrypto;

create table if not exists public.sp_ocr_consent (
  workspace_id uuid primary key references public.sp_workspaces(id) on delete cascade,
  enabled boolean not null default false,
  updated_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sp_ocr_samples (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.sp_workspaces(id) on delete cascade,
  uploaded_by uuid references auth.users(id) on delete set null,
  field text not null check (field in ('team1_score','time','team2_score','unknown')),
  predicted_value text not null default '',
  confidence double precision not null default 0 check (confidence >= 0 and confidence <= 1),
  raw_text text not null default '',
  ocr_pass text not null default '',
  model_name text not null default '',
  model_custom boolean not null default false,
  app_release text not null default '',
  storage_path text not null,
  image_sha256 text not null,
  image_width integer not null default 0 check (image_width >= 0),
  image_height integer not null default 0 check (image_height >= 0),
  status text not null default 'pending' check (status in ('pending','accepted','rejected')),
  label text,
  reviewer_note text not null default '',
  reviewed_at timestamptz,
  reviewed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists sp_ocr_samples_dedupe_idx
on public.sp_ocr_samples(workspace_id, field, image_sha256, model_name);
create index if not exists sp_ocr_samples_review_idx
on public.sp_ocr_samples(status, created_at);
create index if not exists sp_ocr_samples_workspace_idx
on public.sp_ocr_samples(workspace_id, created_at desc);

create or replace function public.sp_ocr_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists sp_ocr_consent_updated_at on public.sp_ocr_consent;
create trigger sp_ocr_consent_updated_at before update on public.sp_ocr_consent
for each row execute function public.sp_ocr_set_updated_at();

drop trigger if exists sp_ocr_samples_updated_at on public.sp_ocr_samples;
create trigger sp_ocr_samples_updated_at before update on public.sp_ocr_samples
for each row execute function public.sp_ocr_set_updated_at();

alter table public.sp_ocr_consent enable row level security;
alter table public.sp_ocr_samples enable row level security;

-- Cualquier miembro activo puede consultar si su workspace comparte o no.
drop policy if exists sp_ocr_consent_read on public.sp_ocr_consent;
create policy sp_ocr_consent_read
on public.sp_ocr_consent for select
to authenticated
using (public.sp_is_workspace_member(workspace_id));

-- Sólo propietario / gestor de competición puede cambiar la decisión.
drop policy if exists sp_ocr_consent_insert on public.sp_ocr_consent;
create policy sp_ocr_consent_insert
on public.sp_ocr_consent for insert
to authenticated
with check (
  public.sp_has_workspace_role(workspace_id, array['owner','competition_manager'])
  and updated_by = auth.uid()
);

drop policy if exists sp_ocr_consent_update on public.sp_ocr_consent;
create policy sp_ocr_consent_update
on public.sp_ocr_consent for update
to authenticated
using (public.sp_has_workspace_role(workspace_id, array['owner','competition_manager']))
with check (
  public.sp_has_workspace_role(workspace_id, array['owner','competition_manager'])
  and updated_by = auth.uid()
);

-- La aplicación comercial sólo puede INSERTAR una muestra cuando existe
-- consentimiento activo. No hay políticas SELECT/UPDATE/DELETE para usuarios:
-- las muestras sólo son accesibles desde OCR Lab mediante service role.
drop policy if exists sp_ocr_samples_opt_in_insert on public.sp_ocr_samples;
create policy sp_ocr_samples_opt_in_insert
on public.sp_ocr_samples for insert
to authenticated
with check (
  public.sp_is_workspace_member(workspace_id)
  and uploaded_by = auth.uid()
  and exists (
    select 1 from public.sp_ocr_consent c
    where c.workspace_id = sp_ocr_samples.workspace_id
      and c.enabled is true
  )
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'ocr-training-samples',
  'ocr-training-samples',
  false,
  524288,
  array['image/jpeg']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create or replace function public.sp_ocr_object_workspace_id(object_name text)
returns uuid
language plpgsql
immutable
as $$
begin
  return split_part(object_name, '/', 1)::uuid;
exception when others then
  return null;
end;
$$;

grant execute on function public.sp_ocr_object_workspace_id(text) to authenticated;

-- El cliente puede subir sólo dentro de la carpeta de su workspace y sólo con
-- consentimiento vigente. No existe política de lectura del bucket para clientes.
drop policy if exists ocr_training_samples_opt_in_insert on storage.objects;
create policy ocr_training_samples_opt_in_insert
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'ocr-training-samples'
  and public.sp_is_workspace_member(public.sp_ocr_object_workspace_id(name))
  and exists (
    select 1 from public.sp_ocr_consent c
    where c.workspace_id = public.sp_ocr_object_workspace_id(name)
      and c.enabled is true
  )
);

commit;
notify pgrst, 'reload schema';
