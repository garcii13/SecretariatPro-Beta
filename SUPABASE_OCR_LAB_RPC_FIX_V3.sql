-- SecretariatPro · OCR Lab RPC y deduplicación de Storage.
-- Seguro para volver a ejecutar en Supabase > SQL Editor.

begin;

create or replace function public.sp_can_submit_ocr_sample(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select auth.uid() is not null
    and exists (
      select 1 from public.sp_workspace_members m
      where m.workspace_id = target_workspace
        and m.user_id = auth.uid()
        and m.status = 'active'
    )
    and exists (
      select 1 from public.sp_ocr_consent c
      where c.workspace_id = target_workspace
        and c.enabled is true
    );
$$;

create or replace function public.sp_find_ocr_sample(
  p_workspace_id uuid,
  p_field text,
  p_image_sha256 text,
  p_model_name text
)
returns uuid
language plpgsql
stable
security definer
set search_path = public, pg_temp
as $$
declare
  sample_id uuid;
begin
  if not public.sp_can_submit_ocr_sample(p_workspace_id) then
    raise exception 'OCR_SAMPLE_NOT_ALLOWED' using errcode = '42501';
  end if;

  select s.id into sample_id
  from public.sp_ocr_samples s
  where s.workspace_id = p_workspace_id
    and s.field = p_field
    and s.image_sha256 = left(coalesce(p_image_sha256, ''), 64)
    and s.model_name = left(coalesce(p_model_name, ''), 128)
  limit 1;

  return sample_id;
end;
$$;

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
set search_path = public, pg_temp
as $$
declare
  new_id uuid;
begin
  if not public.sp_can_submit_ocr_sample(p_workspace_id) then
    raise exception 'OCR_SAMPLE_NOT_ALLOWED' using errcode = '42501';
  end if;
  if coalesce(p_field, '') not in ('team1_score','team2_score','time','unknown') then
    raise exception 'OCR_SAMPLE_INVALID_FIELD' using errcode = '22023';
  end if;
  if coalesce(p_storage_path, '') = ''
     or split_part(p_storage_path, '/', 1) <> p_workspace_id::text then
    raise exception 'OCR_SAMPLE_INVALID_PATH' using errcode = '22023';
  end if;

  insert into public.sp_ocr_samples (
    workspace_id, uploaded_by, field, predicted_value, confidence,
    raw_text, ocr_pass, model_name, model_custom, app_release,
    storage_path, image_sha256, image_width, image_height, status
  ) values (
    p_workspace_id, auth.uid(), coalesce(p_field, 'unknown'),
    left(coalesce(p_predicted_value, ''), 32),
    greatest(0.0, least(1.0, coalesce(p_confidence, 0.0))),
    left(coalesce(p_raw_text, ''), 128),
    left(coalesce(p_ocr_pass, ''), 32),
    left(coalesce(p_model_name, ''), 128),
    coalesce(p_model_custom, false),
    left(coalesce(p_app_release, ''), 64),
    p_storage_path,
    left(coalesce(p_image_sha256, ''), 64),
    greatest(0, coalesce(p_image_width, 0)),
    greatest(0, coalesce(p_image_height, 0)),
    'pending'
  )
  on conflict (workspace_id, field, image_sha256, model_name)
  do update set updated_at = now()
  returning id into new_id;

  return new_id;
end;
$$;

revoke all on function public.sp_can_submit_ocr_sample(uuid) from public, anon;
revoke all on function public.sp_find_ocr_sample(uuid, text, text, text) from public, anon;
revoke all on function public.sp_submit_ocr_sample(uuid, text, text, double precision, text, text, text, boolean, text, text, text, integer, integer) from public, anon;
grant execute on function public.sp_can_submit_ocr_sample(uuid) to authenticated;
grant execute on function public.sp_find_ocr_sample(uuid, text, text, text) to authenticated;
grant execute on function public.sp_submit_ocr_sample(uuid, text, text, double precision, text, text, text, boolean, text, text, text, integer, integer) to authenticated;

revoke select, insert, update, delete on public.sp_ocr_samples from authenticated;

commit;
notify pgrst, 'reload schema';
