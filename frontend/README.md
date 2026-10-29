# Catálogos SaaS — Frontend

Aplicación React, Vite y TypeScript para vendedores y visitantes. Los vendedores administran sus catálogos, productos, pedidos, perfil, suscripción y soporte. Los compradores consultan un catálogo público sin iniciar sesión.

## Desarrollo local

1. Requiere Node.js 20 o superior.
2. Copia `.env.example` a `.env.local` y completa las variables.
3. Instala dependencias: `npm ci`.
4. Inicia Vite: `npm run dev` (normalmente `http://localhost:5173`).
5. Compila para producción: `npm run build`.

`VITE_API_URL` debe apuntar al backend; en local normalmente es `http://localhost:8000`. `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` son la URL y clave pública anon del proyecto Supabase. La clave anon es visible en el navegador por diseño y debe estar respaldada por RLS y las políticas configuradas en Supabase. Nunca pongas en variables `VITE_` una service role key, contraseña, token privado o `DATABASE_URL`: Vite los compila dentro de los archivos públicos.

Las variables `VITE_PRIVACY_CONTROLLER_*` se muestran en el aviso legal; son datos de identificación/contacto que el responsable decidió publicar, no secretos. Completa también la versión y criterio de conservación para que coincidan con la configuración del backend.

## CORS y publicación

GitHub almacena el código y no es el origen de las solicitudes del navegador. Para el monorepo actual, configura Vercel con Root Directory `frontend` (build `npm run build`, output `dist`) y Render con Root Directory `backend` (build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`). Para producción:

1. Este repositorio es un monorepo: en Vercel usa `frontend` como Root Directory y en Render usa `backend`.
2. Define primero el dominio estable del frontend en su hosting (por ejemplo, Vercel o Netlify).
3. En el backend, configura `CORS_ORIGINS` con ese origen exacto HTTPS, sin ruta ni barra final. Ejemplo: `CORS_ORIGINS=https://catalogos.example.com`. Para desarrollo local usa `http://localhost:5173` solo en el `.env` local.
4. Publica el backend y obtén su URL pública HTTPS.
5. Configura `VITE_API_URL` con la URL del backend, además de las variables públicas de Supabase y privacidad, y vuelve a compilar/desplegar el frontend.
6. En Supabase Auth, agrega el dominio final a Site URL/Redirect URLs, incluyendo `/restablecer-contrasena`.

No uses `CORS_ORIGINS=*`. El backend exige orígenes HTTPS exactos cuando `ENVIRONMENT=production` y rechaza localhost en ese modo. Para varios dominios permitidos, sepáralos por comas. Cambia el entorno del hosting, no los archivos `.env` locales versionados.

## Rutas principales

- `/`: página pública de presentación y registro.
- `/login`: acceso y creación de cuenta de vendedor.
- `/dashboard`: panel privado.
- `/catalogos` y `/catalogos/:id`: catálogos y edición de productos.
- `/suscripcion`: estado, renovaciones y solicitudes de ampliación.
- `/pedidos`: bandeja de pedidos del vendedor.
- `/guia-vendedores`: recomendaciones para operar el negocio.
- `/admin`: administración autorizada por `ADMIN_EMAILS` en el backend.
- `/c/:slug`: catálogo público compartible.
- `/aviso-de-privacidad`, `/terminos` y `/cookies`: información legal y preferencias.

## Seguridad de configuración

`.env.local` queda fuera de Git. El proyecto solo necesita la clave anon pública en el cliente; las operaciones privilegiadas y credenciales de base de datos viven en el backend. Revisa que `.env.example` no contenga datos privados antes de publicar cambios.
