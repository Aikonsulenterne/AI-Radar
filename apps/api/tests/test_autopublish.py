"""Fuldt automatisk publicering (AUTO_PUBLISH).

Med flaget slået til godkender AI sine egne claims og publicerer case og
signal uden menneskelig kontrol — altid markeret som AI-publiceret. Slået
fra gælder review-flowet uændret.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.routes.runs import run_ai_provider
from tests.conftest import SIGNAL_RESPONSE, _upload_document


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _process(client: TestClient, headers: dict[str, str], document_id: str) -> Any:
    return client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)


def test_processing_publishes_claims_case_and_signal(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any, auto_publish: None
) -> None:
    document_id = _upload_document(client, admin_headers)

    response = _process(client, admin_headers, document_id)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "reviewed"
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["claims"]
    assert all(claim["review_status"] == "approved" for claim in document["claims"])
    assert all(claim["auto_approved"] for claim in document["claims"])

    cases = client.get("/api/v1/adoption-cases", headers=admin_headers).json()["items"]
    assert len(cases) == 1
    assert cases[0]["status"] == "published"
    assert cases[0]["auto_published"] is True

    signals = client.get("/api/v1/signals", headers=admin_headers).json()["items"]
    assert len(signals) == 1
    signal = signals[0]
    assert signal["status"] == "published"
    assert signal["auto_published"] is True
    assert signal["title"] == SIGNAL_RESPONSE["title"]
    assert signal["claim_count"] == len(document["claims"])
    # Mediekilde, én kilde: aldrig "stærk" dokumentation.
    assert signal["documentation_level"] == "limited"

    dashboard = client.get("/api/v1/dashboard", headers=admin_headers).json()
    assert dashboard["published_signals"] == 1


def test_without_flag_claims_wait_for_a_human(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any
) -> None:
    document_id = _upload_document(client, admin_headers)

    assert _process(client, admin_headers, document_id).json()["status"] == "review_pending"
    assert client.get("/api/v1/signals", headers=admin_headers).json()["items"] == []
    assert "signal_draft" not in fake_provider.calls


def test_failed_signal_draft_still_publishes_claims_and_case(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any, auto_publish: None
) -> None:
    original = fake_provider.complete_text

    def no_signal(**kwargs: Any) -> str:
        if kwargs["prompt_id"] == "signal_draft":
            return "ikke json"
        result: str = original(**kwargs)
        return result

    fake_provider.complete_text = no_signal
    document_id = _upload_document(client, admin_headers)

    assert _process(client, admin_headers, document_id).json()["status"] == "reviewed"
    assert client.get("/api/v1/signals", headers=admin_headers).json()["items"] == []
    cases = client.get("/api/v1/adoption-cases", headers=admin_headers).json()["items"]
    assert [case["status"] for case in cases] == ["published"]


def test_run_publishes_documents_waiting_for_review(
    client: TestClient,
    admin_headers: dict[str, str],
    fake_provider: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Behandlet, før automatisk publicering blev slået til.
    document_id = _upload_document(client, admin_headers)
    assert _process(client, admin_headers, document_id).json()["status"] == "review_pending"

    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    app.dependency_overrides[run_ai_provider] = lambda: fake_provider
    try:
        run = client.post("/api/v1/runs", headers=admin_headers).json()
        run = client.get(f"/api/v1/runs/{run['id']}", headers=admin_headers).json()
    finally:
        app.dependency_overrides.pop(run_ai_provider, None)
        get_settings.cache_clear()

    assert run["status"] == "succeeded"
    assert run["documents_published"] == 1
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["processing_status"] == "reviewed"
    signals = client.get("/api/v1/signals", headers=admin_headers).json()["items"]
    assert len(signals) == 1

    # En ny kørsel publicerer ikke det samme dokument igen.
    app.dependency_overrides[run_ai_provider] = lambda: fake_provider
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    try:
        again = client.post("/api/v1/runs", headers=admin_headers).json()
        again = client.get(f"/api/v1/runs/{again['id']}", headers=admin_headers).json()
    finally:
        app.dependency_overrides.pop(run_ai_provider, None)
        get_settings.cache_clear()
    assert again["documents_published"] == 0
    assert len(client.get("/api/v1/signals", headers=admin_headers).json()["items"]) == 1
