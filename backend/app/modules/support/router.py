from uuid import UUID

from fastapi import APIRouter, Request

from app.core.security import AdminUser, CurrentUser
from app.modules.support.dependencies import SupportServiceDep
from app.modules.support.schemas import (
    AdminMessageCreate, MessageCreate, MessageRead, MessageRecipient, MessageStatusUpdate,
    ReplyCreate, ReplyRead, UnreadCount,
)

router = APIRouter(tags=["support"])
seller_router = APIRouter(prefix="/support/messages")
admin_router = APIRouter(prefix="/admin/messages")


@seller_router.get("", response_model=list[MessageRead], summary="Listar mis mensajes al administrador")
async def list_my_messages(user: CurrentUser, service: SupportServiceDep):
    return await service.list_for_owner(user)


@seller_router.post("", response_model=MessageRead, status_code=201,
                    summary="Enviar una solicitud al administrador")
async def submit_message(payload: MessageCreate, user: CurrentUser, service: SupportServiceDep):
    return await service.submit(user, payload.category, payload.subject, payload.body, payload.store_id)


@seller_router.post("/{message_id}/replies", response_model=ReplyRead, status_code=201,
                    summary="Responder en una conversación con el administrador")
async def seller_reply(message_id: UUID, payload: ReplyCreate, user: CurrentUser,
                       service: SupportServiceDep):
    return await service.reply(message_id, user, "seller", payload.body)


@admin_router.get("/unread-count", response_model=UnreadCount,
                  summary="Contar mensajes nuevos para la notificación del panel")
async def unread_count(user: CurrentUser, request: Request, service: SupportServiceDep):
    # El indicador del sidebar se consulta para cualquier sesión del panel. Devuelve cero
    # a vendedores para evitar 403 repetidos, sin exponer la bandeja ni sus datos.
    if not user.email or user.email.strip().lower() not in request.app.state.settings.admin_emails:
        return {"count": 0}
    return {"count": await service.unread_count()}


@admin_router.get("", response_model=list[MessageRead], summary="Recibir mensajes de vendedores")
async def list_messages(_admin: AdminUser, service: SupportServiceDep):
    return await service.list_for_admin()


@admin_router.get("/recipients", response_model=list[MessageRecipient],
                  summary="Listar vendedores y negocios disponibles para iniciar una conversación")
async def list_recipients(_admin: AdminUser, service: SupportServiceDep):
    return await service.repository.list_recipients()


@admin_router.post("", response_model=MessageRead, status_code=201,
                   summary="Iniciar una conversación con un vendedor")
async def create_message_for_seller(payload: AdminMessageCreate, admin: AdminUser,
                                    service: SupportServiceDep):
    return await service.create_for_seller(
        admin, payload.owner_id, payload.category, payload.subject, payload.body, payload.store_id
    )


@admin_router.post("/{message_id}/replies", response_model=ReplyRead, status_code=201,
                   summary="Responder a un vendedor")
async def admin_reply(message_id: UUID, payload: ReplyCreate, user: AdminUser,
                      service: SupportServiceDep):
    return await service.reply(message_id, user, "admin", payload.body)


@admin_router.patch("/{message_id}", response_model=MessageRead, summary="Actualizar estado de una solicitud")
async def update_message(message_id: UUID, payload: MessageStatusUpdate,
                         _admin: AdminUser, service: SupportServiceDep):
    return await service.update_status(message_id, payload.status)


router.include_router(seller_router)
router.include_router(admin_router)
