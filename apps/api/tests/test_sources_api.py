from fastapi.testclient import TestClient

SOURCE_BODY = {
    "name": "Testkilde",
    "source_type": "media",
    "retrieval_method": "web_fetch",
    "access_class": "public",
    "endpoint_url": "https://example.org/artikel",
    "country_code": "DK",
}


def test_list_sources_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/sources")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_create_source_requires_admin(client: TestClient, reader_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/sources", json=SOURCE_BODY, headers=reader_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_create_and_reader_can_list(
    client: TestClient, admin_headers: dict[str, str], reader_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/sources", json=SOURCE_BODY, headers=admin_headers)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Testkilde"
    assert body["active"] is True

    listed = client.get("/api/v1/sources", headers=reader_headers)
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == body["id"]
    assert {"items", "total", "limit", "offset"} <= page.keys()


def test_web_fetch_source_requires_endpoint_url(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    invalid = {**SOURCE_BODY}
    del invalid["endpoint_url"]
    response = client.post("/api/v1/sources", json=invalid, headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_admin_can_patch_source(client: TestClient, admin_headers: dict[str, str]) -> None:
    source_id = client.post("/api/v1/sources", json=SOURCE_BODY, headers=admin_headers).json()["id"]
    response = client.patch(
        f"/api/v1/sources/{source_id}", json={"active": False}, headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json()["active"] is False


def test_patch_unknown_source_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.patch(
        "/api/v1/sources/00000000-0000-0000-0000-000000000000",
        json={"active": False},
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
