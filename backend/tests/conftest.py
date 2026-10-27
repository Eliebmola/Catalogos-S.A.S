from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import get_db_session
from app.core.security import AuthenticatedUser, get_current_user
from app.db.registry import Base, Store, User
from app.main import create_app

OWNER = AuthenticatedUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="owner@test.dev")
INTRUDER = AuthenticatedUser(id=UUID("22222222-2222-2222-2222-222222222222"), email="intruder@test.dev")


def make_settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql://u:p@localhost/db",
        supabase_url="https://abc.supabase.co",
        supabase_jwt_secret="test-secret-test-secret-test-secret-123",
        max_products_per_store=3,
    )
    return Settings(_env_file=None, **{**base, **overrides})


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def app(session_factory) -> FastAPI:
    application = create_app(make_settings())

    async def _db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db_session] = _db
    return application


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def anon_client(app) -> AsyncIterator[httpx.AsyncClient]:
    """Sin override de auth: ejercita la verificación JWT real."""
    async with _client(app) as client:
        yield client


@pytest_asyncio.fixture
async def owner_client(app) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: OWNER
    async with _client(app) as client:
        yield client


@pytest.fixture
def act_as(app):
    def _act_as(user: AuthenticatedUser) -> None:
        app.dependency_overrides[get_current_user] = lambda: user

    return _act_as


@pytest_asyncio.fixture
async def store_id(session_factory) -> UUID:
    """Una tienda publicada del OWNER, sembrada directo en BD."""
    async with session_factory() as session:
        session.add_all([User(id=OWNER.id, email=OWNER.email), User(id=INTRUDER.id, email=INTRUDER.email)])
        store = Store(id=uuid4(), owner_id=OWNER.id, name="Tienda Test", slug="tienda-test", is_published=True)
        session.add(store)
        await session.commit()
        return store.id
