"""Til OK 3.0: overskrift, konkurrentoverblik, siden sidst, gevinstspænd,
direktørens ja/nej med opfølgning og OK's offentlige status.

Alt på første skærmbillede beregnes af serveren ud fra fund med kilde."""

from typing import Any

from fastapi.testclient import TestClient

from tests.test_market import MARKET, _provider, _run, _upload, market_mode  # noqa: F401

TEXT2 = (
    "Telenor afprøver Agent Assist fra Genesys i kundeservice. "
    "Ifølge Telenor blev efterbehandlingen 40 procent kortere i piloten."
)

MARKET2 = {
    "technologies": [],
    "cases": [
        {
            "company": "Telenor",
            "country": "DK",
            "industry": "telekom",
            "what_they_did_da": "Telenor afprøver Agent Assist i kundeservice.",
            "technology": "Agent Assist",
            "vendor": "Genesys",
            "adoption_stage": "pilot",
            "effect": "40 procent kortere efterbehandling",
            "kpi": "produktivitet",
            "effect_source": "virksomheden",
            "area": ["kundeservice"],
            "quote": "Ifølge Telenor blev efterbehandlingen 40 procent kortere i piloten.",
        }
    ],
}

BRIEF = {
    "decisions": [
        {
            "question": "Må vi starte et forsøg på to uger med en voicebot?",
            "technology": "T1",
            "owner": "Kundeservice",
            "duration": "2 uger",
            "first_step": "Find de fem hyppigste opkaldsemner.",
        }
    ],
    "per_problem": [{"problem": "P1", "best_case": "C1", "next_step": "Book en demo."}],
}


def _brief(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = client.get("/api/v1/ok-brief", headers=headers).json()
    return out


def _voicebot_id(client: TestClient, headers: dict[str, str]) -> str:
    items = client.get("/api/v1/market/technologies", headers=headers).json()["items"]
    return str(next(t["id"] for t in items if t["label"] == "Stemmeagenter og voicebots"))


def test_first_screen_is_computed_from_the_cases(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,  # noqa: F811
) -> None:
    _provider(ok_brief=BRIEF)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    out = _brief(client, reader_headers)

    assert out["headline"]["text"] == (
        "Stemmeagenter og voicebots: 1 af 15 selskaber, der ligner OK, har det i drift."
    )
    matrix = out["matrix"]
    assert [c["label"] for c in matrix["columns"]] == ["Stemmeagenter og voicebots"]
    [row] = matrix["rows"]
    assert row["name"] == "Norlys" and row["group"] == "Energi" and not row["is_ok"]
    assert row["cells"][0]["state"] == "drift" and row["cells"][0]["label"] == "Drift"
    assert row["cells"][0]["href"].startswith("/cases#case-")
    assert "Circle K" in matrix["peers_without"] and "Norlys" not in matrix["peers_without"]
    assert out["since_last"]["lines"] == []
    assert out["since_last"]["note"].startswith("Første udgave")

    # Gevinst fra casen, ikke fra AI'en.
    decision = out["decisions"][0]
    assert decision["technology"]["label"] == "Stemmeagenter og voicebots"
    assert decision["gain"]["text"] == "30 %"
    assert decision["gain"]["kpi"] == "ventetid"
    assert decision["gain"]["cases"] == 1 and decision["gain"]["vendor_only"] is False
    assert decision["first_step"] == "Find de fem hyppigste opkaldsemner."


def test_since_last_shows_what_is_new_and_is_frozen_at_approval(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,  # noqa: F811
) -> None:
    _provider(ok_brief=BRIEF)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)

    _provider(market=MARKET2, ok_brief=BRIEF)
    _upload(client, admin_headers, text=TEXT2)
    _run(client, admin_headers)

    draft = _brief(client, admin_headers)
    assert draft["state"] == "kladde"
    texts = [line["text"] for line in draft["since_last"]["lines"]]
    assert texts[0] == "Nyt hos Telenor: Agent Assist (pilot)."
    assert draft["since_last"]["lines"][0]["href"].startswith("/cases#case-")
    # Direktøren ser stadig den godkendte version uden det nye.
    assert _brief(client, reader_headers)["since_last"]["lines"] == []

    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    reader = _brief(client, reader_headers)
    assert [line["text"] for line in reader["since_last"]["lines"]][0] == texts[0]
    assert {r["name"] for r in reader["matrix"]["rows"]} == {"Norlys", "Telenor"}
    telenor = next(r for r in reader["matrix"]["rows"] if r["name"] == "Telenor")
    assert [c["state"] for c in telenor["cells"]].count("pilot") == 1

    # Intet nyt ved næste godkendelse.
    client.post("/api/v1/ok-brief/generate", headers=admin_headers)
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    again = _brief(client, reader_headers)
    assert again["since_last"]["lines"] == []
    assert again["since_last"]["note"].startswith("Intet nyt siden")


def test_director_answers_and_a_yes_is_followed_up(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,  # noqa: F811
) -> None:
    fake = _provider(ok_brief=BRIEF)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    [decision] = _brief(client, reader_headers)["decisions"]
    assert decision["answer"] is None and decision["answerable"] is True

    wrong = client.post(
        "/api/v1/ok-brief/decisions",
        json={"key": "findes-ikke", "answer": "ja"},
        headers=reader_headers,
    )
    assert wrong.status_code == 404
    answer = client.post(
        "/api/v1/ok-brief/decisions",
        json={"key": decision["key"], "answer": "ja"},
        headers=reader_headers,
    )
    assert answer.status_code == 200, answer.text
    [shown] = _brief(client, reader_headers)["decisions"]
    assert shown["answer"] == "ja" and shown["answered_at"]

    # Næste version stiller ikke spørgsmålet igen, men følger op på ja'et.
    client.post("/api/v1/ok-brief/generate", headers=admin_headers)
    prompt = fake.prompts[len(fake.prompts) - 1]
    assert "DECISIONS ALREADY ANSWERED" in prompt
    assert "Må vi starte et forsøg på to uger med en voicebot?" in prompt
    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    out = _brief(client, reader_headers)
    assert out["decisions"] == []
    [follow_up] = out["follow_ups"]
    assert follow_up["question"] == "Må vi starte et forsøg på to uger med en voicebot?"
    assert follow_up["label"].startswith("Du sagde ja ")


def test_oks_public_status_adds_an_ok_row_with_a_public_source(
    client: TestClient,
    admin_headers: dict[str, str],
    reader_headers: dict[str, str],
    market_mode: Any,  # noqa: F811
) -> None:
    _provider(ok_brief=BRIEF)
    _upload(client, admin_headers)
    _run(client, admin_headers)
    voicebot = _voicebot_id(client, admin_headers)
    url = f"/api/v1/ok-public-status/{voicebot}"

    assert client.put(url, json={"stage": "pilot"}, headers=reader_headers).status_code == 403
    assert client.put(url, json={"stage": "pilot"}, headers=admin_headers).status_code == 422
    insecure = {"stage": "pilot", "source_url": "http://ok.dk/kundeservice"}
    assert client.put(url, json=insecure, headers=admin_headers).status_code == 422
    ok = client.put(
        url,
        json={"stage": "pilot", "source_url": "https://www.ok.dk/kundeservice"},
        headers=admin_headers,
    )
    assert ok.status_code == 200, ok.text
    listed = client.get("/api/v1/ok-public-status", headers=admin_headers).json()
    assert next(r for r in listed if r["technology_id"] == voicebot)["stage"] == "pilot"

    client.post("/api/v1/ok-brief/approve", headers=admin_headers)
    rows = _brief(client, reader_headers)["matrix"]["rows"]
    assert rows[0]["name"] == "OK" and rows[0]["is_ok"] is True
    assert rows[0]["cells"][0] == {
        "state": "pilot",
        "label": "Pilot",
        "href": "https://www.ok.dk/kundeservice",
        "source_url": "https://www.ok.dk/kundeservice",
    }

    # Uden status forsvinder OK's række igen.
    client.put(url, json={"stage": None}, headers=admin_headers)
    assert _brief(client, reader_headers)["matrix"]["rows"][0]["name"] == "Norlys"


def test_gain_range_spans_the_cases() -> None:
    import uuid
    from datetime import UTC, datetime

    from app.market.overview import gain_for
    from app.market.views import CaseCard, SourceRef, TechnologyRef

    tech = TechnologyRef(id=uuid.uuid4(), label="Samtaleopsummering")

    def card(effect: str, kind: str = "uafhængig") -> CaseCard:
        return CaseCard(
            id=uuid.uuid4(),
            item_ids=[],
            company="X",
            company_id=None,
            country="DK",
            region="danmark",
            region_label="Danmark",
            industry=None,
            areas=["kundeservice"],
            what_they_did=None,
            technology=tech,
            technology_name=None,
            vendor=None,
            stage="drift",
            stage_label="I drift",
            scope=None,
            effect=effect,
            kpi="produktivitet",
            kpi_label="Produktivitet",
            effect_source=None,
            effect_source_label=None,
            lesson=None,
            quote="q",
            source=SourceRef(name="Kilde", url="https://example.org"),
            observed_at=datetime.now(UTC),
            source_kind=kind,
        )

    gain = gain_for(tech.id, [card("25 % kortere"), card("halveret", "leverandør")])
    assert gain is not None
    assert gain.text == "25–50 %" and gain.kpi == "produktivitet"
    assert gain.cases == 2 and gain.independent == 1 and not gain.vendor_only
    only_vendor = gain_for(tech.id, [card("hvert fjerde opkald", "leverandør")])
    assert only_vendor is not None and only_vendor.vendor_only
    words = gain_for(tech.id, [card("Medarbejderne er gladere")])
    assert words is not None and words.text == "»Medarbejderne er gladere«"
    assert gain_for(uuid.uuid4(), [card("25 %")]) is None
