-- Perfil público de marca por catálogo.
-- La imagen reside en Supabase Storage; la tabla solo guarda ruta y URL pública.
ALTER TABLE public.stores
    ADD COLUMN IF NOT EXISTS brand_image_path varchar(500),
    ADD COLUMN IF NOT EXISTS brand_image_url varchar(1000);
