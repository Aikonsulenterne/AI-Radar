"""Genlæsning af dokumenter behandlet før leverandørprompten.

Ældre udtræk sprang leverandørtilbud over. Kørslerne genlæser derfor
relevante dokumenter, der mangler vendor_extracted_at: kun leverandørclaims
tilføjes, eksisterende claims dubleres ikke, og der laves ingen nye signaler
eller cases.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.models import Document
from app.routes.documents import ai_provider_dep
from app.routes.runs import run_ai_provider
from tests.conftest import FakeProvider, SessionFactory
from tests.test_vendor_landscape import EXTRACTION, TEXT

OLD_EXTRACTION = {"claims": [EXTRACTION["claims"][1]]}  # kun Telmore USES_VENDOR Puzzel


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def provider() -> Any:
    fake = FakeProvider(extraction=OLD_EXTRACTION)
    app.dependency_overrides[ai_provider_dep] = lambda: fake
    app.dependency_overrides[run_ai_provider] = lambda: fake
    yield fake
    app.dependency_overrides.pop(ai_provider_dep, None)
    app.dependency_overrides.pop(run_ai_provider, None)


def _processed_old_document(
    client: TestClient, headers: dict[str, str], factory: SessionFactory
) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Branchemedie",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=headers,
    ).json()
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("nyhed.txt", TEXT.encode(), "text/plain")},
        headers=headers,
    )
    document_id: str = upload.json()["document"]["id"]
    response = client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)
    assert response.status_code == 200, response.text
    # Som behandlet før leverandørprompten fandtes.
    with factory() as db:
        document = db.get(Document, uuid.UUID(document_id))
        assert document is not None
        document.vendor_extracted_at = None
        db.commit()
    return document_id


def _run(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post("/api/v1/runs", json={"force_all": True}, headers=headers)
    assert response.status_code == 202, response.text
    run: dict[str, Any] = client.get(
        f"/api/v1/runs/{response.json()['id']}", headers=headers
    ).json()
    return run


def test_run_rereads_old_document_and_adds_only_vendor_claims(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session_factory: SessionFactory,
    provider: Any,
    auto_publish: None,
) -> None:
    document_id = _processed_old_document(client, admin_headers, db_session_factory)
    signals_before = client.get("/api/v1/signals", headers=admin_headers).json()["total"]
    cases_before = client.get("/api/v1/adoption-cases", headers=admin_headers).json()["total"]

    provider.extraction = EXTRACTION  # den nye prompt finder også tilbuddet
    run = _run(client, admin_headers)

    assert run["status"] == "succeeded", run
    assert run["documents_reread"] == 1
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    predicates = sorted(claim["predicate"] for claim in document["claims"])
    # USES_VENDOR fandtes allerede og dubleres ikke; tilbuddet er nyt og godkendt.
    assert predicates == ["OFFERS_CAPABILITY", "USES_VENDOR"]
    assert all(claim["review_status"] == "approved" for claim in document["claims"])
    assert "SCOPE:" in provider.prompts[-1]

    assert client.get("/api/v1/signals", headers=admin_headers).json()["total"] == signals_before
    assert (
        client.get("/api/v1/adoption-cases", headers=admin_headers).json()["total"] == cases_before
    )
    landscape = client.get("/api/v1/vendor-landscape", headers=admin_headers).json()
    assert landscape["vendor_count"] == 1

    # Genlæst én gang: næste kørsel rører det ikke.
    assert _run(client, admin_headers)["documents_reread"] == 0


def test_new_documents_are_not_reread(
    client: TestClient, admin_headers: dict[str, str], provider: Any, auto_publish: None
) -> None:
    provider.extraction = EXTRACTION
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Branchemedie",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("nyhed.txt", TEXT.encode(), "text/plain")},
        headers=admin_headers,
    )
    run = _run(client, admin_headers)
    assert run["documents_processed"] == 1
    assert run["documents_reread"] == 0
