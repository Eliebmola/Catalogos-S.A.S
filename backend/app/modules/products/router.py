from uuid import UUID

from fastapi import APIRouter, File, Request, Response, UploadFile, status

from app.core.schemas import ErrorResponse
from app.core.security import CurrentUser
from app.core.exceptions import BusinessRuleViolationException
from app.core.config import Settings
from app.modules.products.dependencies import ProductImageServiceDep, ProductServiceDep
from app.modules.products.schemas import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/stores/{store_id}/products", tags=["products"])


@router.get(
    "",
    response_model=list[ProductRead],
    summary="Listar los productos de una tienda propia",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def list_products(
    store_id: UUID,
    user: CurrentUser,
    service: ProductServiceDep,
) -> list[ProductRead]:
    products = await service.list_products(owner=user, store_id=store_id)
    return [ProductRead.model_validate(product) for product in products]


@router.post(
    "",
    response_model=ProductRead,
    status_code=201,
    summary="Crear un producto en una tienda propia",
    responses={
        401: {"model": ErrorResponse, "description": "Token ausente, inválido o expirado"},
        403: {"model": ErrorResponse, "description": "La tienda pertenece a otro usuario"},
        404: {"model": ErrorResponse, "description": "La tienda no existe"},
        422: {"model": ErrorResponse, "description": "Datos inválidos o límite del plan alcanzado"},
    },
)
async def create_product(
    store_id: UUID,
    payload: ProductCreate,
    user: CurrentUser,
    service: ProductServiceDep,
) -> ProductRead:
    product = await service.create_product(owner=user, store_id=store_id, data=payload)
    return ProductRead.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Editar nombre, descripción, precio o visibilidad de un producto",
)
async def update_product(
    store_id: UUID,
    product_id: UUID,
    payload: ProductUpdate,
    user: CurrentUser,
    service: ProductServiceDep,
) -> ProductRead:
    product = await service.update_product(user, store_id, product_id, payload)
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}/image",
    response_model=ProductRead,
    summary="Quitar la imagen de un producto",
)
async def remove_product_image(
    store_id: UUID,
    product_id: UUID,
    user: CurrentUser,
    service: ProductImageServiceDep,
) -> ProductRead:
    product = await service.remove_image(user, store_id, product_id)
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un producto y su imagen asociada",
)
async def delete_product(
    store_id: UUID,
    product_id: UUID,
    user: CurrentUser,
    service: ProductImageServiceDep,
) -> Response:
    await service.delete_product(user, store_id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{product_id}/image",
    response_model=ProductRead,
    summary="Subir o reemplazar la imagen de un producto",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
async def upload_product_image(
    store_id: UUID,
    product_id: UUID,
    request: Request,
    user: CurrentUser,
    service: ProductImageServiceDep,
    file: UploadFile = File(...),
) -> ProductRead:
    settings: Settings = request.app.state.settings
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise BusinessRuleViolationException("La imagen debe ser JPEG, PNG o WebP.")
    content = await file.read(settings.max_product_image_bytes + 1)
    if len(content) > settings.max_product_image_bytes:
        raise BusinessRuleViolationException("La imagen no puede superar 2 MiB.")
    valid_signatures = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    }
    if not valid_signatures[file.content_type]:
        raise BusinessRuleViolationException("El contenido del archivo no coincide con su formato de imagen.")
    product = await service.upload(user, store_id, product_id, content, file.content_type)
    return ProductRead.model_validate(product)
