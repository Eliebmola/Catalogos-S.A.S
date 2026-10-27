CREATE TABLE IF NOT EXISTS public.product_categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id uuid NOT NULL REFERENCES public.stores(id) ON DELETE CASCADE,
    name varchar(80) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_product_categories_store_name UNIQUE (store_id, name)
);
CREATE INDEX IF NOT EXISTS ix_product_categories_store_id
    ON public.product_categories(store_id);
ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS category_id uuid NULL
        REFERENCES public.product_categories(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_products_category_id ON public.products(category_id);
