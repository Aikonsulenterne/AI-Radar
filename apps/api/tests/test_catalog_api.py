"""Companies, technologies og adoption cases (Slice 4)."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import _upload_document


def _reviewed_company_claims(
    client: TestClient, admin_headers: dict[str, str], approve: bool = True
) -> list[dict[str, Any]]:
    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    claims = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()[
        "claims"
    ]
    if approve:
        for claim in claims:
            client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)
    return claims


def test_company_profile_shows_only_approved_claims(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    claims = _reviewed_company_claims(client, admin_headers, approve=False)
    # Godkend kun det ene claim.
    client.post(f"/api/v1/review/claims/{claims[0]['id']}/approve", headers=admin_headers)

    companies = client.get("/api/v1/companies", headers=reader_headers).json()
    assert companies["total"] == 1
    company = companies["items"][0]
    assert company["name"] == "Danske Bank"
    assert company["approved_claim_count"] == 1
    # country_code er ikke dokumenteret i kilden og er derfor null.
    assert company["country_code"] is None

    detail = client.get(f"/api/v1/companies/{company['id']}", headers=reader_headers).json()
    assert len(detail["claims"]) == 1
    assert detail["claims"][0]["review_status"] == "approved"


def test_technology_profile_lists_adopting_companies(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    _reviewed_company_claims(client, admin_headers)

    technologies = client.get("/api/v1/technologies", headers=reader_headers).json()
    agent_assist = next(t for t in technologies["items"] if t["name"] == "Agent Assist")
    assert agent_assist["adopting_company_count"] == 1
    assert agent_assist["horizon"] in ("now", "next", "horizon")

    detail = client.get(f"/api/v1/technologies/{agent_assist['id']}", headers=reader_headers).json()
    assert detail["companies"][0]["name"] == "Danske Bank"
    assert detail["claims"][0]["predicate"] == "USES_CAPABILITY"


def test_case_publish_flow_and_reader_visibility(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: object,
) -> None:
    claims = _reviewed_company_claims(client, admin_headers, approve=False)
    company_id = claims[0]["subject_entity_id"]

    case = client.post(
        "/api/v1/adoption-cases",
        json={
            "company_id": company_id,
            "title": "Danske Bank: Agent Assist i kundeservice",
            "summary": "Potentiel læring: relevant for mailtunge funktioner.",
            "claim_ids": [c["id"] for c in claims],
        },
        headers=admin_headers,
    )
    assert case.status_code == 201, case.text
    case_id = case.json()["id"]

    # Kan ikke publiceres med uafklarede claims.
    refused = client.post(f"/api/v1/adoption-cases/{case_id}/publish", headers=admin_headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "unapproved_claims"

    # Reader ser ikke kladden.
    assert client.get("/api/v1/adoption-cases", headers=reader_headers).json()["total"] == 0

    for claim in claims:
        client.post(f"/api/v1/review/claims/{claim['id']}/approve", headers=admin_headers)
    published = client.post(f"/api/v1/adoption-cases/{case_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    listed = client.get("/api/v1/adoption-cases", headers=reader_headers).json()
    assert listed["total"] == 1
    facts = listed["items"][0]["facts"]
    # Afledte fakta: capability og effekt er dokumenteret; stage/vendor er ikke.
    assert facts["capability"] == "Agent Assist"
    assert facts["effect"] == "20 procent lavere efterbehandlingstid"
    assert facts["stage"] is None
    assert facts["vendor"] is None

    detail = client.get(f"/api/v1/adoption-cases/{case_id}", headers=reader_headers).json()
    assert detail["company_name"] == "Danske Bank"
    assert detail["technologies"] == ["Agent Assist"]
    assert detail["claims"][0]["evidence"][0]["supporting_excerpt"]


def test_case_claims_must_belong_to_company(
    client: TestClient, admin_headers: dict[str, str], fake_provider: object
) -> None:
    claims = _reviewed_company_claims(client, admin_headers)
    other_company = client.post(
        "/api/v1/sources",
        json={
            "name": "Dummy",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    )
    assert other_company.status_code == 201
    # Opret en case for en anden (ikke-eksisterende) virksomhed med fremmede claims.
    response = client.post(
        "/api/v1/adoption-cases",
        json={
            "company_id": "00000000-0000-0000-0000-000000000000",
            "title": "Forkert virksomhed",
            "claim_ids": [claims[0]["id"]],
        },
        headers=admin_headers,
    )
    assert response.status_code == 422
