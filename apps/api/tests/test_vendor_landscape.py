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


NEW_TECH_TEXT = (
    "Dixa lancerer Dixa Live Translate, der oversætter kundesamtaler i realtid. "
    "Dixa tilbyder også Emotion Radar, der måler kundens følelser undervejs."
)

NEW_TECH_EXTRACTION = {
    "claims": [
        {
            "claim_type": "technology_vendor",
            "predicate": "OFFERS_CAPABILITY",
            "subject_name": "Dixa",
            "object_name": "Real-time Translation",
            "object_text": "Dixa Live Translate",
            "supporting_excerpt": (
                "Dixa lancerer Dixa Live Translate, der oversætter kundesamtaler i realtid."
            ),
        },
        {
            "claim_type": "technology_vendor",
            "predicate": "OFFERS_CAPABILITY",
            "subject_name": "Dixa",
            # For langt til at være et capability-navn: forbliver tekst.
            "object_name": "A tool that measures how the customer feels during the conversation",
            "object_text": "Emotion Radar",
            "supporting_excerpt": (
                "Dixa tilbyder også Emotion Radar, der måler kundens følelser undervejs."
            ),
        },
    ]
}


def _process_text(client: TestClient, headers: dict[str, str], text: str) -> None:
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
        files={"file": ("nyhed.txt", text.encode(), "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["document"]["id"]
    response = client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)
    assert response.status_code == 200, response.text


@pytest.fixture()
def new_tech_provider() -> Any:
    provider = FakeProvider(extraction=NEW_TECH_EXTRACTION)
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    yield provider
    app.dependency_overrides.pop(ai_provider_dep, None)


def _technologies(client: TestClient, headers: dict[str, str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = client.get("/api/v1/technologies", headers=headers).json()[
        "items"
    ]
    return items


def test_unknown_capability_becomes_candidate_technology_once(
    client: TestClient, admin_headers: dict[str, str], new_tech_provider: Any, auto_publish: None
) -> None:
    _process_text(client, admin_headers, NEW_TECH_TEXT)
    _process_text(client, admin_headers, NEW_TECH_TEXT + " ")

    candidates = [t for t in _technologies(client, admin_headers) if t["is_candidate"]]
    # Samme navn to gange giver én kandidat; den lange beskrivelse giver ingen.
    assert [t["name"] for t in candidates] == ["Real-time Translation"]
    candidate = candidates[0]
    assert candidate["horizon"] is None
    assert candidate["discovered_at"] is not None
    assert candidate["vendor_count"] == 1

    # Næste udtræk får kandidaten med, så modellen genbruger navnet.
    prompt = new_tech_provider.prompts[new_tech_provider.calls.index("claim_extraction")]
    assert "- Real-time Translation:" not in prompt  # første kald: fandtes ikke endnu
    last_prompt = [
        p
        for c, p in zip(new_tech_provider.calls, new_tech_provider.prompts, strict=True)
        if c == "claim_extraction"
    ][-1]
    assert "- Real-time Translation:" in last_prompt

    landscape = client.get("/api/v1/vendor-landscape", headers=admin_headers).json()
    row = next(
        c for c in landscape["capabilities"] if c["capability_name"] == "Real-time Translation"
    )
    assert row["technology"]["is_candidate"] is True
    assert [v["name"] for v in row["vendors"]] == ["Dixa"]
    other = next(c for c in landscape["capabilities"] if c["technology"] is None)
    assert other["vendors"][0]["offerings"][0]["product"] == "Emotion Radar"


def test_admin_adopts_candidate_onto_the_radar(
    client: TestClient,
    admin_headers: dict[str, str],
    reviewer_headers: dict[str, str],
    new_tech_provider: Any,
) -> None:
    _process_text(client, admin_headers, NEW_TECH_TEXT)
    [candidate] = [t for t in _technologies(client, admin_headers) if t["is_candidate"]]
    url = f"/api/v1/technologies/{candidate['id']}"

    assert client.patch(url, json={"horizon": "next"}, headers=reviewer_headers).status_code == 403
    assert client.patch(url, json={"horizon": None}, headers=admin_headers).status_code == 422

    response = client.patch(
        url,
        json={"horizon": "next", "definition": "Oversættelse af kundesamtaler i realtid."},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    adopted = response.json()
    assert adopted["horizon"] == "next"
    assert adopted["is_candidate"] is False

    rejected = client.patch(url, json={"active": False}, headers=admin_headers)
    assert rejected.status_code == 200
    assert all(t["id"] != candidate["id"] for t in _technologies(client, admin_headers))

    audit = client.get("/api/v1/audit?entity_type=technology", headers=admin_headers).json()
    assert len(audit["items"]) == 2


def test_merging_duplicate_candidate_moves_claims_and_future_names(
    client: TestClient, admin_headers: dict[str, str], new_tech_provider: Any, auto_publish: None
) -> None:
    _process_text(client, admin_headers, NEW_TECH_TEXT)
    techs = _technologies(client, admin_headers)
    [candidate] = [t for t in techs if t["is_candidate"]]
    [agent_assist] = [t for t in techs if t["name"] == "Agent Assist"]

    response = client.patch(
        f"/api/v1/technologies/{candidate['id']}",
        json={"merge_into_id": agent_assist["id"]},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["vendor_count"] == 1
    assert all(t["id"] != candidate["id"] for t in _technologies(client, admin_headers))

    # Dublettens navn er nu et alias for målet: samme navn igen giver ingen ny kandidat.
    _process_text(client, admin_headers, NEW_TECH_TEXT + " ")
    assert not [t for t in _technologies(client, admin_headers) if t["is_candidate"]]

    landscape = client.get("/api/v1/vendor-landscape", headers=admin_headers).json()
    row = next(c for c in landscape["capabilities"] if c["capability_name"] == "Agent Assist")
    [dixa] = row["vendors"]
    # To artikler om samme produkt vises som ét tilbud.
    assert [o["product"] for o in dixa["offerings"]] == ["Dixa Live Translate"]
    assert dixa["offerings"][0]["also_reported_by"] == []  # samme kilde begge gange


def test_vendor_matches_across_legal_form(client: TestClient, db_session_factory: Any) -> None:
    from app.pipeline.entities import legal_base_name, resolve_company

    assert legal_base_name("Zendesk, Inc.") == "zendesk"
    assert legal_base_name("Puzzel AS") == "puzzel"
    assert legal_base_name("Group") == "group"
    with db_session_factory() as db:
        first = resolve_company(db, "Zendesk")
        assert resolve_company(db, "Zendesk Inc.").id == first.id
        assert resolve_company(db, "Zendesk, Inc.").id == first.id
        assert resolve_company(db, "Zendesk Labs").id != first.id
