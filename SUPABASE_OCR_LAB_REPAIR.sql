-- SecretariatPro OCR Lab · RLS/RPC FIX V3
-- Soluciona definitivamente el error 42501 sin conceder SELECT a clientes.
-- Ejecutar en Supabase > SQL Editor con el propietario del proyecto/postgres.
-- Idempotente: no borra muestras existentes.

begin;

-- 1) Helper autoritativo de autorización.
create or replace function public.sp_can_submit_ocr_sample(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select
    auth.uid() is not null
    and exists (
      select 1
      from public.sp_workspace_members m
      where m.workspace_id = target_workspace
        and m.user_id = auth.uid()
        and m.status = 'active'
    )
    and exists (
      select 1
      from public.sp_ocr_consent c
      where c.workspace_id = target_workspace
        and c.enabled is true
    );
$$;
revoke all on function public.sp_can_submit_ocr_sample(uuid) from public;
grant execute on function public.sp_can_submit_ocr_sample(uuid) to authenticated, service_role;

-- 2) RPC única de escritura de metadatos.
--    El cliente no necesita SELECT ni INSERT directo sobre sp_ocr_samples.
create or replace function public.sp_submit_ocr_sample(
  p_workspace_id uuid,
  p_field text,
  p_predicted_value text,
  p_confidence double precision,
  p_raw_text text,
  p_ocr_pass text,
  p_model_name text,
  p_model_custom boolean,
  p_app_release text,
  p_storage_path text,
  p_image_sha256 text,
  p_image_width integer,
  p_image_height integer
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  new_id uuid;
begin
  if auth.uid() is null then
    raise exception 'OCR_SAMPLE_AUTH_REQUIRED' using errcode = '42501';
  end if;

  if not public.sp_can_submit_ocr_sample(p_workspace_id) then
    raise exception 'OCR_SAMPLE_NOT_ALLOWED' using errcode = '42501';
  end if;

  if coalesce(p_field, '') not in ('team1_score','team2_score','time','unknown') then
    raise exception 'OCR_SAMPLE_INVALID_FIELD' using errcode = '22023';
  end if;

  if coalesce(p_storage_path,'') = ''
     or split_part(p_storage_path, '/', 1) <> p_workspace_id::text then
    raise exception 'OCR_SAMPLE_INVALID_PATH' using errcode = '22023';
  end if;

  insert into public.sp_ocr_samples (
    workspace_id, uploaded_by, field, predicted_value, confidence,
    raw_text, ocr_pass, model_name, model_custom, app_release,
    storage_path, image_sha256, image_width, image_height, status
  ) values (
    p_workspace_id,
    auth.uid(),
    coalesce(p_field,'unknown'),
    left(coalesce(p_predicted_value,''),32),
    greatest(0.0, least(1.0, coalesce(p_confidence,0.0))),
    left(coalesce(p_raw_text,''),128),
    left(coalesce(p_ocr_pass,''),32),
    left(coalesce(p_model_name,''),128),
    coalesce(p_model_custom,false),
    left(coalesce(p_app_release,''),64),
    p_storage_path,
    left(coalesce(p_image_sha256,''),64),
    greatest(0,coalesce(p_image_width,0)),
    greatest(0,coalesce(p_image_height,0)),
    'pending'
  )
  on conflict (workspace_id, field, image_sha256, model_name)
  do update set
    updated_at = now()
  returning id into new_id;

  return new_id;
end;
$$;

revoke all on function public.sp_submit_ocr_sample(uuid,text,text,double precision,text,text,text,boolean,text,text,text,integer,integer) from public;
grant execute on function public.sp_submit_ocr_sample(uuid,text,text,double precision,text,text,text,boolean,text,text,text,integer,integer) to authenticated, service_role;

-- 3) La tabla queda cerrada a clientes: ni SELECT ni INSERT directo.
-- Compatibilidad histórica: sp_ocr_samples_opt_in_insert fue retirada.
-- Bucket debe permanecer con public = false.
alter table public.sp_ocr_samples enable row level security;
revoke all on public.sp_ocr_samples from anon;
revoke select, insert, update, delete on public.sp_ocr_samples from authenticated;
grant all on public.sp_ocr_samples to service_role;

-- Eliminamos políticas directas de INSERT antiguas para evitar ambigüedad.
drop policy if exists sp_ocr_samples_opt_in_insert on public.sp_ocr_samples;
drop policy if exists sp_ocr_samples_insert on public.sp_ocr_samples;
drop policy if exists sp_ocr_samples_submit on public.sp_ocr_samples;

-- 4) Bucket privado: el cliente sólo puede SUBIR su recorte.
create or replace function public.sp_ocr_object_workspace_id(object_name text)
returns uuid
language plpgsql
immutable
set search_path = public
as $$
begin
  return split_part(object_name, '/', 1)::uuid;
exception when others then
  return null;
end;
$$;
grant execute on function public.sp_ocr_object_workspace_id(text) to authenticated, service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('ocr-training-samples','ocr-training-samples',false,524288,array['image/jpeg'])
on conflict (id) do update set
  public=false,
  file_size_limit=524288,
  allowed_mime_types=array['image/jpeg'];

drop policy if exists ocr_training_samples_opt_in_insert on storage.objects;
drop policy if exists ocr_training_samples_insert on storage.objects;
create policy ocr_training_samples_opt_in_insert
on storage.objects
for insert
to authenticated
with check (
  bucket_id='ocr-training-samples'
  and public.sp_can_submit_ocr_sample(public.sp_ocr_object_workspace_id(name))
);

-- Permite limpiar únicamente un archivo propio si el RPC falla.
drop policy if exists ocr_training_samples_own_delete on storage.objects;
create policy ocr_training_samples_own_delete
on storage.objects
for delete
to authenticated
using (
  bucket_id='ocr-training-samples'
  and owner_id=auth.uid()::text
);

commit;
notify pgrst, 'reload schema';

-- 5) Diagnóstico: todas estas filas deben dar OK.
select 'submit RPC' as check_name,
       case when to_regprocedure('public.sp_submit_ocr_sample(uuid,text,text,double precision,text,text,text,boolean,text,text,text,integer,integer)') is not null then 'OK' else 'MISSING' end as result
union all
select 'RPC authenticated EXECUTE',
       case when has_function_privilege('authenticated','public.sp_submit_ocr_sample(uuid,text,text,double precision,text,text,text,boolean,text,text,text,integer,integer)','EXECUTE') then 'OK' else 'MISSING' end
union all
select 'authenticated table SELECT revoked',
       case when not has_table_privilege('authenticated','public.sp_ocr_samples','SELECT') then 'OK' else 'STILL GRANTED' end
union all
select 'authenticated direct INSERT revoked',
       case when not has_table_privilege('authenticated','public.sp_ocr_samples','INSERT') then 'OK' else 'STILL GRANTED' end
union all
select 'private OCR bucket',
       case when exists(select 1 from storage.buckets where id='ocr-training-samples' and public=false) then 'OK' else 'MISSING/NOT PRIVATE' end
union all
select 'storage insert policy',
       case when exists(select 1 from pg_policies where schemaname='storage' and tablename='objects' and policyname='ocr_training_samples_opt_in_insert') then 'OK' else 'MISSING' end;

-- Consentimiento actual por workspace.
select w.id as workspace_id,
       w.name as workspace_name,
       coalesce(c.enabled,false) as ocr_sharing_enabled,
       c.updated_at
from public.sp_workspaces w
left join public.sp_ocr_consent c on c.workspace_id=w.id
order by w.created_at;
