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
    chatbot = by_label["Chatbot / virtuel agent"]
    assert [v["name"] for v in chatbot["vendors"]] == ["Puzzel"]
    assert chatbot["vendors"][0]["danish_supported"] is True
    assert chatbot["vendors"][0]["source"]["name"] == "Energimedie"
    assert chatbot["status"] == "hold_oeje"  # ingen cases endnu
    assert chatbot["for_ok"]
    # Ny teknologi uden for kataloget = Nyt i markedet.
    assert by_label["Emotion Detection"]["is_new"] is True
    assert [n["technology"]["label"] for n in techs["new_on_market"]] == ["Emotion Detection"]
    # Citatet, der ikke står i artiklen, blev kasseret.
    assert by_label["Agent Assist"]["vendors"] == []
    # Voicebot kender Puzzel fra Norlys-casen; én case i drift = værd at afprøve.
    voice = by_label["Stemmeagenter og voicebots"]
    assert voice["case_count"] == 1
    assert voice["status"] == "vaerd_at_afproeve"
    assert voice["best_case"]["company"] == "Norlys"
    assert voice["vendors"][0]["via_case"] is True
    puzzel = next(v for v in techs["vendors"] if v["name"] == "Puzzel")
    assert puzzel["type"] == "Kundecenterplatform"
    assert puzzel["danish"] is True

    cases = client.get("/api/v1/market/cases", headers=reader_headers).json()
    assert [c["company"] for c in cases["items"]] == ["Norlys"]  # Zendesk er ikke sin egen case
    norlys = cases["items"][0]
    assert norlys["region"] == "danmark"
    assert norlys["stage_label"] == "I drift"
    assert norlys["effect"] == "30 % kortere ventetid"
    assert norlys["source_kind_label"] == "Uafhængig kilde"
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
    assert get("?region=norden")["total"] == 1  # Norden omfatter Danmark
    assert get("?region=verden")["total"] == 0
    techs = client.get("/api/v1/market/technologies?area=salg", headers=admin_headers).json()
    assert all("salg" in t["areas"] for t in techs["items"])
    assert {a["area"] for a in techs["areas"]} == {"salg", "kundeservice", "support"}


def test_internal_sources_are_never_market_knowledge(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    fake = _provider()
    _upload(client, admin_headers)
    # Kilden markeres intern efter upload (dokumenter fra før spærringen).
    [source] = client.get("/api/v1/sources", headers=admin_headers).json()["items"]
    client.patch(
        f"/api/v1/sources/{source['id']}",
        json={"access_class": "restricted"},
        headers=admin_headers,
    )
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


def test_ok_brief_keeps_only_valid_references_and_each_case_once(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    brief = {
        "recommendations": [
            {
                "action": "Book en demo med Puzzel.",
                "owner": "Kundeservice",
                "duration": "2 uger",
                "first_step": "Skriv til Puzzel i dag.",
                "technology": "T99",
                "case": "C1",
            }
        ]
        * 5,
        "decisions": [
            {"question": "Må vi starte et forsøg?", "owner": "Kundeservice", "duration": "2 uger"},
            {"question": "Må vi starte et forsøg?"},
            {"question": "Skal vi tale med Norlys?", "technology": "T99"},
        ],
        "per_problem": [
            {
                "problem": "P1",
                "best_technology": "T99",
                "best_case": "C1",
                "why_comparable": "Dansk energiselskab som OK.",
                "more_cases": ["C1"],
                "next_step": "Book en demo med Puzzel.",
            },
            # Samme case igen: må ikke vises to gange.
            {"problem": "P2", "best_case": "C1", "next_step": "Noget andet."},
            {"problem": "P42", "best_case": "C1", "next_step": "Ukendt problem."},
        ],
    }
    fake = _provider(ok_brief=brief)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    assert "ok_brief" in fake.calls  # nye fund → forsiden opdateres
    approve = client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    assert approve.status_code == 200, approve.text

    out = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert out["state"] == "godkendt"
    assert len(out["recommendations"]) == 3
    rec = out["recommendations"][0]
    assert rec["first_step"] == "Skriv til Puzzel i dag."
    assert rec["reference"]["company"] == "Norlys"
    assert rec["reference"]["href"].startswith("/cases#case-")
    assert rec["vendor"] == "Puzzel"
    assert rec["technology"] is None  # ugyldig henvisning
    # Samme spørgsmål to gange vises én gang.
    assert [d["question"] for d in out["decisions"]] == [
        "Må vi starte et forsøg?",
        "Skal vi tale med Norlys?",
    ]
    assert out["decisions"][0]["owner"] == "Kundeservice"
    # Svar gemmes ikke, før OK har godkendt det (STORE_DECISIONS).
    assert out["decisions_stored"] is False
    assert out["decisions"][0]["answerable"] is False
    assert [a["area"] for a in out["areas"]] == ["kundeservice"]
    row = out["areas"][0]["rows"][0]
    assert row["key"] == "ventetid"
    assert row["proof"]["company"] == "Norlys"
    assert row["proof"]["kind_label"] == "Uafhængig kilde"
    assert row["more"] == []  # samme case som beviset
    # Ugyldig teknologi-id: casens egen teknologi og dens status bruges.
    assert row["technology"]["label"] == "Stemmeagenter og voicebots"
    assert row["technology"]["status_label"] == "Værd at afprøve"
    assert row["vendors"] == ["Puzzel"]  # kendt fra casen
    assert row["reference"] == "Norlys"
    # Kun én række viser Norlys; de øvrige problemer er endnu ikke dokumenteret.
    assert sum(len(a["rows"]) for a in out["areas"]) == 1
    assert len(out["undocumented"]) == 10

    # Skjules casen, forsvinder den også fra Til OK.
    cases = client.get("/api/v1/market/cases", headers=admin_headers).json()["items"]
    client.patch(
        f"/api/v1/market/items/{cases[0]['item_ids'][0]}",
        json={"hidden": True},
        headers=admin_headers,
    )
    after = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert after["matrix"]["rows"] == []
    assert after["recommendations"][0]["reference"] is None
    assert after["areas"] == []
    assert len(after["undocumented"]) == 11


def test_sources_table_counts_relevant_articles_and_is_admin_only(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    _provider()
    _upload(client, admin_headers)
    client.post(
        "/api/v1/sources",
        json={
            "name": "Interne data (OK)",
            "source_type": "primary",
            "retrieval_method": "manual_upload",
            "access_class": "restricted",
        },
        headers=admin_headers,
    )
    _run(client, admin_headers)
    assert client.get("/api/v1/market/sources", headers=reader_headers).status_code == 403
    sources = client.get("/api/v1/market/sources", headers=admin_headers).json()
    assert len(sources) == 1  # den interne kilde vises ikke
    assert sources[0]["type"] == "Fagmedie"
    assert sources[0]["relevant_articles"] == 1
    me = client.get("/api/v1/me", headers=admin_headers).json()
    assert me["last_updated"] is not None


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
    assert response.json()["undocumented"]


def test_me_reports_role(
    client: TestClient, admin_headers: dict[str, str], reader_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/me", headers=admin_headers).json()["role"] == "admin"
    assert client.get("/api/v1/me", headers=reader_headers).json()["role"] == "reader"
    assert client.get("/api/v1/me").status_code == 401


def test_director_sees_only_the_approved_til_ok_and_mail_is_sent(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = {
        "decisions": [
            {"question": "Må vi starte et forsøg?", "owner": "Kundeservice", "duration": "2 uger"}
        ],
        "per_problem": [{"problem": "P1", "best_case": "C1", "next_step": "Book en demo."}],
    }
    fake = _provider(ok_brief=brief)
    _upload(client, admin_headers)
    _run(client, admin_headers)

    # Før godkendelse: direktøren ser intet, konsulenten ser kladden.
    assert client.get("/api/v1/ok-brief", headers=reader_headers).json()["state"] == "ingen"
    draft = client.get("/api/v1/ok-brief", headers=admin_headers).json()
    assert draft["state"] == "kladde"
    assert draft["decisions"][0]["answerable"] is False  # endnu ikke godkendt
    assert client.post("/api/v1/ok-brief/approve", headers=reader_headers).status_code == 403

    sent: list[Any] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            return None

        def send_message(self, message: Any) -> None:
            sent.append(message)

    monkeypatch.setattr("app.mailer.smtplib.SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("BRIEF_RECIPIENTS", "direktoer@example.org, nicl@example.org")
    monkeypatch.setenv("PUBLIC_WEB_URL", "https://radar.example.org")
    get_settings.cache_clear()

    approved = client.post("/api/v1/ok-brief/approve", headers=admin_headers).json()
    assert approved["mail"] == "sendt til 2"
    body = sent[0].get_body(preferencelist=("plain",)).get_content()
    headline = "Stemmeagenter og voicebots: 1 af 15 selskaber, der ligner OK, har det i drift."
    assert headline in body
    assert "SIDEN SIDST" in body and "Første udgave" in body
    assert "Ja / nej: Må vi starte et forsøg?" in body
    assert "Kræver: Kundeservice · 2 uger" in body
    assert "https://radar.example.org/#beslutninger" in body
    html = sent[0].get_body(preferencelist=("html",)).get_content()
    assert "Svar i radaren" in html

    out = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert out["state"] == "godkendt"
    assert out["headline"]["text"] == headline
    assert out["decisions"][0]["question"] == "Må vi starte et forsøg?"

    # En ny kladde ændrer ikke direktørens side, før den er godkendt.
    fake.ok_brief = {"decisions": [{"question": "Ny kladde?"}]}
    client.post("/api/v1/ok-brief/generate", headers=admin_headers)
    assert client.get("/api/v1/ok-brief", headers=admin_headers).json()["state"] == "kladde"
    reader_view = client.get("/api/v1/ok-brief", headers=reader_headers).json()
    assert reader_view["decisions"][0]["question"] == "Må vi starte et forsøg?"


def test_approve_without_mail_setup_still_publishes(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    _provider(ok_brief={"decisions": [{"question": "Må vi starte et forsøg?"}]})
    _upload(client, admin_headers)
    _run(client, admin_headers)
    approved = client.post("/api/v1/ok-brief/approve", headers=admin_headers).json()
    assert approved["mail"] == "ikke sat op"
    admin_view = client.get("/api/v1/ok-brief", headers=admin_headers).json()
    assert admin_view["state"] == "godkendt"
    assert admin_view["mail_status"] == "ikke sat op"


def test_brief_input_contains_oks_systems(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    fake = _provider()
    _upload(client, admin_headers)
    _run(client, admin_headers)
    brief_prompt = fake.prompts[fake.calls.index("ok_brief")]
    assert brief_prompt.startswith("OK TODAY:")
    assert "FocalScope" in brief_prompt and "G4" in brief_prompt


def test_spreadsheet_has_public_findings_and_formulas_but_no_ok_numbers(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
) -> None:
    from io import BytesIO

    from openpyxl import load_workbook

    from app.market.spreadsheet import effect_percent

    _provider(
        ok_brief={
            "must_know": [{"text": "Norlys har kortere ventetid.", "source": "C1"}],
            "per_problem": [{"problem": "P1", "best_case": "C1", "next_step": "Book en demo."}],
        }
    )
    _upload(client, admin_headers)
    _run(client, admin_headers)
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)

    row = client.get("/api/v1/ok-brief", headers=reader_headers).json()["areas"][0]["rows"][0]
    assert "FocalScope" in row["lookup"]
    assert row["effect_pct"] == 0.3

    response = client.get("/api/v1/ok-brief/regneark.xlsx", headers=reader_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml"
    )
    sheet = load_workbook(BytesIO(response.content))["Regnestykke"]
    assert sheet["B8"].value == "Lange ventetider i telefon og chat"
    assert sheet["D8"].value == "Norlys · Danmark"
    assert sheet["H8"].value == 0.3
    # OK's felter er tomme: radaren kender ikke tallene.
    assert sheet["C5"].value is None and sheet["J8"].value is None and sheet["L8"].value is None
    assert sheet["M8"].value.startswith("=IF(OR(")
    assert "J8*L8/60*$C$5*H8" in sheet["M8"].value

    assert effect_percent("fra 8 til 4 minutter") is None
    assert effect_percent("30-40 % kortere efterbehandling") == 0.3
    assert effect_percent("12,5 procent færre opkald") == 0.125
    assert effect_percent("Tiden på efterbehandling er halveret.") == 0.5
    assert effect_percent("Voicebotten løser hvert fjerde opkald") == 0.25


def test_cases_from_companies_like_ok_are_marked_and_missing_ones_named(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    from app.market.catalog import peer_for

    fake = _provider()
    _upload(client, admin_headers)
    _run(client, admin_headers)
    data = client.get("/api/v1/market/cases", headers=admin_headers).json()
    [norlys] = data["items"]
    assert norlys["peer"] == "Norlys" and norlys["peer_group"] == "Energi"
    assert "Norlys" not in data["peers_without_cases"]
    assert "Circle K" in data["peers_without_cases"]
    brief_prompt = fake.prompts[fake.calls.index("ok_brief")]
    assert "ligner OK: Energi" in brief_prompt

    assert peer_for("Andel Energi A/S").name == "Andel"  # type: ignore[union-attr]
    assert peer_for("3M") is None
    assert peer_for("Shellfish Inc") is None


def test_no_mail_when_there_is_nothing_new(
    client: TestClient, admin_headers: dict[str, str], market_mode: Any
) -> None:
    _provider(ok_brief={"per_problem": [{"problem": "P1", "best_case": "C1"}]})
    _upload(client, admin_headers)
    _run(client, admin_headers)
    approved = client.post("/api/v1/ok-brief/approve", headers=admin_headers).json()
    assert approved["mail"] == "ikke sendt (intet nyt)"


def test_add_case_from_a_public_link(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.ingestion.fetch import FetchResult

    def fake_fetch(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
        return FetchResult(
            data=f"<html><title>Opslag</title><body>{TEXT}</body></html>".encode(),
            content_type="text/html",
            final_url=url,
        )

    monkeypatch.setattr("app.routes.market.fetch_url", fake_fetch)
    _provider()
    body = {"url": "https://www.linkedin.com/posts/norlys-voicebot"}
    assert client.post("/api/v1/market/links", json=body, headers=reader_headers).status_code == 403
    unsafe = {"url": "http://127.0.0.1/admin"}
    assert (
        client.post("/api/v1/market/links", json=unsafe, headers=admin_headers).status_code == 422
    )

    added = client.post("/api/v1/market/links", json=body, headers=admin_headers)
    assert added.status_code == 200, added.text
    out = added.json()
    assert out["cases"] == 1 and out["already_known"] is False
    assert "Opdatér Til OK" in out["message"]
    [case] = client.get("/api/v1/market/cases", headers=admin_headers).json()["items"]
    assert case["company"] == "Norlys" and case["peer"] == "Norlys"

    again = client.post("/api/v1/market/links", json=body, headers=admin_headers).json()
    assert again["already_known"] is True


def test_companies_like_ok_only_count_in_denmark() -> None:
    from app.market.catalog import peer_for

    assert peer_for("Shell", "GB") is None
    assert peer_for("Telenor", "NO") is None
    assert peer_for("Vattenfall", None) is None
    assert peer_for("Telenor Danmark", "DK") is not None
