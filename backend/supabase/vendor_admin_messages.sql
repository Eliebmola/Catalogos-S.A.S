-- Bandeja interna de solicitudes de vendedores. No requiere correo ni WhatsApp.
-- Ejecutar una vez en Supabase → SQL Editor.
create table if not exists public.seller_admin_messages (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.users(id) on delete cascade,
  category varchar(32) not null check (category in ('catalog_request', 'complaint', 'technical_issue', 'other')),
  subject varchar(160) not null,
  body text not null,
  status varchar(16) not null default 'new' check (status in ('new', 'in_progress', 'resolved')),
  sender_role varchar(16) not null default 'seller' check (sender_role in ('seller', 'admin')),
  admin_read_at timestamptz,
  seller_read_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_seller_admin_messages_status_created
  on public.seller_admin_messages(status, created_at desc);
create index if not exists ix_seller_admin_messages_owner_created
  on public.seller_admin_messages(owner_id, created_at desc);

alter table public.seller_admin_messages enable row level security;
-- Idempotent upgrades for installations created with the first version of this table.
alter table public.seller_admin_messages
  add column if not exists sender_role varchar(16) not null default 'seller';
alter table public.seller_admin_messages
  add column if not exists seller_read_at timestamptz;

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'seller_admin_messages_sender_role_check') then
    alter table public.seller_admin_messages
      add constraint seller_admin_messages_sender_role_check check (sender_role in ('seller', 'admin'));
  end if;
end $$;

create table if not exists public.seller_admin_replies (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.seller_admin_messages(id) on delete cascade,
  sender_id uuid not null,
  sender_role varchar(16) not null check (sender_role in ('seller', 'admin')),
  sender_name varchar(120),
  body text not null,
  admin_read_at timestamptz,
  seller_read_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists ix_seller_admin_replies_thread_created
  on public.seller_admin_replies(message_id, created_at);
alter table public.seller_admin_replies enable row level security;
-- La identidad del remitente se valida en FastAPI con el JWT de Supabase.
-- No exigir un perfil de vendedor para que un administrador pueda responder.
alter table public.seller_admin_replies
  drop constraint if exists seller_admin_replies_sender_id_fkey;
-- Datos de identidad para que cada conversación identifique el negocio y a quien lo administra.
alter table public.seller_admin_messages
  add column if not exists store_id uuid references public.stores(id) on delete set null;
alter table public.seller_admin_messages
  add column if not exists business_name varchar(120);
alter table public.seller_admin_messages
  add column if not exists sender_name varchar(120);
alter table public.seller_admin_replies
  add column if not exists sender_name varchar(120);
-- No direct client policies: all reads/writes go through the authenticated FastAPI backend,
-- which checks the seller identity or the administrator email allowlist.
