"""Conexión asíncrona a PostgreSQL (Supabase). Engine y session factory se crean en el
`lifespan` (no al importar), lo que facilita los tests y evita efectos secundarios."""

from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    connect_args: dict[str, Any] = {}

    if settings.db_require_ssl:
        connect_args["ssl"] = "require"

    if settings.db_behind_pooler:
        # Supavisor/PgBouncer en modo transacción no soportan prepared statements de sesión:
        # se desactiva la caché de asyncpg y de SQLAlchemy y se usan nombres únicos.
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"

    return create_async_engine(
        settings.database_url.get_secret_value(),
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=1800,  # recicla conexiones antes de que el pooler las cierre
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: en async, acceder a atributos expirados dispararía I/O implícito.
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una sesión por request. NO hace commit: la frontera transaccional la decide la capa de
    servicios (commit explícito), así un fallo al confirmar se reporta correctamente al cliente.
    Al salir, la sesión se cierra y revierte cualquier transacción pendiente."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
