-- Pedidos persistentes para que el vendedor los revise desde su cuenta.
-- Ejecutar una vez en Supabase → SQL Editor.
create table if not exists public.store_orders (
  id uuid primary key default gen_random_uuid(),
  order_number varchar(16) not null unique,
  store_id uuid references public.stores(id) on delete set null,
  owner_id uuid not null references public.users(id) on delete cascade,
  store_name varchar(120) not null,
  buyer_name varchar(120) not null,
  buyer_phone varchar(24) not null,
  buyer_email varchar(160),
  requires_shipping boolean not null default false,
  city varchar(100),
  neighborhood varchar(100),
  address varchar(180),
  privacy_consent_at timestamptz not null default now(),
  status varchar(16) not null default 'new'
    check (status in ('new', 'contacted', 'completed', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_store_orders_owner_created
  on public.store_orders(owner_id, created_at desc);
create index if not exists ix_store_orders_store_created
  on public.store_orders(store_id, created_at desc);

create table if not exists public.store_order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.store_orders(id) on delete cascade,
  product_id uuid not null,
  product_name varchar(150) not null,
  image_url varchar(1000),
  quantity integer not null check (quantity between 1 and 99),
  unit_price numeric(12, 2) not null check (unit_price >= 0),
  line_total numeric(14, 2) not null check (line_total >= 0),
  currency varchar(3) not null,
  created_at timestamptz not null default now()
);

create index if not exists ix_store_order_items_order_id
  on public.store_order_items(order_id);

alter table public.store_orders enable row level security;
alter table public.store_order_items enable row level security;
-- Sin políticas directas para anon/authenticated: FastAPI verifica el propietario del pedido.
