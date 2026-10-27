import asyncio
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.billing.models import BillingNotification
from app.modules.billing.repository import BillingRepository


def _email_ready(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def _whatsapp_ready(settings: Settings) -> bool:
    return bool(
        settings.whatsapp_access_token
        and settings.whatsapp_phone_number_id
        and settings.whatsapp_template_name
        and settings.whatsapp_graph_api_version
    )


def _send_email(settings: Settings, destination: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = destination
    message.set_content(body)
    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value() if settings.smtp_password else "")
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value() if settings.smtp_password else "")
            smtp.send_message(message)


async def _send_whatsapp(settings: Settings, destination: str, body_parameter: str, account_name: str) -> None:
    version = settings.whatsapp_graph_api_version
    phone_number_id = settings.whatsapp_phone_number_id
    token = settings.whatsapp_access_token.get_secret_value() if settings.whatsapp_access_token else ""
    url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": "".join(character for character in destination if character.isdigit()),
        "type": "template",
        "template": {
            "name": settings.whatsapp_template_name,
            "language": {"code": settings.whatsapp_template_language},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": account_name or "vendedor"},
                    {"type": "text", "text": body_parameter},
                ],
            }],
        },
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()


async def run_billing_notifications(
    session: AsyncSession, settings: Settings, today: date
) -> dict[str, int]:
    """Daily idempotent job. Schedule one process per day; sent events are not repeated."""
    repository = BillingRepository(session)
    counts = {"sent": 0, "failed": 0, "not_configured": 0}
    for owner, subscription in await repository.due_accounts(today):
        period_end = subscription.paid_through
        if period_end is None:
            continue
        events: list[tuple[str, str]] = []
        if today >= period_end:
            events.append(("due", "Tu periodo mensual venció. Tienes dos días de gracia para registrar el pago."))
        if today > period_end + timedelta(days=settings.billing_grace_days):
            events.append(("suspended", "Tus catálogos están pausados hasta que el administrador registre tu pago."))
        channels = [
            ("email", owner.email, _email_ready(settings)),
            ("whatsapp", subscription.whatsapp_number, _whatsapp_ready(settings)),
        ]
        for kind, message in events:
            for channel, destination, ready in channels:
                if not destination:
                    continue
                if not ready:
                    counts["not_configured"] += 1
                    continue
                record = await repository.get_notification(owner.id, period_end, kind, channel)
                if record is not None and record.status == "sent":
                    continue
                if record is None:
                    record = BillingNotification(
                        owner_id=owner.id, period_end=period_end, kind=kind,
                        channel=channel, status="failed", attempts=0,
                    )
                    session.add(record)
                record.attempts += 1
                record.status = "failed"
                record.last_error = None
                await session.commit()
                try:
                    if channel == "email":
                        subject = "Aviso de pago de tu catálogo" if kind == "due" else "Tus catálogos se pausaron"
                        await asyncio.to_thread(_send_email, settings, destination, subject, message)
                    else:
                        await _send_whatsapp(settings, destination, message, owner.full_name or "")
                    record.status = "sent"
                    record.sent_at = datetime.now(timezone.utc)
                    record.last_error = None
                    counts["sent"] += 1
                except (smtplib.SMTPException, OSError, httpx.HTTPError) as exc:
                    # No almacenar el contenido de la excepción: los proveedores pueden incluir URLs sensibles.
                    record.status = "failed"
                    record.last_error = type(exc).__name__
                    counts["failed"] += 1
                await session.commit()
    return counts
