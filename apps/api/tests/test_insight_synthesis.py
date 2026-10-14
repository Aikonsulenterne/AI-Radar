"""Indsigter på tværs af radarens fund: kun godkendte claims fra ikke-interne
kilder, mindst to dokumenter pr. indsigt, evidensstyrke beregnet af serveren."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import DOC_TEXT, FakeProvider, _upload_document
from tests.test_vendor_landscape import EXTRACTION, TEXT

INSIGHT = {
    "type": "adoption",
    "title": "Agent Assist er i drift hos flere og sælges af nordiske leverandører",
    "finding": "Danske Bank bruger Agent Assist, og Puzzel tilbyder Agent Assist.",
    "implication": "Det kan være modent nok til en pilot i OK's mailkø.",
    "recommendation": "Spørg Telmore, hvordan Puzzel Agent Assist virker i praksis.",
    "problem": "Store mailmængder",
    "claims": [1, 2, 3, 4],
}


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _radar_with_two_documents(client: TestClient, headers: dict[str, str]) -> None:
    app.dependency_overrides[ai_provider_dep] = lambda: FakeProvider()
    document_id = _upload_document(client, headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)
    # Andet dokument fra leverandørens egen kilde.
    app.dependency_overrides[ai_provider_dep] = lambda: FakeProvider(extraction=EXTRACTION)
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
    client.post(
        f"/api/v1/review/documents/{upload.json()['document']['id']}/process", headers=headers
    )
    app.dependency_overrides.pop(ai_provider_dep, None)


def _generate(client: TestClient, headers: dict[str, str], provider: FakeProvider) -> Any:
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        return client.post("/api/v1/insights/generate", headers=headers)
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)


def test_insights_need_two_documents_and_known_claims(
    client: TestClient, admin_headers: dict[str, str], auto_publish: None
) -> None:
    _radar_with_two_documents(client, admin_headers)
    provider = FakeProvider(
        insights={
            "insights": [
                INSIGHT,
                {**INSIGHT, "title": "Kun ét claim", "claims": [1]},
                {**INSIGHT, "title": "Ukendt claim", "claims": [1, 999]},
            ]
        }
    )

    response = _generate(client, admin_headers, provider)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["evidence_count"] == 4
    assert data["discarded"] == 2
    [insight] = data["items"]
    assert insight["title"] == INSIGHT["title"]
    assert insight["problem"] == "Store mailmængder"
    assert insight["document_count"] == 2
    # To dokumenter, ikke kun leverandørkilder: moderat — beregnet af serveren.
    assert insight["strength"] == "moderat"
    assert insight["vendor_only"] is False
    assert len(insight["evidence"]) == 4
    assert {e["vendor_source"] for e in insight["evidence"]} == {True, False}

    prompt = provider.prompts[provider.calls.index("insight_synthesis")]
    assert prompt.startswith("OK'S PROBLEMS:\n- Store mailmængder:")
    assert "EVIDENCE:\n[1] " in prompt

    # Gemt: læsning giver samme indsigt.
    again = client.get("/api/v1/insights", headers=admin_headers).json()
    assert [i["id"] for i in again["items"]] == [insight["id"]]


def test_internal_sources_never_feed_insights(
    client: TestClient, admin_headers: dict[str, str], auto_publish: None
) -> None:
    _radar_with_two_documents(client, admin_headers)
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Interne data (OK)",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    ).json()
    secret = "Intern hemmelig tekst om OK's indbakke med 359 bounces."
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("intern.txt", (secret + " " + DOC_TEXT).encode(), "text/plain")},
        headers=admin_headers,
    )
    app.dependency_overrides[ai_provider_dep] = lambda: FakeProvider()
    client.post(
        f"/api/v1/review/documents/{upload.json()['document']['id']}/process",
        headers=admin_headers,
    )
    app.dependency_overrides.pop(ai_provider_dep, None)
    # Kilden blev siden markeret intern: dens claims må aldrig indgå.
    client.patch(
        f"/api/v1/sources/{source['id']}",
        json={"access_class": "restricted"},
        headers=admin_headers,
    )

    provider = FakeProvider()
    _generate(client, admin_headers, provider)
    prompt = provider.prompts[provider.calls.index("insight_synthesis")]
    assert "Interne data (OK)" not in prompt
    assert prompt.count("\n[") == 4  # kun de fire markedsclaims


def test_rejected_evidence_removes_the_insight(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session_factory: Any,
    auto_publish: None,
) -> None:
    import uuid

    from app.enums import ReviewStatus
    from app.models_claims import Claim

    _radar_with_two_documents(client, admin_headers)
    _generate(client, admin_headers, FakeProvider(insights={"insights": [INSIGHT]}))
    [insight] = client.get("/api/v1/insights", headers=admin_headers).json()["items"]

    # Trækkes claims fra det ene dokument tilbage, er der kun ét dokument
    # tilbage — så bærer evidensen ikke længere en indsigt.
    with db_session_factory() as db:
        for evidence in insight["evidence"]:
            if evidence["vendor_source"]:
                claim = db.get(Claim, uuid.UUID(evidence["claim_id"]))
                claim.review_status = ReviewStatus.rejected
        db.commit()

    assert client.get("/api/v1/insights", headers=admin_headers).json()["items"] == []


def test_only_admin_generates(client: TestClient, reviewer_headers: dict[str, str]) -> None:
    response = _generate(client, reviewer_headers, FakeProvider())
    assert response.status_code == 403


def test_run_with_new_knowledge_refreshes_insights(
    client: TestClient, admin_headers: dict[str, str], auto_publish: None
) -> None:
    from app.routes.runs import run_ai_provider

    _upload_document(client, admin_headers)
    provider = FakeProvider()
    app.dependency_overrides[run_ai_provider] = lambda: provider
    try:
        run = client.post("/api/v1/runs", json={"force_all": True}, headers=admin_headers)
    finally:
        app.dependency_overrides.pop(run_ai_provider, None)
    assert run.status_code == 202, run.text
    assert "insight_synthesis" in provider.calls
    assert client.get("/api/v1/insights", headers=admin_headers).json()["generated_at"]
