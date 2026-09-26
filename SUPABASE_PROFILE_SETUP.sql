-- SecretariatPro Phase 34
-- Ejecutar una sola vez en Supabase > SQL Editor.
-- Crea el bucket público de avatares y limita cada usuario a su propia carpeta.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'avatars',
  'avatars',
  true,
  8388608,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "SecretariatPro avatars select own" on storage.objects;
create policy "SecretariatPro avatars select own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "SecretariatPro avatars insert own" on storage.objects;
create policy "SecretariatPro avatars insert own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "SecretariatPro avatars update own" on storage.objects;
create policy "SecretariatPro avatars update own"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
)
with check (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

drop policy if exists "SecretariatPro avatars delete own" on storage.objects;
create policy "SecretariatPro avatars delete own"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'avatars'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);
