"""Leverandørlandskab: hvem tilbyder hvilken AI-capability til kundecentre.

Et tilbud ("<leverandør> OFFERS_CAPABILITY <capability>") er ikke adoption:
det tæller som leverandør på teknologien, giver ingen adoption case og
vises i /vendor-landscape sammen med dokumenterede kunder.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import FakeProvider

TEXT = (
    "Puzzel lancerer Puzzel Agent Assist med dansk sprogstøtte til kundecentre. "
    "Telmore bruger Puzzel i sit kundecenter."
)

EXTRACTION = {
    "claims": [
        {
            "claim_type": "technology_vendor",
            "predicate": "OFFERS_CAPABILITY",
            "subject_name": "Puzzel",
            "object_name": "Agent Assist",
            "object_text": "Puzzel Agent Assist med dansk sprogstøtte",
            "supporting_excerpt": (
                "Puzzel lancerer Puzzel Agent Assist med dansk sprogstøtte til kundecentre."
            ),
        },
        {
            "claim_type": "technology_vendor",
            "predicate": "USES_VENDOR",
            "subject_name": "Telmore",
            "object_name": "Puzzel",
            "object_text": None,
            "supporting_excerpt": "Telmore bruger Puzzel i sit kundecenter.",
        },
    ]
}


@pytest.fixture()
def vendor_provider() -> Any:
    provider = FakeProvider(extraction=EXTRACTION)
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    yield provider
    app.dependency_overrides.pop(ai_provider_dep, None)


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _process_vendor_document(client: TestClient, headers: dict[str, str]) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Puzzel nyheder",
            "source_type": "vendor_claim",
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
    assert upload.status_code == 200, upload.text
    document_id: str = upload.json()["document"]["id"]
    response = client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)
    assert response.status_code == 200, response.text
    return document_id


def test_extraction_gets_the_curated_capability_list(
    client: TestClient, admin_headers: dict[str, str], vendor_provider: Any
) -> None:
    _process_vendor_document(client, admin_headers)

    extraction_prompt = vendor_provider.prompts[vendor_provider.calls.index("claim_extraction")]
    assert extraction_prompt.startswith("CAPABILITIES:\n- Agent Assist:")
    assert extraction_prompt.endswith(TEXT)


def test_landscape_shows_vendor_offering_and_documented_customer(
    client: TestClient, admin_headers: dict[str, str], vendor_provider: Any, auto_publish: None
) -> None:
    _process_vendor_document(client, admin_headers)

    landscape = client.get("/api/v1/vendor-landscape", headers=admin_headers).json()
    assert landscape["vendor_count"] == 1
    assert landscape["offering_count"] == 1
    agent_assist = next(
        row for row in landscape["capabilities"] if row["capability_name"] == "Agent Assist"
    )
    [vendor] = agent_assist["vendors"]
    assert vendor["name"] == "Puzzel"
    assert vendor["customers"] == ["Telmore"]
    [offering] = vendor["offerings"]
    assert offering["product"] == "Puzzel Agent Assist med dansk sprogstøtte"
    assert offering["source_name"] == "Puzzel nyheder"
    assert offering["auto_approved"] is True
    assert offering["excerpt"].startswith("Puzzel lancerer")


def test_offering_counts_as_vendor_not_adoption_and_gets_no_case(
    client: TestClient, admin_headers: dict[str, str], vendor_provider: Any, auto_publish: None
) -> None:
    _process_vendor_document(client, admin_headers)

    [technology] = client.get("/api/v1/technologies", headers=admin_headers).json()["items"]
    assert technology["vendor_count"] == 1
    assert technology["adopting_company_count"] == 0

    detail = client.get(f"/api/v1/technologies/{technology['id']}", headers=admin_headers).json()
    assert [vendor["name"] for vendor in detail["vendors"]] == ["Puzzel"]
    assert detail["companies"] == []

    # Kun kunden (Telmore) får en adoption case — aldrig leverandøren selv.
    cases = client.get("/api/v1/adoption-cases", headers=admin_headers).json()["items"]
    assert [case["company_name"] for case in cases] == ["Telmore"]


def test_unapproved_offering_is_not_shown(
    client: TestClient, admin_headers: dict[str, str], vendor_provider: Any
) -> None:
    _process_vendor_document(client, admin_headers)

    landscape = client.get("/api/v1/vendor-landscape", headers=admin_headers).json()
    assert landscape["vendor_count"] == 0
    assert all(row["vendors"] == [] for row in landscape["capabilities"])
