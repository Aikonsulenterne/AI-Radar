"""Pipeline- og review-tests med fake AI-provider (fixtures, ingen netkald)."""

from fastapi.testclient import TestClient

from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import DOC_TEXT, FakeProvider, _upload_document


def test_process_creates_claims_with_evidence(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    document_id = _upload_document(client, admin_headers)

    result = client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "review_pending"
    assert body["claims_created"] == 2
    # Claimet med et uddrag, der ikke findes ordret i teksten, kasseres.
    assert body["claims_skipped"] == 1
    assert fake_provider.calls == ["relevance_classification", "claim_extraction"]

    detail = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert len(detail["claims"]) == 2
    adoption = next(c for c in detail["claims"] if c["claim_type"] == "adoption")
    assert adoption["subject_name"] == "Danske Bank"
    assert adoption["review_status"] == "proposed"
    assert adoption["created_by"] == "ai"
    excerpt = adoption["evidence"][0]
    assert excerpt["supporting_excerpt"] in DOC_TEXT
    assert (
        DOC_TEXT[excerpt["excerpt_start"] : excerpt["excerpt_end"]]
        == (excerpt["supporting_excerpt"])
    )


def test_irrelevant_document_is_marked_and_skips_extraction(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    provider = FakeProvider(relevance={"relevant": False, "reason": "Ikke om AI"})
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        document_id = _upload_document(client, admin_headers)
        result = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
        assert result.status_code == 200
        assert result.json()["status"] == "classified_irrelevant"
        assert provider.calls == ["relevance_classification"]
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)


def test_schema_failure_after_retry_marks_document_failed(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    provider = FakeProvider(invalid_json=True)
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        document_id = _upload_document(client, admin_headers)
        result = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
        assert result.status_code == 200
        assert result.json()["status"] == "failed"
        # Én kontrolleret retry: relevans kaldes præcis to gange.
        assert provider.calls == ["relevance_classification", "relevance_classification"]
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)


def test_process_without_ai_configuration_returns_503(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    document_id = _upload_document(client, admin_headers)
    result = client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "ai_not_configured"


def test_entity_resolution_reuses_company_across_documents(
    client: TestClient, admin_headers: dict[str, str], fake_provider: FakeProvider
) -> None:
    first_doc = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{first_doc}/process", headers=admin_headers)

    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Andet medie",
            "source_type": "research",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=admin_headers,
    ).json()
    other_text = DOC_TEXT + " Analysen er ny."
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("analyse.txt", other_text.encode(), "text/plain")},
        headers=admin_headers,
    )
    second_doc = upload.json()["document"]["id"]
    client.post(f"/api/v1/review/documents/{second_doc}/process", headers=admin_headers)

    first_claims = client.get(
        f"/api/v1/review/documents/{first_doc}", headers=admin_headers
    ).json()["claims"]
    second_claims = client.get(
        f"/api/v1/review/documents/{second_doc}", headers=admin_headers
    ).json()["claims"]
    assert first_claims and second_claims
    assert first_claims[0]["subject_entity_id"] == second_claims[0]["subject_entity_id"]
    # Samme udsagn i to dokumenter → duplicate-kandidat til review.
    candidates = second_claims[0]["possible_duplicates"]
    assert first_claims[0]["id"] in [candidate["id"] for candidate in candidates]
    # Kandidaten vises med indhold, så relationen kan vurderes direkte.
    assert candidates[0]["subject_name"]
    assert candidates[0]["review_status"]


def test_review_actions_approve_edit_reject_complete(
    client: TestClient,
    admin_headers: dict[str, str],
    reviewer_headers: dict[str, str],
    reader_headers: dict[str, str],
    fake_provider: FakeProvider,
) -> None:
    document_id = _upload_document(client, admin_headers)
    client.post(f"/api/v1/review/documents/{document_id}/process", headers=admin_headers)
    claims = client.get(f"/api/v1/review/documents/{document_id}", headers=reviewer_headers).json()[
        "claims"
    ]
    adoption = next(c for c in claims if c["claim_type"] == "adoption")
    effect = next(c for c in claims if c["claim_type"] == "effect")

    # Reader må ikke reviewe.
    assert (
        client.post(
            f"/api/v1/review/claims/{adoption['id']}/approve", headers=reader_headers
        ).status_code
        == 403
    )

    approved = client.post(
        f"/api/v1/review/claims/{adoption['id']}/approve", headers=reviewer_headers
    )
    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["reviewed_at"] is not None

    # Edit and approve → approved_with_edits.
    edited = client.post(
        f"/api/v1/review/claims/{effect['id']}/approve",
        json={"edits": {"object_text": "20 % lavere efterbehandlingstid"}},
        headers=reviewer_headers,
    )
    assert edited.status_code == 200
    assert edited.json()["review_status"] == "approved_with_edits"
    assert edited.json()["object_text"] == "20 % lavere efterbehandlingstid"

    # Allerede afgjort claim kan ikke afgøres igen.
    again = client.post(f"/api/v1/review/claims/{adoption['id']}/reject", headers=reviewer_headers)
    assert again.status_code == 409

    complete = client.post(
        f"/api/v1/review/documents/{document_id}/complete", headers=reviewer_headers
    )
    assert complete.status_code == 200
    assert complete.json()["processing_status"] == "reviewed"
