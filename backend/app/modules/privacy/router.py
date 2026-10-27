from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.database import DbSession
from app.core.security import VerifiedUser
from app.modules.privacy.models import PrivacyConsent
from app.modules.privacy.schemas import ConsentAcceptance, ConsentStatus

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/consent", response_model=ConsentStatus)
async def get_consent_status(
    user: VerifiedUser, session: DbSession, request: Request
) -> ConsentStatus:
    version = request.app.state.settings.privacy_policy_version
    consent = await session.get(PrivacyConsent, (user.id, version))
    return ConsentStatus(
        accepted=consent is not None,
        policy_version=version,
        accepted_at=consent.accepted_at if consent else None,
    )


@router.post("/consent", response_model=ConsentStatus, status_code=status.HTTP_200_OK)
async def accept_current_policy(
    payload: ConsentAcceptance, user: VerifiedUser, session: DbSession, request: Request
) -> ConsentStatus:
    if not payload.accepted:
        raise HTTPException(status_code=422, detail="Se requiere aceptación expresa.")
    version = request.app.state.settings.privacy_policy_version
    key = (user.id, version)
    consent = await session.get(PrivacyConsent, key)
    if consent is None:
        consent = PrivacyConsent(user_id=user.id, policy_version=version)
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    return ConsentStatus(
        accepted=True,
        policy_version=consent.policy_version,
        accepted_at=consent.accepted_at,
    )
