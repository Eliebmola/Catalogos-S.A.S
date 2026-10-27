from uuid import uuid4

from tests.conftest import INTRUDER

VALID = {"name": "Camiseta Oversize", "price": "59990.50", "description": "Algodón 100%"}


async def test_create_product_ok(owner_client, store_id):
    r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json=VALID)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Camiseta Oversize"
    assert body["price"] == "59990.50"  # Decimal serializado como string
    assert body["currency"] == "COP" and body["is_active"] is True
    assert body["store_id"] == str(store_id)
    assert body["created_at"] and body["id"]
    assert "image_path" not in body  # campo interno nunca expuesto


async def test_requires_authentication(anon_client, store_id):
    r = await anon_client.post(f"/api/v1/stores/{store_id}/products", json=VALID)
    assert r.status_code == 401
    assert r.json()["code"] == 401 and r.json()["type"] == "authentication_required"
    assert r.headers["www-authenticate"] == "Bearer"


async def test_cannot_create_in_someone_elses_store(owner_client, act_as, store_id):
    act_as(INTRUDER)
    r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json=VALID)
    assert r.status_code == 403
    assert r.json()["type"] == "forbidden"


async def test_unknown_store_is_404(owner_client):
    r = await owner_client.post(f"/api/v1/stores/{uuid4()}/products", json=VALID)
    assert r.status_code == 404
    assert r.json() == {"error": "La tienda no existe.", "code": 404, "type": "resource_not_found"}


async def test_invalid_payload_is_422_and_does_not_echo_input(owner_client, store_id):
    bad = {"name": "x", "price": "-5", "store_id": str(uuid4()), "image_url": "javascript:alert(1)"}
    r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert body["type"] == "validation_error"
    fields = {d["field"] for d in body["details"]}
    assert {"body.name", "body.price", "body.store_id", "body.image_url"} <= fields  # extra='forbid'
    assert "javascript" not in r.text  # no se refleja la entrada del cliente


async def test_html_is_stripped_and_empty_result_rejected(owner_client, store_id):
    r = await owner_client.post(
        f"/api/v1/stores/{store_id}/products",
        json={"name": "<script>alert(1)</script>Gorra", "price": 10},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "alert(1)Gorra"  # etiquetas fuera

    r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json={"name": "<b></b>", "price": 10})
    assert r.status_code == 422


async def test_price_precision_rejected(owner_client, store_id):
    r = await owner_client.post(
        f"/api/v1/stores/{store_id}/products", json={"name": "Producto", "price": "1.999"}
    )
    assert r.status_code == 422


async def test_plan_limit_is_422(owner_client, store_id):
    for i in range(3):  # max_products_per_store = 3 en los tests
        r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json={**VALID, "name": f"Prod {i}"})
        assert r.status_code == 201
    r = await owner_client.post(f"/api/v1/stores/{store_id}/products", json=VALID)
    assert r.status_code == 422
    assert r.json()["type"] == "business_rule_violation"


async def test_unknown_route_uses_standard_error_shape(anon_client):
    r = await anon_client.get("/api/v1/nope")
    assert r.status_code == 404
    assert set(r.json()) == {"error", "code", "type"}
