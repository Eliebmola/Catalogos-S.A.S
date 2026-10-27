from typing import Annotated

from fastapi import Depends

from app.core.database import DbSession
from app.modules.categories.repository import CategoryRepository
from app.modules.categories.service import CategoryService
from app.modules.stores.repository import StoreRepository


def get_category_service(session: DbSession) -> CategoryService:
    return CategoryService(session, CategoryRepository(session), StoreRepository(session))


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
