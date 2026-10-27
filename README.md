# Catálogos S.A.S.

Plataforma SaaS para que vendedores creen catálogos públicos y reciban pedidos. El repositorio agrupa API y aplicación web en carpetas separadas.

## Estructura

- `backend/`: API FastAPI, modelos SQLAlchemy, configuración y scripts SQL de Supabase.
- `frontend/`: aplicación React + Vite + Tailwind.

## Inicio local

1. Configura las variables de entorno usando `backend/.env.example` y `frontend/.env.example`. No subas archivos `.env` reales.
2. Instala y ejecuta la API desde `backend/`:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
3. Instala y ejecuta el frontend desde `frontend/`:
   ```powershell
   npm ci
   npm run dev
   ```

## CORS y despliegue

En desarrollo, el frontend local usa `http://localhost:5173`. En producción, configura `CORS_ORIGINS` en el backend con el origen HTTPS exacto donde se publica el frontend (sin ruta, consulta ni `*`). Configura `VITE_API_URL` en el frontend con la URL pública de la API y reconstruye el frontend después de cambiarla.

Las plantillas `.env.example` contienen nombres y valores de ejemplo solamente. Mantén las credenciales reales fuera de GitHub; nunca uses una clave `service_role` ni secretos en variables `VITE_`.

Consulta los README de `backend/` y `frontend/` para detalles de configuración, Supabase y despliegue.
