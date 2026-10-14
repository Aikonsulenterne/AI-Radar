"""Interne OK-dokumenter: radaren kører ikke i et internt miljø, så de kan
ikke uploades, og dokumenter fra før spærringen sendes aldrig til AI."""

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import DOC_TEXT, FakeProvider


def _source(client: TestClient, headers: dict[str, str], access_class: str) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Interne data (OK)",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": access_class,
        },
        headers=headers,
    ).json()
    source_id: str = source["id"]
    return source_id


def test_internal_documents_cannot_be_uploaded(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _source(client, admin_headers, "restricted")
    upload = client.post(
        f"/api/v1/sources/{source_id}/documents",
        files={"file": ("indbakke.txt", DOC_TEXT.encode(), "text/plain")},
        headers=admin_headers,
    )
    assert upload.status_code == 409
    assert upload.json()["error"]["code"] == "internal_not_allowed"


def test_internal_document_from_before_is_never_sent_to_ai(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _source(client, admin_headers, "public")
    upload = client.post(
        f"/api/v1/sources/{source_id}/documents",
        files={"file": ("indbakke.txt", DOC_TEXT.encode(), "text/plain")},
        headers=admin_headers,
    )
    document_id = upload.json()["document"]["id"]
    client.patch(
        f"/api/v1/sources/{source_id}", json={"access_class": "restricted"}, headers=admin_headers
    )
    provider = FakeProvider()
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        response = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)
    assert response.status_code == 200, response.text
    assert response.json()["claims_created"] == 0
    assert provider.calls == []


def test_market_document_still_goes_through_the_filter(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any
) -> None:
    from tests.conftest import _upload_document

    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    assert fake_provider.calls[0] == "relevance_classification"


def test_csv_export_can_be_uploaded_as_text(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source_id = _source(client, admin_headers, "public")
    csv = "kategori;antal\nchat;359\nmail;192\n"
    upload = client.post(
        f"/api/v1/sources/{source_id}/documents",
        files={"file": ("eksport.csv", csv.encode(), "text/csv")},
        headers=admin_headers,
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["document"]["processing_status"] == "normalized"
