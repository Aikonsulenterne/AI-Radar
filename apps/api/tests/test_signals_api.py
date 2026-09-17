"""Signal-publicering, provenance og dashboard (Slice 3)."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import _upload_document


def _setup_reviewed_claims(
    client: TestClient, admin_headers: dict[str, str]
) -> tuple[str, list[dict[str, Any]]]:
    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    claims = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()[
        "claims"
    ]
    return document_id, claims


def test_publish_requires_approved_claims(
    client: TestClient, admin_headers: dict[str, str], fake_provider: object
) -> None:
    _, claims = _setup_reviewed_claims(client, admin_headers)

    created = client.post(
        "/api/v1/signals",
        json={
            "title": "Agent Assist vinder frem i danske banker",
            "summary": "Dokumenteret adoption af Agent Assist i kundeservice.",
            "analysis": "Mønstret ligner tidligere skandinaviske cases.",
            "recommendation": "Undersøg relevans for OK Kundecenter.",
            "documentation_level": "limited",
            "claim_ids": [c["id"] for c in claims],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    signal_id = created.json()["id"]
    assert created.json()["status"] == "draft"
    assert created.json()["claim_count"] == len(claims)

    # Publicering afvises, mens claims stadig er proposed.
    refused = client.post(f"/api/v1/signals/{signal_id}/publish", headers=admin_headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "unapproved_claims"

    for claim in claims:
        approve = client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)
        assert approve.status_code == 200

    published = client.post(f"/api/v1/signals/{signal_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None


def test_reader_sees_only_published_signals(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    _, claims = _setup_reviewed_claims(client, admin_headers)
    for claim in claims:
        client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)

    draft = client.post(
        "/api/v1/signals",
        json={
            "title": "Kladdesignal",
            "summary": "Ikke publiceret endnu.",
            "documentation_level": "early",
            "claim_ids": [claims[0]["id"]],
        },
        headers=admin_headers,
    ).json()

    # Reader må ikke oprette signaler og ser ikke kladder.
    forbidden = client.post(
        "/api/v1/signals",
        json={"title": "x", "summary": "y", "documentation_level": "early"},
        headers=reader_headers,
    )
    assert forbidden.status_code == 403

    listed = client.get("/api/v1/signals", headers=reader_headers).json()
    assert listed["total"] == 0
    assert client.get(f"/api/v1/signals/{draft['id']}", headers=reader_headers).status_code == 404

    client.post(f"/api/v1/signals/{draft['id']}/publish", headers=admin_headers)
    listed_after = client.get("/api/v1/signals", headers=reader_headers).json()
    assert listed_after["total"] == 1

    detail = client.get(f"/api/v1/signals/{draft['id']}", headers=reader_headers)
    assert detail.status_code == 200
    body = detail.json()
    # Provenance: claims med evidensuddrag og relaterede entities.
    assert body["claims"][0]["evidence"][0]["supporting_excerpt"]
    assert body["companies"][0]["name"] == "Danske Bank"


def test_dashboard_counts(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    _, claims = _setup_reviewed_claims(client, admin_headers)
    for claim in claims:
        client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)
    signal = client.post(
        "/api/v1/signals",
        json={
            "title": "Publiceret signal",
            "summary": "Resumé.",
            "documentation_level": "limited",
            "claim_ids": [c["id"] for c in claims],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/api/v1/signals/{signal['id']}/publish", headers=admin_headers)

    dashboard = client.get("/api/v1/dashboard", headers=reader_headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["published_signals"] == 1
    assert body["approved_claims"] == len(claims)
    assert body["companies_with_claims"] == 1
    assert body["latest_signals"][0]["title"] == "Publiceret signal"


def test_archived_signal_via_patch_and_claim_listing(
    client: TestClient, admin_headers: dict[str, str], fake_provider: object
) -> None:
    _, claims = _setup_reviewed_claims(client, admin_headers)
    client.post(f"/api/v1/review/claims/{claims[0]['id']}/approve", headers=admin_headers)

    approved = client.get(
        "/api/v1/review/claims?review_status=approved", headers=admin_headers
    ).json()
    assert approved["total"] == 1

    signal = client.post(
        "/api/v1/signals",
        json={
            "title": "Arkivtest",
            "summary": "Resumé.",
            "documentation_level": "early",
            "claim_ids": [claims[0]["id"]],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/api/v1/signals/{signal['id']}/publish", headers=admin_headers)

    archived = client.patch(
        f"/api/v1/signals/{signal['id']}", json={"status": "archived"}, headers=admin_headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
