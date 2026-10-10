"""Direktørvisningen: OK-problem → capabilities → leverandører, dokumenteret
brug og effekt. Kun godkendte claims tæller."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import FakeProvider, _upload_document
from tests.test_vendor_landscape import EXTRACTION, TEXT, _process_text


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _with_provider(provider: FakeProvider) -> None:
    app.dependency_overrides[ai_provider_dep] = lambda: provider


def test_problem_shows_vendors_references_and_effects(
    client: TestClient, admin_headers: dict[str, str], auto_publish: None
) -> None:
    try:
        # Danske Bank bruger Agent Assist og rapporterer en effekt (standardfixturen).
        _with_provider(FakeProvider())
        document_id = _upload_document(client, admin_headers)
        assert (
            client.post(
                f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
            ).status_code
            == 200
        )
        # Puzzel tilbyder Agent Assist; Telmore bruger Puzzel.
        _with_provider(FakeProvider(extraction=EXTRACTION))
        _process_text(client, admin_headers, TEXT)
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)

    data = client.get("/api/v1/opportunity-map", headers=admin_headers).json()
    [problem] = [p for p in data["problems"] if p["name"] == "Store mailmængder"]
    assert [c["name"] for c in problem["capabilities"]] == ["Agent Assist"]
    assert [v["name"] for v in problem["vendors"]] == ["Puzzel"]
    assert problem["vendors"][0]["products"] == ["Puzzel Agent Assist med dansk sprogstøtte"]
    refs = {(r["name"], r["how"]) for r in problem["references"]}
    assert refs == {("Danske Bank", "Bruger Agent Assist")}
    # Leverandørens kunder står under leverandøren, ikke som brug af capability.
    assert problem["vendors"][0]["customers"] == ["Telmore"]
    assert [e["effect"] for e in problem["effects"]] == ["20 procent lavere efterbehandlingstid"]
    assert problem["effects"][0]["organization"] == "Danske Bank"
    assert problem["evidence_count"] > 0


def test_empty_radar_still_lists_problems(
    client: TestClient, reader_headers: dict[str, str]
) -> None:
    data = client.get("/api/v1/opportunity-map", headers=reader_headers).json()
    [problem] = data["problems"]
    assert problem["name"] == "Store mailmængder"
    assert problem["vendors"] == [] and problem["references"] == [] and problem["effects"] == []
