"""Automatiske kørsler: ugentlig udløser (worker-token) og "Kør nu" (Admin).

TestClient udfører FastAPI's baggrundsopgaver, før kaldet returnerer, så
kørslen er færdig, når POST /runs har svaret.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.enums import RunStatus
from app.ingestion.run import RunDocument, SourceRunOutcome
from app.main import app
from app.models_runs import WorkerRun
from app.routes.runs import run_ai_provider
from tests.conftest import SessionFactory, _upload_document

TOKEN = "hemmeligt-testtoken"


@pytest.fixture()
def worker_token(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("WORKER_TRIGGER_TOKEN", TOKEN)
    get_settings.cache_clear()
    yield TOKEN
    get_settings.cache_clear()


@pytest.fixture()
def run_provider(fake_provider: Any) -> Any:
    app.dependency_overrides[run_ai_provider] = lambda: fake_provider
    yield fake_provider
    app.dependency_overrides.pop(run_ai_provider, None)


def _web_source(client: TestClient, headers: dict[str, str], frequency: str) -> str:
    response = client.post(
        "/api/v1/sources",
        json={
            "name": f"Kilde {frequency}",
            "source_type": "media",
            "retrieval_method": "web_fetch",
            "access_class": "public",
            "endpoint_url": "https://example.com/artikel",
            "frequency": frequency,
        },
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text
    source_id: str = response.json()["id"]
    return source_id


def test_run_now_processes_new_documents(
    client: TestClient, admin_headers: dict[str, str], run_provider: Any
) -> None:
    document_id = _upload_document(client, admin_headers)

    response = client.post("/api/v1/runs", json={"force_all": True}, headers=admin_headers)

    assert response.status_code == 202, response.text
    run = client.get(f"/api/v1/runs/{response.json()['id']}", headers=admin_headers).json()
    assert run["status"] == "succeeded"
    assert run["trigger"] == "manual"
    assert run["documents_processed"] == 1
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["processing_status"] == "review_pending"


def test_scheduled_run_fetches_only_due_sources(
    client: TestClient,
    admin_headers: dict[str, str],
    worker_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    weekly = _web_source(client, admin_headers, "weekly")
    _web_source(client, admin_headers, "manual")
    fetched: list[str] = []

    def fake_fetch(db: Any, storage: Any, source: Any, **_: Any) -> SourceRunOutcome:
        fetched.append(str(source.id))
        return SourceRunOutcome(documents=[RunDocument(document=None, created=True)])  # type: ignore[arg-type]

    monkeypatch.setattr("app.worker.run_source_fetch", fake_fetch)

    response = client.post(
        "/api/v1/runs", json={"force_all": False}, headers={"X-Worker-Token": worker_token}
    )

    assert response.status_code == 202, response.text
    run = client.get(
        f"/api/v1/runs/{response.json()['id']}", headers={"X-Worker-Token": worker_token}
    ).json()
    assert run["trigger"] == "schedule"
    assert run["status"] == "succeeded"
    # Manuelle kilder hentes kun, når et menneske beder om det.
    assert fetched == [weekly]
    assert run["documents_created"] == 1
    # Uden AI-konfiguration hentes der stadig, men intet AI-behandles.
    assert run["processing_skipped_no_ai"] is True

    # Kilden er nu hentet og ikke forfalden igen før om en uge.
    second = client.post(
        "/api/v1/runs", json={"force_all": False}, headers={"X-Worker-Token": worker_token}
    )
    assert second.status_code == 202
    assert fetched == [weekly]


def test_wrong_or_missing_token_is_rejected(client: TestClient, worker_token: str) -> None:
    assert client.post("/api/v1/runs", headers={"X-Worker-Token": "forkert"}).status_code == 401
    assert client.get("/api/v1/runs").status_code == 401


def test_token_is_disabled_when_not_configured(client: TestClient) -> None:
    response = client.post("/api/v1/runs", headers={"X-Worker-Token": ""})
    assert response.status_code == 401


def test_reviewer_cannot_start_a_run(client: TestClient, reviewer_headers: dict[str, str]) -> None:
    assert client.post("/api/v1/runs", headers=reviewer_headers).status_code == 403


def test_only_one_run_at_a_time(
    client: TestClient, admin_headers: dict[str, str], db_session_factory: SessionFactory
) -> None:
    with db_session_factory() as db:
        db.add(WorkerRun(trigger="manual", status=RunStatus.running, started_at=datetime.now(UTC)))
        db.commit()

    response = client.post("/api/v1/runs", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "run_in_progress"


def test_stale_running_run_does_not_block(
    client: TestClient, admin_headers: dict[str, str], db_session_factory: SessionFactory
) -> None:
    stale_id = uuid.uuid4()
    with db_session_factory() as db:
        db.add(
            WorkerRun(
                id=stale_id,
                trigger="manual",
                status=RunStatus.running,
                started_at=datetime.now(UTC) - timedelta(hours=7),
            )
        )
        db.commit()

    response = client.post("/api/v1/runs", headers=admin_headers)

    assert response.status_code == 202
    stale = client.get(f"/api/v1/runs/{stale_id}", headers=admin_headers).json()
    assert stale["status"] == "failed"


def test_rejected_ai_key_fails_the_run_with_a_reason(
    client: TestClient, admin_headers: dict[str, str], run_provider: Any
) -> None:
    from app.ai.provider import AIProviderRejected

    document_id = _upload_document(client, admin_headers)

    def rejected(**_: Any) -> str:
        raise AIProviderRejected(401)

    run_provider.complete_text = rejected

    response = client.post("/api/v1/runs", headers=admin_headers)

    run = client.get(f"/api/v1/runs/{response.json()['id']}", headers=admin_headers).json()
    assert run["status"] == "failed"
    assert "AI_PROVIDER_API_KEY" in run["error_message_safe"]
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["processing_status"] == "normalized"


def test_runs_are_listed_newest_first(client: TestClient, admin_headers: dict[str, str]) -> None:
    client.post("/api/v1/runs", headers=admin_headers)
    client.post("/api/v1/runs", headers=admin_headers)

    runs = client.get("/api/v1/runs", headers=admin_headers).json()

    assert len(runs) == 2
    assert runs[0]["started_at"] >= runs[1]["started_at"]


def test_token_registered_in_database_starts_a_run(
    client: TestClient, db_session_factory: SessionFactory
) -> None:
    import hashlib

    from app.models_runs import WorkerTriggerKey

    token = "db-registreret-noegle"
    with db_session_factory() as db:
        db.add(WorkerTriggerKey(token_sha256=hashlib.sha256(token.encode()).hexdigest()))
        db.commit()

    response = client.post(
        "/api/v1/runs", json={"force_all": False}, headers={"X-Worker-Token": token}
    )

    assert response.status_code == 202, response.text
    assert response.json()["trigger"] == "schedule"
    assert client.post("/api/v1/runs", headers={"X-Worker-Token": "forkert"}).status_code == 401


def test_run_counts_are_stored_while_it_runs(
    client: TestClient, admin_headers: dict[str, str], run_provider: Any
) -> None:
    import app.worker as worker

    _upload_document(client, admin_headers)
    seen: list[int] = []
    original = worker._store_counts

    def spy(run: Any, result: Any) -> None:
        original(run, result)
        seen.append(result.documents_processed)

    worker._store_counts = spy
    try:
        client.post("/api/v1/runs", headers=admin_headers)
    finally:
        worker._store_counts = original

    # Mindst én løbende opdatering før den afsluttende.
    assert len(seen) >= 2
    assert seen[-1] == 1
