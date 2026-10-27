ALTER TABLE public.stores
    ADD COLUMN IF NOT EXISTS whatsapp_orders_opt_in boolean NOT NULL DEFAULT false;
