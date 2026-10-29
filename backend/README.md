# Catálogos SaaS — API

Micro-SaaS de catálogos digitales / micro-landing pages para vendedores independientes (Instagram + WhatsApp).
FastAPI · SQLAlchemy 2 (async) · Supabase (PostgreSQL + Auth + Storage) · Pydantic v2.

## Arranque rápido

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # completa DATABASE_URL y SUPABASE_URL
python -m scripts.init_db       # crea tablas (solo dev; en producción: Alembic)
# Supabase → SQL Editor: ejecuta supabase/security.sql (FK a auth.users, RLS, bucket)
uvicorn app.main:create_app --factory --reload
pytest                          # pruebas locales (SQLite en memoria)
```
Documentación interactiva: http://localhost:8000/docs (deshabilitada si `ENVIRONMENT=production`).

## Capas (regla de dependencia: router → service → repository)

| Capa | Responsabilidad | Prohibido |
|---|---|---|
| `router.py` | HTTP: parsear, autenticar, devolver schema | lógica de negocio, SQL |
| `service.py` | Reglas de negocio, autorización por propiedad, **commit** | `HTTPException`, SQL directo |
| `repository.py` | Consultas SQLAlchemy, `flush` | commit, reglas de negocio |
| `schemas.py` | Contrato Pydantic (entrada saneada / salida mínima) | exponer modelos ORM |
| `dependencies.py` | Composition root: cablea implementaciones (DI de FastAPI) | — |

## Endpoints

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/api/v1/stores` | JWT | Crear tienda |
| GET | `/api/v1/stores` | JWT | Mis tiendas |
| PATCH | `/api/v1/stores/{store_id}/publication` | JWT + dueño | Publicar catálogo o dejarlo como borrador |
| GET | `/api/v1/stores/{store_id}/products` | JWT + dueño | Listar productos propios |
| POST | `/api/v1/stores/{store_id}/products` | JWT + dueño | Crear producto |
| PATCH | `/api/v1/stores/{store_id}/products/{product_id}` | JWT + dueño | Editar nombre, descripción, precio o visibilidad |
| POST | `/api/v1/stores/{store_id}/products/{product_id}/image` | JWT + dueño | Subir imagen (JPEG/PNG/WebP, máximo 2 MiB) |
| DELETE | `/api/v1/stores/{store_id}/products/{product_id}/image` | JWT + dueño | Eliminar archivo de Storage y limpiar sus referencias en la base de datos |
| DELETE | `/api/v1/stores/{store_id}/products/{product_id}` | JWT + dueño | Eliminar producto y archivo asociado |
| GET | `/api/v1/public/stores/{slug}` | — | Landing pública (2 queries, cacheable) |
| GET | `/api/v1/admin/subscriptions` | JWT + `ADMIN_EMAILS` | Revisar cuentas y estado |
| POST/PATCH | `/api/v1/admin/subscriptions/{owner_id}/...` | JWT + `ADMIN_EMAILS` | Registrar pago, bloquear/desbloquear y actualizar WhatsApp |

## Formato de error (todas las respuestas)
```json
{ "error": "La tienda no existe.", "code": 404, "type": "resource_not_found", "details": null }
```
`details` solo aparece en errores de validación (lista de `{field, message}`).

## Decisiones de seguridad clave
- JWT verificado **localmente** (JWKS ES256/RS256, o HS256 legacy), lista cerrada de algoritmos, `aud`/`iss`/`exp` obligatorios.
- Autorización por **propiedad en backend** + RLS en BD como segunda barrera.
- `extra="forbid"` en entradas (anti mass-assignment), saneo de HTML/caracteres invisibles, `Decimal` para dinero.
- Sin secretos en código; `Settings` falla al arrancar si `DEBUG=true` o CORS `*` en producción.
- Sin trazas al cliente; `/docs` y `/openapi.json` apagados en producción.

## Estado y pendientes principales

Ya están disponibles la gestión de catálogos, productos e imágenes, categorías, tienda pública con búsqueda y carrito, consentimiento de privacidad, control manual de suscripciones y la mensajería interna vendedor-administrador.

Pendiente: conexión real con SMTP y WhatsApp para avisos automáticos; limitar abuso de forma distribuida en el proxy/WAF de producción; automatizar CI/CD. El backend se encuentra desplegado en Render y el frontend en Vercel. Los pedidos ya se guardan en la bandeja del vendedor. La suscripción aplica una prueba de seis días, dos catálogos incluidos por $15.000 COP/mes y $5.000 COP/mes por cada catálogo extra aprobado manualmente por administración. Tras el vencimiento hay dos días de gracia; luego se oculta el catálogo público hasta registrar la renovación.

## Suscripciones manuales y nuevas tablas

El backend mantiene la suscripción por propietario. Al vencer `paid_through`, la cuenta conserva acceso durante los dos días de gracia; después, los catálogos públicos y la creación de productos se suspenden. Registrar un pago desde el panel renueva un mes desde el día del registro. No hay cobros dentro de la plataforma. Bloquear/desbloquear afecta los catálogos de la cuenta completa.

El periodo de prueba inicia cuando la persona entra por primera vez al panel con su cuenta. En la página Suscripción puede solicitar renovación o ampliación; ambas solicitudes abren WhatsApp y no procesan pagos. Configura BILLING_WHATSAPP_NUMBER en el .env del backend para habilitar esos enlaces. Administración registra los pagos y define el número de catálogos extra permitidos desde su panel. La renovación tardía inicia el nuevo mes desde la fecha en que administración registra el pago.

Para autorizar el panel, registra la cuenta administradora en Supabase Auth y añade su correo a `ADMIN_EMAILS` en el `.env` del backend. El usuario inicia sesión con Supabase; las contraseñas no se guardan en este proyecto.

Después de crear las tablas base y aplicar `supabase/security.sql`, ejecuta una vez `supabase/billing_and_storage.sql`. Las cuentas que ya existían conservan acceso durante la transición; el administrador registra su primer vencimiento/pago desde el panel.

## Controles de abuso y límites HTTP

El backend limita por IP las consultas públicas de catálogo a 120 por minuto y los pedidos públicos a 8 por minuto por proceso. La tabla de límites vive en memoria del proceso: en despliegues con varios workers cada worker mantiene su propio contador. Configura también límites equivalentes o más estrictos en el proxy/WAF (por ejemplo, Cloudflare), y configura Uvicorn para confiar las cabeceras de IP únicamente del proxy conocido; no confíes directamente en `X-Forwarded-For` de cualquier cliente. El backend rechaza solicitudes que declaren un cuerpo mayor de 4 MiB; las imágenes además se limitan a 2 MiB. El proxy debe imponer un límite de cuerpo y tiempo de lectura para cubrir solicitudes HTTP fragmentadas o sin `Content-Length`.

En producción, FastAPI envía HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Permissions-Policy`. La política CSP debe configurarse en el hosting que sirve el frontend, ajustada al dominio real de Supabase, API y fuentes; el proyecto no fija proveedor de hosting ni sus dominios.

El frontend incluye aviso y preferencias para almacenamiento/cookies. Actualmente solo recuerda la elección con una cookie técnica y usa almacenamiento local para sesión de Supabase e idioma; no hay cookies de analítica o publicidad activas. Consulta `/cookies` en la aplicación.

## GitHub y despliegue

El `.gitignore` excluye los archivos `.env*` reales, entornos virtuales, cachés y archivos locales del editor; solo se versiona `.env.example`. Nunca subas la service role key, `DATABASE_URL`, contraseñas, tokens ni datos privados. La URL del proyecto de Supabase en la plantilla es un marcador y debe configurarse en el entorno del hosting.

En desarrollo, `CORS_ORIGINS` puede ser `http://localhost:5173`. En producción, configura en el hosting del backend únicamente los orígenes HTTPS exactos desde los que se sirve el frontend, por ejemplo `https://catalogos.example.com` (sin ruta ni barra final). Se permiten varios orígenes separados por comas. FastAPI rechaza wildcard, HTTP y localhost cuando `ENVIRONMENT=production`.

El repositorio GitHub almacena código; no define el origen CORS. Primero define/despliega el frontend para obtener su URL estable; después configura `CORS_ORIGINS` en el backend con esa URL y publica el backend. Luego configura `VITE_API_URL` del frontend con la URL pública del backend y vuelve a desplegarlo. Para dominios personalizados, agrega el origen HTTPS final y actualiza la configuración.

## Aviso de privacidad y consentimiento

Antes de desplegar el frontend que exige consentimiento, ejecuta `supabase/privacy_consent.sql` en Supabase SQL Editor y configura `PRIVACY_POLICY_VERSION` en el `.env` del backend. Debe coincidir con `VITE_PRIVACY_POLICY_VERSION` del frontend y con la versión fijada en el trigger de ese SQL. Las cuentas existentes deberán aceptar la política vigente al iniciar sesión; no se les atribuye consentimiento retroactivo. El registro nuevo requiere la marca de aceptación enviada a Supabase Auth y el trigger la registra con la hora del servidor.

El responsable debe completar en el `.env.local` del frontend nombre/razón social, identificación si aplica, dirección, correo, teléfono y criterio de conservación. El flujo no permite nuevos registros ni el acceso privado mientras falte información obligatoria. El texto es un borrador funcional: el responsable debe verificarlo y confirmar el tratamiento, los proveedores, transferencias y plazos reales antes de producción.

Las imágenes aceptan JPEG, PNG y WebP hasta 2 MiB. La subida se hace desde el backend con `SUPABASE_SERVICE_ROLE_KEY`; esta clave nunca debe aparecer en el frontend.

## Configuración de SMTP y WhatsApp

Todas las credenciales de proveedores van en `C:\Catalogos saas\.env`, en el backend. `C:\Catalogos saas\.env.example` es solo una guía; no pegues secretos en el frontend ni publiques el `.env`. Después de editar el archivo, reinicia FastAPI.

Para SMTP, solicita a tu proveedor de correo el host, puerto, usuario, contraseña SMTP o contraseña de aplicación, y la dirección remitente verificada:

- `SMTP_HOST`: servidor saliente del proveedor.
- `SMTP_PORT=587` y `SMTP_USE_SSL=false`: conexión STARTTLS, configuración usual.
- `SMTP_PORT=465` y `SMTP_USE_SSL=true`: conexión SSL directa, si así lo indica el proveedor.
- `SMTP_USERNAME` y `SMTP_PASSWORD`: credenciales SMTP; no uses la contraseña normal de tu correo si el proveedor requiere una contraseña de aplicación.
- `SMTP_FROM_EMAIL`: dirección verificada que aparecerá como remitente.

El backend implementa avisos por correo, pero no verifica las credenciales al guardar la configuración. Los avisos de vencimiento y suspensión solo se intentan cuando se programa `python -m scripts.run_billing_notifications` una vez al día, por ejemplo desde el Programador de tareas de Windows.

WhatsApp tiene dos plantillas distintas en Meta WhatsApp Business Platform:

- `WHATSAPP_TEMPLATE_NAME`: aviso de suscripción aprobado, con `{{1}}` para el nombre del vendedor y `{{2}}` para el aviso.
- `WHATSAPP_ORDER_TEMPLATE_NAME`: pedido aprobado, con `{{1}}` para el detalle del pedido.
- `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_GRAPH_API_VERSION`: datos de la aplicación y número emisor de Meta.
- `WHATSAPP_TEMPLATE_LANGUAGE=es_CO`: debe coincidir con el idioma aprobado de la plantilla.

Para pedidos, cada vendedor además debe guardar su número en su perfil y autorizar la recepción automática. El token y los ID de Meta pertenecen al backend; no son los números personales de los vendedores. Sin las credenciales y plantillas aprobadas no se envían mensajes. El panel administrativo solo indica si hay configuración suficiente; no hace una prueba de entrega.

El aviso de pago y los pedidos usan el mismo remitente de WhatsApp, pero plantillas separadas. El envío de avisos de suscripción requiere además el job diario; los pedidos se intentan al confirmar el pedido en el catálogo público.
