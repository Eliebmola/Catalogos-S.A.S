-- ═══════════════════════════════════════════════════════════════════════════
-- Ejecutar en Supabase → SQL Editor DESPUÉS de crear las tablas (scripts/init_db.py o Alembic).
-- Defensa en profundidad: el backend ya valida propiedad; esto protege las tablas si alguien
-- las consulta directo con la anon key vía PostgREST. El rol del backend (postgres) hace
-- BYPASSRLS, por lo que estas políticas NO afectan a FastAPI.
-- ═══════════════════════════════════════════════════════════════════════════

-- 1) El perfil comparte id con auth.users y se borra en cascada si se elimina la cuenta.
alter table public.users
  add constraint fk_users_id_auth_users
  foreign key (id) references auth.users (id) on delete cascade;

-- 2) RLS activado en todas las tablas de negocio.
alter table public.users    enable row level security;
alter table public.stores   enable row level security;
alter table public.products enable row level security;

-- 3) Lectura pública SOLO de lo publicado.
create policy stores_public_read on public.stores
  for select to anon, authenticated
  using (is_published);

create policy products_public_read on public.products
  for select to anon, authenticated
  using (
    is_active and exists (
      select 1 from public.stores s where s.id = products.store_id and s.is_published
    )
  );

-- 4) El dueño gestiona lo suyo. (select auth.uid()) se evalúa una vez por consulta, no por fila.
create policy users_self_read on public.users
  for select to authenticated
  using (id = (select auth.uid()));

create policy stores_owner_all on public.stores
  for all to authenticated
  using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

create policy products_owner_all on public.products
  for all to authenticated
  using (exists (select 1 from public.stores s
                 where s.id = products.store_id and s.owner_id = (select auth.uid())))
  with check (exists (select 1 from public.stores s
                      where s.id = products.store_id and s.owner_id = (select auth.uid())));

-- 5) Bucket de imágenes: lectura pública, escritura SOLO desde el backend (service role).
--    No se crea ninguna política INSERT/UPDATE/DELETE para anon/authenticated sobre storage.objects.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('product-images', 'product-images', true, 2097152,
        array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do nothing;
