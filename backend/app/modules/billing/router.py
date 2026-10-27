from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.database import DbSession
from app.core.security import AdminUser, CurrentUser
from app.modules.billing.dependencies import BillingServiceDep, current_local_date
from app.modules.billing.schemas import AccessOverrideUpdate, BillingAccountRead, BillingProviderStatus, ExtraCatalogsUpdate, PlanInfoRead, WhatsAppContactUpdate
from app.core.config import Settings
from app.modules.users.models import User
from app.modules.billing.models import Subscription
from app.modules.billing.repository import BillingRepository
from app.modules.billing.service import subscription_status
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/admin/subscriptions", tags=["admin-billing"])


@router.get("/me", response_model=PlanInfoRead, summary="Consultar mi plan y suscripción")
async def my_plan(user: CurrentUser, session: DbSession, request: Request,
                  today: date = Depends(current_local_date)) -> dict:
    settings: Settings = request.app.state.settings
    billing = BillingRepository(session)
    is_new_account = await UserRepository(session).ensure_exists(user.id, user.email)
    subscription = await billing.get_subscription(user.id)
    if is_new_account and subscription is not None:
        from datetime import timedelta
        subscription.trial_until = today + timedelta(days=settings.billing_trial_days - 1)
        subscription.legacy_grandfathered = False
        await session.commit()
    status = subscription_status(subscription, today, settings.billing_grace_days)
    if subscription and subscription.legacy_grandfathered:
        status = "legacy"
    extra = subscription.extra_catalogs if subscription else 0
    count = await billing.count_stores(user.id)
    return {
        "status": status, "catalog_count": count, "included_catalogs": 2,
        "extra_catalogs": extra, "catalog_limit": 2 + extra,
        "monthly_price_cop": settings.billing_monthly_price_cop,
        "extra_catalog_price_cop": settings.billing_extra_catalog_price_cop,
        "monthly_total_cop": settings.billing_monthly_price_cop + extra * settings.billing_extra_catalog_price_cop,
        "trial_until": subscription.trial_until if subscription else None,
        "paid_through": subscription.paid_through if subscription else None,
        "grace_days": settings.billing_grace_days,
        "billing_whatsapp_number": settings.billing_whatsapp_number,
    }


@router.get("/notification-status", response_model=BillingProviderStatus, summary="Ver configuración de avisos")
async def notification_status(_admin: AdminUser, request: Request) -> BillingProviderStatus:
    settings: Settings = request.app.state.settings
    return BillingProviderStatus(
        grace_days=settings.billing_grace_days,
        trial_days=settings.billing_trial_days,
        monthly_price_cop=settings.billing_monthly_price_cop,
        extra_catalog_price_cop=settings.billing_extra_catalog_price_cop,
        max_image_bytes=settings.max_product_image_bytes,
        email_notifications_ready=bool(settings.smtp_host and settings.smtp_from_email),
        whatsapp_notifications_ready=bool(
            settings.whatsapp_access_token and settings.whatsapp_phone_number_id
            and settings.whatsapp_template_name and settings.whatsapp_graph_api_version
        ),
        whatsapp_orders_ready=bool(
            settings.whatsapp_access_token and settings.whatsapp_phone_number_id
            and settings.whatsapp_order_template_name and settings.whatsapp_graph_api_version
        ),
    )


@router.get("", response_model=list[BillingAccountRead], summary="Listar cuentas y estado de suscripción")
async def list_accounts(
    _admin: AdminUser,
    service: BillingServiceDep,
    today: date = Depends(current_local_date),
) -> list[dict]:
    return await service.list_accounts(today)


@router.post("/{owner_id}/payments", response_model=BillingAccountRead, summary="Registrar pago manual y renovar un mes")
async def record_payment(
    owner_id: UUID,
    _admin: AdminUser,
    session: DbSession,
    service: BillingServiceDep,
    today: date = Depends(current_local_date),
) -> dict:
    if await session.get(User, owner_id) is None:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("La cuenta no existe.")
    await service.record_payment(owner_id, today, _admin.email or "")
    account = next((row for row in await service.list_accounts(today) if row["owner_id"] == owner_id), None)
    return account


@router.patch("/{owner_id}/access", response_model=BillingAccountRead, summary="Bloquear o desbloquear catálogos de una cuenta")
async def update_access(
    owner_id: UUID,
    payload: AccessOverrideUpdate,
    _admin: AdminUser,
    session: DbSession,
    service: BillingServiceDep,
    today: date = Depends(current_local_date),
) -> dict:
    if await session.get(User, owner_id) is None:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("La cuenta no existe.")
    await service.set_access_override(owner_id, payload.blocked)
    return next(row for row in await service.list_accounts(today) if row["owner_id"] == owner_id)


@router.patch("/{owner_id}/contact", response_model=BillingAccountRead, summary="Actualizar el WhatsApp de avisos")
async def update_contact(
    owner_id: UUID,
    payload: WhatsAppContactUpdate,
    _admin: AdminUser,
    session: DbSession,
    service: BillingServiceDep,
    today: date = Depends(current_local_date),
) -> dict:
    if await session.get(User, owner_id) is None:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("La cuenta no existe.")
    await service.update_whatsapp(owner_id, payload.whatsapp_number)
    return next(row for row in await service.list_accounts(today) if row["owner_id"] == owner_id)


@router.patch("/{owner_id}/extra-catalogs", response_model=BillingAccountRead,
              summary="Definir el número de catálogos extra incluidos en el plan")
async def update_extra_catalogs(
    owner_id: UUID,
    payload: ExtraCatalogsUpdate,
    _admin: AdminUser,
    session: DbSession,
    service: BillingServiceDep,
    today: date = Depends(current_local_date),
) -> dict:
    if await session.get(User, owner_id) is None:
        from app.core.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("La cuenta no existe.")
    await service.set_extra_catalogs(owner_id, payload.extra_catalogs)
    return next(row for row in await service.list_accounts(today) if row["owner_id"] == owner_id)
