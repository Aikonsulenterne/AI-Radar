"""AI-foreslåede opportunity-kandidater: forslaget er en kandidat, ikke en beslutning."""

from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import FakeProvider
from tests.test_opportunities_api import _published_signal

PROPOSAL = {
    "proposal": {
        "title": "Agent Assist til mailtunge teams",
        "problem_name": "Store mailmængder",
        "relevance_hypothesis": "Bankcasen peger på samme flaskehals som OK's mailhåndtering.",
        "evidence_gaps": "Ingen dansk energi-case er dokumenteret.",
        "recommended_next_action": "Afklar hvilke mailtyper der kan afgrænses.",
    },
    "reason": "",
}


def _use_provider(provider: FakeProvider) -> None:
    app.dependency_overrides[ai_provider_dep] = lambda: provider


def _propose(client: TestClient, headers: dict[str, str], signal_id: str) -> Any:
    return client.post(
        "/api/v1/opportunities/propose", json={"signal_id": signal_id}, headers=headers
    )


def test_ai_proposal_lands_as_unapproved_candidate(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    setup = _published_signal(client, admin_headers)
    provider = FakeProvider(opportunity=PROPOSAL)
    _use_provider(provider)

    response = _propose(client, admin_headers, setup["signal"]["id"])
    assert response.status_code == 201, response.text
    opportunity = response.json()

    assert opportunity["proposed_by_ai"] is True
    assert opportunity["proposal_prompt_version"] == "1.0.0"
    assert opportunity["approved"] is False
    assert opportunity["status"] == "identified"
    assert opportunity["problem_name"] == "Store mailmængder"
    # Forslaget er koblet til signalet og dets godkendte claims.
    assert opportunity["signal_count"] == 1
    assert opportunity["claim_count"] == len(setup["claims"])

    # Et forslag kan ikke rykke status, før et menneske har godkendt det.
    refused = client.patch(
        f"/api/v1/opportunities/{opportunity['id']}",
        json={"status": "investigating"},
        headers=admin_headers,
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "not_approved"

    # Modellen fik kun godkendte fakta og problemlisten at arbejde med.
    prompt = provider.prompts[-1]
    assert "APPROVED FACTS" in prompt
    assert "Store mailmængder" in prompt


def test_proposal_is_rejected_when_model_finds_no_problem(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    setup = _published_signal(client, admin_headers)
    _use_provider(FakeProvider(opportunity={"proposal": None, "reason": "Ingen relevant kobling."}))

    response = _propose(client, admin_headers, setup["signal"]["id"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_opportunity"
    assert client.get("/api/v1/opportunities", headers=admin_headers).json()["total"] == 0


def test_unknown_problem_name_does_not_create_taxonomy_entries(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    setup = _published_signal(client, admin_headers)
    proposal = {"proposal": dict(PROPOSAL["proposal"], problem_name="Opfundet problem")}
    _use_provider(FakeProvider(opportunity=proposal))

    response = _propose(client, admin_headers, setup["signal"]["id"])
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "unknown_problem"

    problems = client.get("/api/v1/problems", headers=admin_headers).json()
    assert all(item["name"] != "Opfundet problem" for item in problems["items"])


def test_proposal_requires_published_signal_and_reviewer_role(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: FakeProvider,
) -> None:
    _use_provider(FakeProvider(opportunity=PROPOSAL))
    draft = client.post(
        "/api/v1/signals",
        json={
            "title": "Kladde",
            "summary": "Endnu ikke publiceret.",
            "documentation_level": "limited",
            "claim_ids": [],
        },
        headers=admin_headers,
    ).json()

    refused = _propose(client, admin_headers, draft["id"])
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "invalid_status"

    forbidden = _propose(client, reader_headers, draft["id"])
    assert forbidden.status_code == 403
