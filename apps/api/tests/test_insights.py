"""Indsigter: interne OK-dokumenter går uden om markedsfilteret, får et
internt udtræk uden persondata og genlæses ikke for leverandørtilbud."""

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import DOC_TEXT, FakeProvider


def _internal_document(client: TestClient, headers: dict[str, str]) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Interne data (OK)",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": "restricted",
        },
        headers=headers,
    ).json()
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("indbakke.txt", DOC_TEXT.encode(), "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    document_id: str = upload.json()["document"]["id"]
    return document_id


def test_internal_document_skips_market_filter_and_uses_internal_scope(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    # Markedsfilteret ville afvise dokumentet — det må ikke blive spurgt.
    provider = FakeProvider(relevance={"relevant": False, "reason": "ikke marked"})
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        document_id = _internal_document(client, admin_headers)
        response = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)

    assert response.status_code == 200, response.text
    assert response.json()["claims_created"] > 0
    assert "relevance_classification" not in provider.calls
    extraction_prompt = provider.prompts[provider.calls.index("claim_extraction")]
    assert extraction_prompt.startswith("SCOPE: this is an INTERNAL document")
    assert "Never extract personal data" in extraction_prompt


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
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Interne data (OK)",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": "restricted",
        },
        headers=admin_headers,
    ).json()
    csv = "kategori;antal\nbounce;359\nno-reply-svar;192\n"
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("eksport.csv", csv.encode(), "text/csv")},
        headers=admin_headers,
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["document"]["processing_status"] == "normalized"
