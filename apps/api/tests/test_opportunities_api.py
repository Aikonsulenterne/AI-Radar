"""Opportunities: kandidat, godkendelse og statuspipeline (Slice 5)."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import _upload_document


def _published_signal(client: TestClient, admin_headers: dict[str, str]) -> dict[str, Any]:
    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    claims = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()[
        "claims"
    ]
    for claim in claims:
        client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)
    signal = client.post(
        "/api/v1/signals",
        json={
            "title": "Agent Assist i banksektoren",
            "summary": "Dokumenteret adoption.",
            "documentation_level": "limited",
            "claim_ids": [c["id"] for c in claims],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/api/v1/signals/{signal['id']}/publish", headers=admin_headers)
    return {"signal": signal, "claims": claims}


def test_opportunity_candidate_flow(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    setup = _published_signal(client, admin_headers)
    problem_id = client.get("/api/v1/problems", headers=reader_headers).json()["items"][0]["id"]

    # Reader kan se, men ikke oprette.
    forbidden = client.post(
        "/api/v1/opportunities",
        json={
            "title": "x",
            "problem_id": problem_id,
            "relevance_hypothesis": "y",
            "recommended_next_action": "z",
        },
        headers=reader_headers,
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/v1/opportunities",
        json={
            "title": "Agent Assist til mailtunge teams",
            "problem_id": problem_id,
            "relevance_hypothesis": (
                "Dokumenteret bankcase kan overføres til OK's mailhåndtering."
            ),
            "evidence_gaps": "Ingen dansk energi-case dokumenteret endnu.",
            "recommended_next_action": "Undersøg leverandører og datakrav.",
            "signal_ids": [setup["signal"]["id"]],
            "claim_ids": [setup["claims"][0]["id"]],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    opportunity = created.json()
    assert opportunity["status"] == "identified"
    assert opportunity["approved"] is False
    assert opportunity["problem_name"] == "Store mailmængder"
    assert opportunity["signal_count"] == 1

    # Status kan ikke rykkes uden menneskelig godkendelse.
    refused = client.patch(
        f"/api/v1/opportunities/{opportunity['id']}",
        json={"status": "investigating"},
        headers=admin_headers,
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "not_approved"

    approved = client.post(
        f"/api/v1/opportunities/{opportunity['id']}/approve", headers=admin_headers
    )
    assert approved.status_code == 200
    assert approved.json()["approved"] is True

    moved = client.patch(
        f"/api/v1/opportunities/{opportunity['id']}",
        json={"status": "investigating"},
        headers=admin_headers,
    )
    assert moved.status_code == 200
    assert moved.json()["status"] == "investigating"

    detail = client.get(f"/api/v1/opportunities/{opportunity['id']}", headers=reader_headers).json()
    assert detail["signals"][0]["title"] == "Agent Assist i banksektoren"
    assert detail["claims"][0]["evidence"][0]["supporting_excerpt"]

    listed = client.get("/api/v1/opportunities", headers=reader_headers).json()
    assert listed["total"] == 1


def test_opportunity_requires_valid_problem(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/opportunities",
        json={
            "title": "Ugyldigt problem",
            "problem_id": "00000000-0000-0000-0000-000000000000",
            "relevance_hypothesis": "h",
            "recommended_next_action": "n",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
