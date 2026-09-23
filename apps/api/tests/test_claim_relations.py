"""Dubletter og konflikter: reviewer sætter relationen, intet claim overskrives."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import FakeProvider, _upload_document


def _two_documents_with_same_claim(
    client: TestClient, headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Samme udsagn i to dokumenter giver en deterministisk dublet-kandidat."""
    claims: list[dict[str, Any]] = []
    for _ in range(2):
        document_id = _upload_document(client, headers)
        client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)
        found = client.get(f"/api/v1/review/documents/{document_id}", headers=headers).json()[
            "claims"
        ]
        assert found
        claims.append(found[0])
    return claims[0], claims[1]


def test_merging_a_duplicate_keeps_both_claims(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    keeper, duplicate = _two_documents_with_same_claim(client, admin_headers)

    response = client.post(
        f"/api/v1/review/claims/{keeper['id']}/relate",
        json={"related_claim_id": duplicate["id"], "relation": "supersedes"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["relations"][0]["relation"] == "supersedes"
    assert body["relations"][0]["related_claim_id"] == duplicate["id"]
    # Det beholdte claim er uændret.
    assert body["lifecycle_status"] == "current"

    # Dubletten består — den er markeret, ikke slettet (Technical Master §15).
    claims = client.get("/api/v1/review/claims", headers=admin_headers).json()["items"]
    by_id = {claim["id"]: claim for claim in claims}
    assert by_id[duplicate["id"]]["lifecycle_status"] == "superseded"
    assert by_id[keeper["id"]]["lifecycle_status"] == "current"


def test_marking_a_contradiction_flags_both_without_resolving(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    first, second = _two_documents_with_same_claim(client, admin_headers)

    response = client.post(
        f"/api/v1/review/claims/{first['id']}/relate",
        json={"related_claim_id": second["id"], "relation": "contradicts"},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text

    claims = client.get("/api/v1/review/claims", headers=admin_headers).json()["items"]
    lifecycles = {claim["id"]: claim["lifecycle_status"] for claim in claims}
    # Begge markeres — MVP afgør ikke selv, hvilket claim der er rigtigt.
    assert lifecycles[first["id"]] == "contradicted"
    assert lifecycles[second["id"]] == "contradicted"


def test_relation_is_validated(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: FakeProvider,
) -> None:
    first, second = _two_documents_with_same_claim(client, admin_headers)

    same = client.post(
        f"/api/v1/review/claims/{first['id']}/relate",
        json={"related_claim_id": first["id"], "relation": "supersedes"},
        headers=admin_headers,
    )
    assert same.status_code == 422

    missing = client.post(
        f"/api/v1/review/claims/{first['id']}/relate",
        json={
            "related_claim_id": "00000000-0000-0000-0000-000000000000",
            "relation": "supersedes",
        },
        headers=admin_headers,
    )
    assert missing.status_code == 404

    body = {"related_claim_id": second["id"], "relation": "supports"}
    assert (
        client.post(
            f"/api/v1/review/claims/{first['id']}/relate", json=body, headers=reader_headers
        ).status_code
        == 403
    )

    assert (
        client.post(
            f"/api/v1/review/claims/{first['id']}/relate", json=body, headers=admin_headers
        ).status_code
        == 200
    )
    # Samme par kan ikke relateres to gange.
    repeat = client.post(
        f"/api/v1/review/claims/{first['id']}/relate", json=body, headers=admin_headers
    )
    assert repeat.status_code == 409
    assert repeat.json()["error"]["code"] == "already_related"


def test_relation_is_audited(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    first, second = _two_documents_with_same_claim(client, admin_headers)
    client.post(
        f"/api/v1/review/claims/{first['id']}/relate",
        json={"related_claim_id": second["id"], "relation": "contradicts"},
        headers=admin_headers,
    )

    events = client.get(
        "/api/v1/audit",
        headers=admin_headers,
        params={"entity_type": "claim", "entity_id": first["id"]},
    ).json()["items"]
    assert events[0]["action"] == "related"
    assert events[0]["changes"]["relation"] == "contradicts"
