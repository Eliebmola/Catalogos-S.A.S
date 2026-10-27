-- Ejecutar una sola vez en Supabase SQL Editor después de las tablas base y security.sql.
-- Las cuentas ya existentes conservan acceso hasta su primera renovación manual.
create table if not exists public.subscriptions (
  owner_id uuid primary key references public.users(id) on delete cascade,
  paid_through date,
  trial_until date,
  extra_catalogs integer not null default 0 check (extra_catalogs >= 0),
  whatsapp_number varchar(16),
  access_override boolean,
  legacy_grandfathered boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_subscriptions_whatsapp_e164
    check (whatsapp_number is null or whatsapp_number ~ '^\+[1-9][0-9]{7,14}$')
);

-- Actualiza instalaciones que ya tenían el esquema inicial de suscripciones.
alter table public.subscriptions add column if not exists trial_until date;
alter table public.subscriptions add column if not exists extra_catalogs integer not null default 0;
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'subscriptions_extra_catalogs_nonnegative') then
    alter table public.subscriptions add constraint subscriptions_extra_catalogs_nonnegative check (extra_catalogs >= 0);
  end if;
end $$;

insert into public.subscriptions (owner_id, access_override, legacy_grandfathered)
select id, false, true from public.users
on conflict (owner_id) do nothing;

create table if not exists public.billing_notifications (
  id bigserial primary key,
  owner_id uuid not null references public.users(id) on delete cascade,
  period_end date not null,
  kind varchar(24) not null check (kind in ('due', 'suspended')),
  channel varchar(16) not null check (channel in ('email', 'whatsapp')),
  status varchar(16) not null check (status in ('sent', 'failed', 'skipped')),
  attempts integer not null default 1,
  sent_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_billing_notification_period unique (owner_id, period_end, kind, channel)
);
create index if not exists ix_billing_notifications_status
  on public.billing_notifications(status, created_at);

create table if not exists public.billing_payments (
  id bigserial primary key,
  owner_id uuid not null references public.users(id) on delete cascade,
  recorded_by_email varchar(320) not null,
  paid_at timestamptz not null default now(),
  paid_through date not null,
  created_at timestamptz not null default now()
);
create index if not exists ix_billing_payments_owner_paid_at
  on public.billing_payments(owner_id, paid_at);

alter table public.subscriptions enable row level security;
alter table public.billing_notifications enable row level security;
alter table public.billing_payments enable row level security;
-- No policies for anon/authenticated: only the FastAPI service role may read or write billing data.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('product-images', 'product-images', true, 2097152,
        array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
set file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
