"""Ejecutar una vez al día desde un programador (cron/Task Scheduler)."""
import asyncio

from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.database import build_engine, create_session_factory
from app.modules.billing.notifications import run_billing_notifications
from datetime import datetime


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    sessions = create_session_factory(engine)
    today = datetime.now(ZoneInfo(settings.app_timezone)).date()
    async with sessions() as session:
        result = await run_billing_notifications(session, settings, today)
    print(f"Avisos de suscripción: {result}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
