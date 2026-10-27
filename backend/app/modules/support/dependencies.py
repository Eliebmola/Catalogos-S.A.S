from typing import Annotated

from fastapi import Depends

from app.core.database import DbSession
from app.modules.support.repository import SupportRepository
from app.modules.support.service import SupportService


def get_support_service(session: DbSession) -> SupportService:
    return SupportService(SupportRepository(session))


SupportServiceDep = Annotated[SupportService, Depends(get_support_service)]
