from uuid import UUID

from uuid import uuid4

from fastapi import APIRouter, File, Request, Response, UploadFile, status

from app.core.schemas import ErrorResponse
from app.core.security import CurrentUser
from app.modules.stores.dependencies import StoreServiceDep
from app.modules.stores.schemas import StoreCreate, StoreDeleteConfirmation, StorePublicationUpdate, StoreRead, StoreUpdate
from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolationException, ExternalServiceException
from app.core.storage import SupabaseStorage

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post(
    "",
    response_model=StoreRead,
    status_code=201,
    summary="Crear una tienda",
    responses={401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def create_store(payload: StoreCreate, user: CurrentUser, service: StoreServiceDep) -> StoreRead:
    store = await service.create_store(owner=user, data=payload)
    return StoreRead.model_validate(store)


@router.get(
    "",
    response_model=list[StoreRead],
    summary="Listar mis tiendas",
    responses={401: {"model": ErrorResponse}},
)
async def list_my_stores(user: CurrentUser, service: StoreServiceDep) -> list[StoreRead]:
    stores = await service.list_my_stores(owner=user)
    return [StoreRead.model_validate(s) for s in stores]


@router.patch(
    "/{store_id}/publication",
    response_model=StoreRead,
    summary="Publicar o dejar como borrador un catálogo",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def update_publication(
    store_id: UUID,
    payload: StorePublicationUpdate,
    user: CurrentUser,
    service: StoreServiceDep,
) -> StoreRead:
    store = await service.update_publication(user, store_id, payload.is_published)
    return StoreRead.model_validate(store)


@router.patch("/{store_id}", response_model=StoreRead, summary="Editar el perfil público de la marca")
async def update_store_profile(
    store_id: UUID, payload: StoreUpdate, user: CurrentUser, service: StoreServiceDep
) -> StoreRead:
    store = await service.update_profile(user, store_id, payload)
    return StoreRead.model_validate(store)


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar permanentemente un catálogo y sus productos")
async def delete_store(
    store_id: UUID, payload: StoreDeleteConfirmation, user: CurrentUser, service: StoreServiceDep
) -> Response:
    await service.delete_store(user, store_id, payload.confirmation_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{store_id}/brand-image", response_model=StoreRead, summary="Subir el logo de la marca")
async def upload_brand_image(
    store_id: UUID, request: Request, user: CurrentUser, service: StoreServiceDep,
    file: UploadFile = File(...),
) -> StoreRead:
    settings: Settings = request.app.state.settings
    allowed = {"image/jpeg": ("jpg", b"\xff\xd8\xff"), "image/png": ("png", b"\x89PNG\r\n\x1a\n")}
    if file.content_type == "image/webp":
        signature = None
        extension = "webp"
    elif file.content_type in allowed:
        extension, signature = allowed[file.content_type]
    else:
        raise BusinessRuleViolationException("El logo debe ser JPEG, PNG o WebP.")
    content = await file.read(settings.max_product_image_bytes + 1)
    if len(content) > settings.max_product_image_bytes:
        raise BusinessRuleViolationException("El logo no puede superar 2 MiB.")
    if signature and not content.startswith(signature):
        raise BusinessRuleViolationException("El contenido del archivo no coincide con su formato de imagen.")
    if file.content_type == "image/webp" and not (len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
        raise BusinessRuleViolationException("El contenido del archivo no coincide con su formato de imagen.")
    if not settings.supabase_service_role_key:
        raise ExternalServiceException("No se pudo subir la imagen. Estamos revisando el servicio para solucionarlo pronto.")
    storage = SupabaseStorage(settings)
    path = f"{store_id}/brand/{uuid4().hex}.{extension}"
    url = await storage.upload(path, content, file.content_type)
    try:
        store, old_path = await service.update_brand_image(user, store_id, path, url)
    except Exception:
        await storage.remove(path, best_effort=True)
        raise
    if old_path:
        await storage.remove(old_path, best_effort=True)
    return StoreRead.model_validate(store)


@router.delete("/{store_id}/brand-image", response_model=StoreRead, summary="Quitar el logo de la marca")
async def remove_brand_image(
    store_id: UUID, request: Request, user: CurrentUser, service: StoreServiceDep
) -> StoreRead:
    settings: Settings = request.app.state.settings
    # El servicio valida propiedad antes de que se elimine el archivo.
    store = await service.get_owned_store(user, store_id)
    path = store.brand_image_path
    if path:
        if not settings.supabase_service_role_key:
            raise ExternalServiceException("No se pudo quitar la imagen. Inténtalo de nuevo pronto.")
        await SupabaseStorage(settings).remove(path)
    store, _ = await service.update_brand_image(user, store_id, None, None)
    return StoreRead.model_validate(store)
