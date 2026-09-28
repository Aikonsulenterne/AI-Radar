"""Samme dokument må aldrig AI-behandles to gange samtidig.

Et dobbeltklik gav to kørsler: dobbelte claims og dobbelt AI-forbrug. En
kørsel markerer derfor dokumentet extraction_pending (committet) før AI
kaldes, og et samtidigt kald afvises med 409.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.enums import ProcessingStatus
from app.models import Document
from tests.conftest import SessionFactory, _upload_document


def _set_status(
    factory: SessionFactory, document_id: str, status: ProcessingStatus, age: timedelta
) -> None:
    with factory() as session:
        document = session.get(Document, uuid.UUID(document_id))
        assert document is not None
        document.processing_status = status
        session.flush()
        # updated_at sættes eksplicit, så onupdate ikke overskriver alderen.
        document.updated_at = datetime.now(UTC) - age
        session.commit()


def _process(client: TestClient, headers: dict[str, str], document_id: str) -> Any:
    return client.post(f"/api/v1/review/documents/{document_id}/process", headers=headers)


def test_document_under_processing_is_not_processed_again(
    client: TestClient,
    admin_headers: dict[str, str],
    fake_provider: Any,
    db_session_factory: SessionFactory,
) -> None:
    document_id = _upload_document(client, admin_headers)
    _set_status(db_session_factory, document_id, ProcessingStatus.extraction_pending, timedelta())

    response = _process(client, admin_headers, document_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_processing"
    assert fake_provider.calls == []


def test_stale_processing_can_be_restarted(
    client: TestClient,
    admin_headers: dict[str, str],
    fake_provider: Any,
    db_session_factory: SessionFactory,
) -> None:
    document_id = _upload_document(client, admin_headers)
    _set_status(
        db_session_factory, document_id, ProcessingStatus.extraction_pending, timedelta(hours=1)
    )

    response = _process(client, admin_headers, document_id)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "review_pending"


def test_second_run_after_success_is_rejected(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any
) -> None:
    document_id = _upload_document(client, admin_headers)
    first = _process(client, admin_headers, document_id)
    assert first.status_code == 200
    calls_after_first = len(fake_provider.calls)

    again = _process(client, admin_headers, document_id)

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "invalid_status"
    assert len(fake_provider.calls) == calls_after_first
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert len(document["claims"]) == first.json()["claims_created"]


def test_crash_mid_run_restores_status(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any
) -> None:
    document_id = _upload_document(client, admin_headers)

    def boom(**_: Any) -> str:
        raise RuntimeError("forbindelsen døde")

    fake_provider.complete_text = boom
    crash_client = TestClient(client.app, raise_server_exceptions=False)
    response = _process(crash_client, admin_headers, document_id)

    assert response.status_code == 500
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["processing_status"] == "normalized"
