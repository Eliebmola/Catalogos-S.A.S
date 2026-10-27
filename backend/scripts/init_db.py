"""Crea las tablas (SOLO desarrollo / primer arranque). Para producción usa migraciones Alembic (paso 4).
Uso:  python -m scripts.init_db"""

import asyncio

from app.core.config import get_settings
from app.core.database import build_engine
from app.db.registry import Base


async def main() -> None:
    engine = build_engine(get_settings())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tablas creadas.")


if __name__ == "__main__":
    asyncio.run(main())
