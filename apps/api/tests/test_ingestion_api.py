from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ingestion.fetch import FetchResult


def _create_source(client: TestClient, headers: dict[str, str], **overrides: Any) -> str:
    body: dict[str, Any] = {
        "name": "Uploadkilde",
        "source_type": "primary",
        "retrieval_method": "manual_upload",
        "access_class": "public",
    }
    body.update(overrides)
    response = client.post("/api/v1/sources", json=body, headers=headers)
    assert response.status_code == 201, response.text
    source_id: str = response.json()["id"]
    return source_id


def test_upload_is_idempotent_on_content_hash(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _create_source(client, admin_headers)
    files = {"file": ("notat.txt", b"Referat   fra  moede\n", "text/plain")}

    first = client.post(
        f"/api/v1/sources/{source_id}/documents", files=files, headers=admin_headers
    )
    assert first.status_code == 200, first.text
    assert first.json()["created"] is True
    doc = first.json()["document"]
    assert doc["processing_status"] == "normalized"
    assert doc["mime_type"] == "text/plain"

    second = client.post(
        f"/api/v1/sources/{source_id}/documents", files=files, headers=admin_headers
    )
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["document"]["id"] == doc["id"]


def test_upload_rejects_unsupported_mime(client: TestClient, admin_headers: dict[str, str]) -> None:
    source_id = _create_source(client, admin_headers)
    files = {"file": ("virus.exe", b"MZ", "application/octet-stream")}
    response = client.post(
        f"/api/v1/sources/{source_id}/documents", files=files, headers=admin_headers
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_run_web_fetch_creates_document_and_is_idempotent(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _create_source(
        client,
        admin_headers,
        retrieval_method="web_fetch",
        endpoint_url="https://example.org/nyhed",
    )

    def fake_fetch(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
        html = b"<html><head><title>Nyhed</title></head><body><p>Indhold</p></body></html>"
        return FetchResult(data=html, content_type="text/html", final_url=url)

    monkeypatch.setattr("app.routes.sources.fetch_url", fake_fetch)

    first = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert first.status_code == 200, first.text
    assert first.json()["created"] is True
    document = first.json()["document"]
    assert document["title"] == "Nyhed"
    assert document["canonical_url"] == "https://example.org/nyhed"
    assert document["processing_status"] == "normalized"

    second = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["created"] is False


def test_run_rss_source_is_not_implemented_yet(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _create_source(
        client,
        admin_headers,
        retrieval_method="rss",
        endpoint_url="https://example.org/feed.xml",
    )
    response = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_implemented"


def test_run_non_public_source_is_rejected(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _create_source(
        client,
        admin_headers,
        retrieval_method="web_fetch",
        endpoint_url="https://example.org/artikel",
        access_class="licensed",
    )
    response = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "access_restricted"


def test_review_documents_requires_reviewer(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    source_id = _create_source(client, admin_headers)
    files = {"file": ("notat.txt", b"Tekst til review", "text/plain")}
    upload = client.post(
        f"/api/v1/sources/{source_id}/documents", files=files, headers=admin_headers
    )
    document_id = upload.json()["document"]["id"]

    forbidden = client.get("/api/v1/review/documents", headers=reader_headers)
    assert forbidden.status_code == 403

    listed = client.get("/api/v1/review/documents", headers=reviewer_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    detail = client.get(f"/api/v1/review/documents/{document_id}", headers=reviewer_headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["normalized_text"] == "Tekst til review"
    assert body["raw_storage_path"] is not None
    # Lokal storage udsteder ingen signerede URLs.
    assert body["raw_url"] is None
