"""Beslutningsoplæg (OK's egne tal + regneeksempel) og interne analyser,
der holdes ude af markedsviden."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from tests.conftest import DOC_TEXT


@pytest.fixture()
def auto_publish(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("AUTO_PUBLISH", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_empty_brief_names_what_is_missing(
    client: TestClient, reader_headers: dict[str, str]
) -> None:
    data = client.get("/api/v1/decision-brief", headers=reader_headers).json()
    assert data["brief"]["title"].startswith("90 dage")
    assert data["calculation"]["saving_low"] is None
    assert "årsværk" in data["calculation"]["missing"]


def test_admin_saves_numbers_and_calculation_uses_only_them(
    client: TestClient,
    admin_headers: dict[str, str],
    reviewer_headers: dict[str, str],
) -> None:
    body = {
        "fte": 40,
        "cost_per_fte": 450000,
        "contacts_per_year": {"phone": 200000, "mail": 100000, "chat": 50000},
        "aht_minutes": 6,
        "scenario_low_pct": 5,
        "scenario_high_pct": 10,
        "internal_findings": [{"title": "No-reply-støj", "figure": "359 tickets i august"}],
        "ask": "30-dages sprint",
    }
    assert (
        client.put("/api/v1/decision-brief", json=body, headers=reviewer_headers).status_code == 403
    )

    response = client.put("/api/v1/decision-brief", json=body, headers=admin_headers)
    assert response.status_code == 200, response.text
    calc = response.json()["calculation"]
    assert calc["annual_cost"] == 18_000_000
    assert calc["total_contacts"] == 350_000
    assert calc["cost_per_contact"] == pytest.approx(51.43, rel=1e-3)
    assert calc["handling_hours"] == 35_000
    assert calc["saving_low"] == 900_000
    assert calc["saving_high"] == 1_800_000
    assert calc["missing"] == []

    saved = client.get("/api/v1/decision-brief", headers=admin_headers).json()
    assert saved["brief"]["internal_findings"][0]["figure"] == "359 tickets i august"
    assert saved["updated_at"] is not None


def test_signal_from_internal_source_is_not_market_intelligence(
    client: TestClient, admin_headers: dict[str, str], fake_provider: Any, auto_publish: None
) -> None:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "FocalScope-eksport",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": "restricted",
        },
        headers=admin_headers,
    ).json()
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("eksport.txt", DOC_TEXT.encode(), "text/plain")},
        headers=admin_headers,
    )
    assert upload.status_code == 200, upload.text
    document_id = upload.json()["document"]["id"]
    processed = client.post(
        f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
    )
    assert processed.status_code == 200, processed.text

    all_signals = client.get("/api/v1/signals", headers=admin_headers).json()["items"]
    assert len(all_signals) == 1 and all_signals[0]["internal"] is True
    market = client.get("/api/v1/signals?internal=false", headers=admin_headers).json()
    assert market["items"] == []
    internal = client.get("/api/v1/signals?internal=true", headers=admin_headers).json()
    assert len(internal["items"]) == 1
    dashboard = client.get("/api/v1/dashboard", headers=admin_headers).json()
    assert dashboard["published_signals"] == 0
    assert dashboard["latest_signals"] == []
