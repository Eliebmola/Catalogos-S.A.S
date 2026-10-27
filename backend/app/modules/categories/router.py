from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.security import CurrentUser
from app.modules.categories.dependencies import CategoryServiceDep
from app.modules.categories.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/stores/{store_id}/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead], summary="Listar categorías de un catálogo")
async def list_categories(store_id: UUID, user: CurrentUser, service: CategoryServiceDep):
    return [CategoryRead.model_validate(item) for item in await service.list(user, store_id)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED,
             summary="Crear categoría en un catálogo")
async def create_category(store_id: UUID, payload: CategoryCreate, user: CurrentUser,
                          service: CategoryServiceDep) -> CategoryRead:
    return CategoryRead.model_validate(await service.create(user, store_id, payload))


@router.patch("/{category_id}", response_model=CategoryRead, summary="Renombrar categoría")
async def update_category(store_id: UUID, category_id: UUID, payload: CategoryUpdate,
                          user: CurrentUser, service: CategoryServiceDep) -> CategoryRead:
    return CategoryRead.model_validate(await service.update(user, store_id, category_id, payload))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Eliminar categoría y dejar sus productos sin categoría")
async def delete_category(store_id: UUID, category_id: UUID, user: CurrentUser,
                          service: CategoryServiceDep) -> Response:
    await service.delete(user, store_id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
