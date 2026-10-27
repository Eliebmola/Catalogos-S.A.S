from fastapi import APIRouter

from app.core.database import DbSession
from app.core.security import CurrentUser
from app.modules.users.models import User
from app.modules.users.schemas import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileRead, summary="Consultar mi nombre de contacto")
async def get_my_profile(user: CurrentUser, session: DbSession):
    profile = await session.get(User, user.id)
    return {"email": user.email, "full_name": (profile.full_name if profile else None) or user.full_name}


@router.patch("/me", response_model=UserProfileRead, summary="Actualizar mi nombre de contacto")
async def update_my_profile(payload: UserProfileUpdate, user: CurrentUser, session: DbSession):
    profile = await session.get(User, user.id)
    if profile is None:
        profile = User(id=user.id, email=user.email, full_name=payload.full_name)
        session.add(profile)
    else:
        profile.email = user.email or profile.email
        profile.full_name = payload.full_name
    await session.commit()
    return {"email": user.email, "full_name": payload.full_name}
