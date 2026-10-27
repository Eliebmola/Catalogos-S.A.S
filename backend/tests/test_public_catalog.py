from sqlalchemy import event

from app.db.registry import Product, Store
from tests.conftest import OWNER


async def _seed(session_factory, store_id):
    async with session_factory() as s:
        s.add_all(
            [
                Product(store_id=store_id, name="B segundo", price=20, sort_order=2),
                Product(store_id=store_id, name="A primero", price=10, sort_order=1),
                Product(store_id=store_id, name="Oculto", price=5, is_active=False),
            ]
        )
        s.add(Store(owner_id=OWNER.id, name="Borrador", slug="borrador", is_published=False))
        await s.commit()


async def test_public_catalog_only_active_sorted_and_minimal(anon_client, session_factory, store_id):
    await _seed(session_factory, store_id)
    r = await anon_client.get("/api/v1/public/stores/tienda-test")
    assert r.status_code == 200
    assert "max-age=60" in r.headers["cache-control"]
    body = r.json()
    assert [p["name"] for p in body["products"]] == ["A primero", "B segundo"]
    assert "owner_id" not in body and "id" not in body and "created_at" not in body


async def test_unpublished_and_unknown_are_indistinguishable_404(anon_client, session_factory, store_id):
    await _seed(session_factory, store_id)
    a = await anon_client.get("/api/v1/public/stores/borrador")
    b = await anon_client.get("/api/v1/public/stores/no-existe")
    assert a.status_code == b.status_code == 404
    assert a.json() == b.json()


async def test_public_catalog_is_two_queries_regardless_of_size(anon_client, session_factory, store_id, app):
    async with session_factory() as s:
        s.add_all([Product(store_id=store_id, name=f"P{i}", price=i) for i in range(25)])
        await s.commit()

    statements: list[str] = []
    engine = session_factory.kw["bind"].sync_engine
    listener = lambda conn, cur, stmt, *a: statements.append(stmt)  # noqa: E731
    event.listen(engine, "before_cursor_execute", listener)
    try:
        r = await anon_client.get("/api/v1/public/stores/tienda-test")
    finally:
        event.remove(engine, "before_cursor_execute", listener)

    assert r.status_code == 200 and len(r.json()["products"]) == 25
    assert len(statements) == 2  # sin N+1
