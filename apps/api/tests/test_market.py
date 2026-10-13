"""Den forenklede radar: markedsudtræk, Teknologier, Sådan gør andre og Til OK.

Hvert fund kræver et ordret citat; tal i effekten skal stå i kilden;
leverandøren er aldrig sin egen case; interne kilder er aldrig markedsviden;
et skjult fund forsvinder overalt; Til OK citerer kun fund, der findes.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.models import Document
from app.routes.documents import ai_provider_dep
from app.routes.runs import run_ai_provider
from tests.conftest import FakeProvider, SessionFactory

TEXT = (
    "Puzzel lancerer en dansk chatbot til kundeservice, som forstår dansk. "
    "Norlys har sat en voicebot i drift i kundeservice med Puzzel. "
    "Ifølge Norlys blev ventetiden 30 procent kortere. "
    "Zendesk bruger selv sin AI-agent. "
    "Leverandøren lover også en revolution."
)

MARKET = {
    "technologies": [
        {
            "technology": "chatbot",  # alias for Virtual Agent i kataloget
            "vendor": "Puzzel",
            "product": "Puzzel Chatbot",
            "what_it_does_da": "Besvarer kundens spørgsmål i chatten.",
            "business_value_da": None,
            "danish_supported": True,
            "area": ["kundeservice"],
            "quote": "Puzzel lancerer en dansk chatbot til kundeservice, som forstår dansk.",
        },
        {
            "technology": "Emotion Detection",  # ny teknologi → kandidat
            "vendor": "Puzzel",
            "area": ["salg"],
            "quote": "Leverandøren lover også en revolution.",
        },
        {
            "technology": "Agent Assist",
            "vendor": "Puzzel",
            "area": ["kundeservice"],
            "quote": "Dette citat står ikke i artiklen.",
        },
    ],
    "cases": [
        {
            "company": "Norlys",
            "country": "DK",
            "industry": "energi",
            "what_they_did_da": "Norlys bruger en voicebot i kundeservice.",
            "technology": "Voice AI",
            "vendor": "Puzzel",
            "adoption_stage": "drift",
            "scope": None,
            "effect": "30 % kortere ventetid",
            "kpi": "ventetid",
            "effect_source": "virksomheden",
            "lesson": None,
            "area": ["kundeservice"],
            "quote": (
                "Norlys har sat en voicebot i drift i kundeservice med Puzzel. "
                "Ifølge Norlys blev ventetiden 30 procent kortere."
            ),
        },
        {
            "company": "Zendesk",
            "technology": "Agentic AI",
            "vendor": "Zendesk",
            "area": ["kundeservice"],
            "quote": "Zendesk bruger selv sin AI-agent.",
        },
    ],
}


@pytest.fixture()
def market_mode(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("MARKET_PIPELINE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _provider(**kwargs: Any) -> FakeProvider:
    fake = FakeProvider(market=kwargs.pop("market", MARKET), **kwargs)
    app.dependency_overrides[ai_provider_dep] = lambda: fake
    app.dependency_overrides[run_ai_provider] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.pop(ai_provider_dep, None)
    app.dependency_overrides.pop(run_ai_provider, None)


def _upload(
    client: TestClient,
    headers: dict[str, str],
    text: str = TEXT,
    access_class: str = "public",
) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Energimedie",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": access_class,
        },
        headers=headers,
    ).json()
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("nyhed.txt", text.encode(), "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    document_id: str = upload.json()["document"]["id"]
    return document_id


def _run(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post("/api/v1/runs", json={"force_all": True}, headers=headers)
    assert response.status_code == 202, response.text
    run: dict[str, Any] = client.get(
        f"/api/v1/runs/{response.json()['id']}", headers=headers
    ).json()
    return run


def test_run_extracts_technologies_and_cases_with_verbatim_quotes(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    fake = _provider()
    _upload(client, admin_headers)
    run = _run(client, admin_headers)
    assert run["status"] == "succeeded", run
    assert "market_extraction" in fake.calls
    assert "claim_extraction" not in fake.calls  # den gamle pipeline kører ikke

    techs = client.get("/api/v1/market/technologies", headers=reader_headers).json()
    by_label = {t["label"]: t for t in techs["items"]}
    chatbot = by_label["Chatbot og virtuel agent"]
    assert [v["name"] for v in chatbot["vendors"]] == ["Puzzel"]
    assert chatbot["vendors"][0]["danish_supported"] is True
    assert chatbot["vendors"][0]["source"]["name"] == "Energimedie"
    # Ny teknologi uden for kataloget = Nyt i markedet.
    assert by_label["Emotion Detection"]["is_new"] is True
    # Citatet, der ikke står i artiklen, blev kasseret.
    assert by_label["Hjælp til medarbejderen under samtalen"]["vendors"] == []
    # Voicebot kender Puzzel fra Norlys-casen.
    voice = by_label["Voicebot og tale-AI"]
    assert voice["case_count"] == 1
    assert voice["vendors"][0]["via_case"] is True

    cases = client.get("/api/v1/market/cases", headers=reader_headers).json()
    assert [c["company"] for c in cases["items"]] == ["Norlys"]  # Zendesk er ikke sin egen case
    norlys = cases["items"][0]
    assert norlys["region"] == "danmark"
    assert norlys["stage_label"] == "I drift"
    assert norlys["effect"] == "30 % kortere ventetid"
    assert norlys["kpi_label"] == "Ventetid"
    assert norlys["effect_source_label"] == "Virksomhedens egne tal"
    assert norlys["vendor"] == "Puzzel"


def test_effect_with_numbers_not_in_the_source_is_dropped(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    case = dict(MARKET["cases"][0], effect="45 % kortere ventetid")
    _provider(market={"technologies": [], "cases": [case]})
    _upload(client, admin_headers)
    _run(client, admin_headers)
    cards = client.get("/api/v1/market/cases", headers=admin_headers).json()["items"]
    assert cards[0]["effect"] is None
    assert cards[0]["kpi"] is None


def test_filters_by_area_and_region(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    _provider()
    _upload(client, admin_headers)
    _run(client, admin_headers)
    get = lambda q: client.get(f"/api/v1/market/cases{q}", headers=admin_headers).json()  # noqa: E731
    assert get("?area=kundeservice")["total"] == 1
    assert get("?area=salg")["total"] == 0
    assert get("?region=norden")["total"] == 0
    techs = client.get("/api/v1/market/technologies?area=salg", headers=admin_headers).json()
    assert all("salg" in t["areas"] for t in techs["items"])
    assert {a["area"] for a in techs["areas"]} == {"salg", "kundeservice", "support"}


def test_internal_sources_are_never_market_knowledge(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    fake = _provider()
    _upload(client, admin_headers, access_class="restricted")
    _run(client, admin_headers)
    assert "market_extraction" not in fake.calls
    assert client.get("/api/v1/market/cases", headers=admin_headers).json()["total"] == 0


def test_hidden_item_disappears_and_hiding_requires_admin(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    _provider()
    _upload(client, admin_headers)
    _run(client, admin_headers)
    case = client.get("/api/v1/market/cases", headers=admin_headers).json()["items"][0]
    item_id = case["item_ids"][0]
    denied = client.patch(
        f"/api/v1/market/items/{item_id}", json={"hidden": True}, headers=reader_headers
    )
    assert denied.status_code == 403
    hidden = client.patch(
        f"/api/v1/market/items/{item_id}", json={"hidden": True}, headers=admin_headers
    )
    assert hidden.status_code == 200 and hidden.json()["hidden"] is True
    assert client.get("/api/v1/market/cases", headers=admin_headers).json()["total"] == 0
    audit = client.get("/api/v1/audit?entity_type=market_item", headers=admin_headers).json()
    assert audit["items"][0]["changes"]["hidden"] == {"fra": False, "til": True}


def test_ok_brief_keeps_only_valid_references(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    brief = {
        "top_now": [
            {"text": "Norlys har fået 30 % kortere ventetid med en voicebot.", "refs": ["C1"]},
            {"text": "Et punkt uden kilde.", "refs": ["C99"]},
        ],
        "problems": [
            {
                "problem": "P1",
                "technologies": ["T1", "T99"],
                "cases": [{"ref": "C1", "why": "Dansk energiselskab som OK."}],
                "next_step": "Book en demo med Puzzel.",
            },
            {"problem": "P42", "technologies": [], "cases": [], "next_step": "Ukendt."},
        ],
    }
    fake = _provider(ok_brief=brief)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    assert "ok_brief" in fake.calls  # nye fund → forsiden opdateres

    out = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert [p["text"] for p in out["top_now"]] == [brief["top_now"][0]["text"]]
    assert out["top_now"][0]["cases"][0]["company"] == "Norlys"
    first = out["problems"][0]
    assert first["key"] == "ventetid"
    assert first["next_step"] == "Book en demo med Puzzel."
    assert [c["case"]["company"] for c in first["cases"]] == ["Norlys"]
    assert first["effects"][0]["effect"] == "30 % kortere ventetid"
    assert {c["name"] for c in first["contacts"]} >= {"Norlys"}
    # Alle problemer vises, også dem uden fund.
    assert len(out["problems"]) == 11

    sales = client.get("/api/v1/ok-brief?area=salg", headers=reader_headers).json()
    assert {p["area"] for p in sales["problems"]} == {"salg"}

    # Skjules casen, forsvinder den også fra Til OK.
    item_id = out["problems"][0]["cases"][0]["case"]["item_ids"][0]
    client.patch(f"/api/v1/market/items/{item_id}", json={"hidden": True}, headers=admin_headers)
    after = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert after["top_now"] == []
    assert after["problems"][0]["cases"] == []


def test_older_documents_are_analysed_by_later_runs(
    client: TestClient,
    admin_headers: dict[str, str],
    db_session_factory: SessionFactory,
    market_mode: Any,
) -> None:
    _provider()
    document_id = _upload(client, admin_headers)
    _run(client, admin_headers)
    # Som et dokument behandlet af den gamle pipeline.
    with db_session_factory() as db:
        document = db.get(Document, uuid.UUID(document_id))
        assert document is not None
        document.market_extracted_at = None
        db.commit()
    run = _run(client, admin_headers)
    assert run["documents_reread"] == 1
    assert client.get("/api/v1/market/cases", headers=admin_headers).json()["total"] == 1


def test_generate_ok_brief_requires_admin(
    client: TestClient, admin_headers: dict[str, str], reader_headers: dict[str, str]
) -> None:
    _provider()
    assert client.post("/api/v1/ok-brief/generate", headers=reader_headers).status_code == 403
    response = client.post("/api/v1/ok-brief/generate", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["case_count"] == 0
