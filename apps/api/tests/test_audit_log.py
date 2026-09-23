"""Audit-log: hvem traf hvilken beslutning, og hvad ændrede sig (Technical Master §18)."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import _upload_document


def _events(client: TestClient, headers: dict[str, str], **params: Any) -> list[dict[str, Any]]:
    response = client.get("/api/v1/audit", headers=headers, params=params)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def test_review_decisions_are_audited_with_actor_and_edits(
    client: TestClient, admin_headers: dict[str, str], fake_provider: object
) -> None:
    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    claims = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()[
        "claims"
    ]

    # Godkend ét claim med en rettelse og afvis et andet.
    client.post(
        f"/api/v1/review/claims/{claims[0]['id']}/approve",
        json={"edits": {"object_text": "Rettet af reviewer"}},
        headers=admin_headers,
    )
    client.post(f"/api/v1/review/claims/{claims[1]['id']}/reject", headers=admin_headers)

    approved = _events(client, admin_headers, entity_type="claim", entity_id=claims[0]["id"])
    assert [event["action"] for event in approved] == ["approved"]
    assert approved[0]["actor_user_id"] is not None
    assert approved[0]["changes"]["status"] == "approved_with_edits"
    # Rettelsen er sporet med før og efter (§18: rettelser før godkendelse).
    assert approved[0]["changes"]["rettelser"]["object_text"]["til"] == "Rettet af reviewer"

    rejected = _events(client, admin_headers, entity_type="claim", entity_id=claims[1]["id"])
    assert [event["action"] for event in rejected] == ["rejected"]

    processed = _events(client, admin_headers, entity_type="document", entity_id=document_id)
    assert processed[0]["action"] == "processed"
    assert processed[0]["changes"]["claims_oprettet"] >= 1


def test_source_changes_are_audited_with_before_and_after(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Kilde",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    ).json()
    client.patch(
        f"/api/v1/sources/{source['id']}",
        json={"name": "Kilde med nyt navn"},
        headers=admin_headers,
    )

    events = _events(client, admin_headers, entity_type="source", entity_id=source["id"])
    assert [event["action"] for event in events] == ["updated", "created"]
    assert events[0]["changes"]["name"] == {"fra": "Kilde", "til": "Kilde med nyt navn"}
    # Correlation id kobler rækken til den request, der udløste den.
    assert events[0]["request_id"]


def test_audit_log_requires_admin(
    client: TestClient, reviewer_headers: dict[str, str], reader_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/audit", headers=reader_headers).status_code == 403
    assert client.get("/api/v1/audit", headers=reviewer_headers).status_code == 403


def test_long_values_are_truncated_in_the_trail(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """Loggen er et spor, ikke en kopi af indholdet."""
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Kilde",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    ).json()
    client.patch(
        f"/api/v1/sources/{source['id']}",
        json={"notes": "x" * 2000},
        headers=admin_headers,
    )

    events = _events(client, admin_headers, entity_type="source", entity_id=source["id"])
    stored = events[0]["changes"]["notes"]["til"]
    assert len(stored) < 600
    assert stored.endswith("…")
