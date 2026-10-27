import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import app.db.registry  # noqa: F401  (registra todos los modelos antes de la primera consulta)
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine, create_session_factory
from app.core.error_handlers import register_exception_handlers
from app.core.security import SupabaseJWTVerifier
from app.core.traffic import InMemoryRateLimiter, RequestBodyLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = build_engine(app.state.settings)
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        # En producción no se publica la documentación interactiva ni el esquema OpenAPI.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.jwt_verifier = SupabaseJWTVerifier(settings)
    app.state.public_rate_limiter = InMemoryRateLimiter()

    # CORS cerrado: orígenes explícitos, sin cookies (la auth va por header Authorization).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        prefix = f"{settings.api_v1_prefix}/public/stores/"
        if path.startswith(prefix):
            client_ip = request.client.host if request.client else "unknown"
            if request.method == "POST" and path.endswith("/orders"):
                limit, rule = 8, "public-order"
            elif request.method == "GET" and "/orders" not in path:
                limit, rule = 120, "public-catalog"
            else:
                limit, rule = None, ""
            if limit is not None:
                allowed, retry_after = await request.app.state.public_rate_limiter.allow(
                    f"{rule}:{client_ip}", limit=limit, window_seconds=60
                )
                if not allowed:
                    return Response(
                        content='{"error":"Demasiadas solicitudes. Intenta de nuevo en un minuto.","code":429,"type":"rate_limit"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": str(retry_after)},
                    )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    register_exception_handlers(app, settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


# Instancia global para que Uvicorn la detecte sin el flag --factory.
# Este CORS exterior también añade sus cabeceras a respuestas 500 creadas por
# ServerErrorMiddleware, que de otro modo queda por fuera del middleware interno.
_fastapi_app = create_app()
app = CORSMiddleware(
    RequestBodyLimitMiddleware(_fastapi_app),
    allow_origins=_fastapi_app.state.settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)
