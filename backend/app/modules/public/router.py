from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from app.core.database import DbSession
from app.core.schemas import ErrorResponse
from app.modules.public.repository import PublicCatalogRepository
from app.modules.public.schemas import PublicCatalog, PublicOrderCreate, PublicOrderReceipt
from app.modules.public.service import PublicCatalogService
from app.modules.public.order_service import PublicOrderService
from app.modules.stores.schemas import SLUG_PATTERN
from app.core.config import Settings
from app.modules.billing.dependencies import current_local_date

router = APIRouter(prefix="/public", tags=["public"])


def get_public_catalog_service(session: DbSession, request: Request) -> PublicCatalogService:
    settings: Settings = request.app.state.settings
    return PublicCatalogService(
        PublicCatalogRepository(session),
        current_local_date(request),
        settings.billing_grace_days,
    )


@router.get(
    "/stores/{slug}",
    response_model=PublicCatalog,
    summary="Catálogo público de una tienda (sin autenticación)",
    responses={404: {"model": ErrorResponse}},
)
async def get_public_catalog(
    slug: Annotated[str, Path(min_length=3, max_length=63, pattern=SLUG_PATTERN)],
    response: Response,
    service: Annotated[PublicCatalogService, Depends(get_public_catalog_service)],
) -> PublicCatalog:
    # Cacheable por CDN/navegador: la mayoría de las visitas ni siquiera llegan a la base de datos.
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return await service.get_catalog(slug)


@router.post(
    "/stores/{slug}/orders",
    response_model=PublicOrderReceipt,
    status_code=201,
    summary="Registrar un pedido y preparar el mensaje de WhatsApp para que el cliente lo envíe",
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def create_public_order(
    slug: Annotated[str, Path(min_length=3, max_length=63, pattern=SLUG_PATTERN)],
    payload: PublicOrderCreate,
    session: DbSession,
    request: Request,
) -> PublicOrderReceipt:
    settings: Settings = request.app.state.settings
    service = PublicOrderService(
        PublicCatalogRepository(session), current_local_date(request), settings.billing_grace_days,
    )
    return await service.submit(slug, payload)
