"""Til OK's første skærmbillede: beregnet af serveren, aldrig af AI.

- Overskriften: dagens vigtigste fakta i én sætning.
- Konkurrentoverblikket: dem, der ligner OK (catalog.PEERS) × teknologier.
- Siden sidst: forskellen mellem nu og den senest godkendte version.
- Gevinstspænd: hvad andre fik ud af en teknologi, ud fra casene.

Alt bygger på synlige fund med kilde. AI'en vælger og formulerer andre
steder på siden, men tæller, vurderer og beregner aldrig her.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.market.catalog import PEERS
from app.market.spreadsheet import effect_percent
from app.market.views import (
    KPI_LABELS,
    LIVE_STAGES,
    STATUS_LABELS,
    STATUS_ORDER,
    CaseCard,
    TechnologyCard,
    TechnologyRef,
)
from app.pipeline.entities import normalize_alias

PEER_TOTAL = len(PEERS)
_MAX_COLUMNS = 6
_MAX_SINCE = 3

_MONTHS_SHORT = "jan. feb. mar. apr. maj jun. jul. aug. sep. okt. nov. dec.".split()


def short_date(value: datetime) -> str:
    return f"{value.day}. {_MONTHS_SHORT[value.month - 1]}"


def case_href(card: CaseCard) -> str:
    return f"/cases#case-{card.id}"


def case_key(card: CaseCard) -> str:
    """Stabil nøgle for en case på tværs af kørsler (samme som grupperingen:
    virksomhed + teknologi), også når et nyere fund bliver casens forside."""
    technology = (
        str(card.technology.id) if card.technology else normalize_alias(card.technology_name or "")
    )
    return f"{card.company_id}:{technology}"


# --- Gevinstspænd ---


class Gain(BaseModel):
    """Hvad andre fik ud af en teknologi, som casene skriver det."""

    text: str
    kpi: str | None = None
    cases: int
    independent: int
    vendor_only: bool
    source_url: str | None = None
    source_title: str | None = None
    case_id: uuid.UUID | None = None


def _percent(value: float) -> str:
    number = round(value * 100, 1)
    return f"{number:g}".replace(".", ",")


def gain_for(technology_id: uuid.UUID | None, cases: list[CaseCard]) -> Gain | None:
    """Spændet af andele (laveste–højeste) for den KPI, flest cases måler på.
    Uden andele: den bedste effekt ordret. Uden effekter: None."""
    if technology_id is None:
        return None
    with_effect = [
        c for c in cases if c.technology and c.technology.id == technology_id and c.effect
    ]
    if not with_effect:
        return None
    by_kpi: dict[str, list[tuple[float, CaseCard]]] = {}
    for card in with_effect:
        pct = effect_percent(card.effect)
        if pct is not None:
            by_kpi.setdefault(card.kpi or "andet", []).append((pct, card))
    if by_kpi:
        kpi, values = max(by_kpi.items(), key=lambda item: (len(item[1]), item[0] != "andet"))
        low, high = min(v for v, _ in values), max(v for v, _ in values)
        text = f"{_percent(low)} %" if low == high else f"{_percent(low)}–{_percent(high)} %"
        group = [card for _, card in values]
        kpi_label = KPI_LABELS.get(kpi, "").lower() if kpi != "andet" else None
    else:
        group = with_effect
        best = next((c for c in group if c.source_kind == "uafhængig"), group[0])
        text, kpi_label = f"»{best.effect}«", None
    independent = sum(1 for c in group if c.source_kind == "uafhængig")
    lead = next((c for c in group if c.source_kind == "uafhængig"), group[0])
    return Gain(
        text=text,
        kpi=kpi_label or None,
        cases=len(group),
        independent=independent,
        vendor_only=independent == 0,
        source_url=lead.source.url,
        source_title=lead.source.title or lead.source.name,
        case_id=lead.id,
    )


# --- Konkurrentoverblik ---

CellState = Literal["drift", "pilot", "omtalt", "ingen"]
_CELL_LABELS: dict[str, str] = {
    "drift": "Drift",
    "pilot": "Pilot",
    "omtalt": "Omtalt",
    "ingen": "Ikke fundet",
}
_CELL_RANK = {"drift": 3, "pilot": 2, "omtalt": 1, "ingen": 0}


def _cell_state(stage: str | None) -> CellState:
    if stage in LIVE_STAGES:
        return "drift"
    if stage == "pilot":
        return "pilot"
    return "omtalt"


class MatrixCell(BaseModel):
    state: CellState
    label: str
    href: str | None = None
    source_url: str | None = None


class MatrixRow(BaseModel):
    name: str
    group: str | None = None
    is_ok: bool = False
    cells: list[MatrixCell]


class Matrix(BaseModel):
    """ "Ikke fundet" betyder: ikke fundet i radarens kilder — ikke at
    selskabet ikke bruger teknologien."""

    columns: list[TechnologyRef] = Field(default_factory=list)
    rows: list[MatrixRow] = Field(default_factory=list)
    peers_without: list[str] = Field(default_factory=list)
    peer_total: int = PEER_TOTAL
    more_columns: int = 0
    # Seneste gennemførte søgning i kilderne.
    searched_at: datetime | None = None


class OkStatus(BaseModel):
    """OK's offentlige status for én teknologi, registreret af Admin med en
    offentlig kilde (fx ok.dk). Aldrig interne oplysninger."""

    stage: Literal["drift", "pilot"]
    source_url: str
    note: str | None = None


def build_matrix(
    cases: list[CaseCard],
    technologies: list[TechnologyCard],
    ok_status: dict[str, OkStatus],
    searched_at: datetime | None = None,
) -> Matrix:
    best: dict[tuple[str, uuid.UUID], CaseCard] = {}
    for card in cases:
        if card.peer is None or card.technology is None:
            continue
        key = (card.peer, card.technology.id)
        current = best.get(key)
        if (
            current is None
            or _CELL_RANK[_cell_state(card.stage)] > _CELL_RANK[_cell_state(current.stage)]
        ):
            best[key] = card
    labels = {t.id: t.label for t in technologies}
    for card in cases:
        if card.technology is not None:
            labels.setdefault(card.technology.id, card.technology.label)
    ok_ids = {uuid.UUID(k) for k in ok_status if _is_uuid(k) and uuid.UUID(k) in labels}

    def weight(tech_id: uuid.UUID) -> tuple[int, int]:
        cells = [c for (_, t), c in best.items() if t == tech_id]
        live = sum(1 for c in cells if _cell_state(c.stage) == "drift")
        return (live, len(cells))

    ranked = sorted({t for _, t in best} | ok_ids, key=lambda t: weight(t), reverse=True)
    columns = ranked[:_MAX_COLUMNS]
    rows: list[MatrixRow] = []
    if ok_ids:
        cells = []
        for tech_id in columns:
            status = ok_status.get(str(tech_id))
            if status is None:
                cells.append(MatrixCell(state="ingen", label=_CELL_LABELS["ingen"]))
            else:
                cells.append(
                    MatrixCell(
                        state=status.stage,
                        label=_CELL_LABELS[status.stage],
                        href=status.source_url,
                        source_url=status.source_url,
                    )
                )
        rows.append(MatrixRow(name="OK", is_ok=True, cells=cells))
    with_cases = {peer for peer, _ in best}
    for peer in PEERS:
        if peer.name not in with_cases:
            continue
        cells = []
        for tech_id in columns:
            found = best.get((peer.name, tech_id))
            if found is None:
                cells.append(MatrixCell(state="ingen", label=_CELL_LABELS["ingen"]))
            else:
                state = _cell_state(found.stage)
                cells.append(
                    MatrixCell(
                        state=state,
                        label=_CELL_LABELS[state],
                        href=case_href(found),
                        source_url=found.source.url,
                    )
                )
        rows.append(MatrixRow(name=peer.name, group=peer.group, cells=cells))
    return Matrix(
        columns=[TechnologyRef(id=t, label=labels[t]) for t in columns],
        rows=rows,
        peers_without=[p.name for p in PEERS if p.name not in with_cases],
        more_columns=max(0, len(ranked) - len(columns)),
        searched_at=searched_at,
    )


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


# --- Overskriften ---


class Headline(BaseModel):
    text: str
    href: str | None = None


def headline(cases: list[CaseCard], matrix: Matrix) -> Headline:
    peer_columns = [
        (column, [row.cells[i] for row in matrix.rows if not row.is_ok])
        for i, column in enumerate(matrix.columns)
    ]
    if peer_columns:
        column, cells = max(
            peer_columns,
            key=lambda item: (
                sum(1 for c in item[1] if c.state == "drift"),
                sum(1 for c in item[1] if c.state != "ingen"),
            ),
        )
        live = sum(1 for c in cells if c.state == "drift")
        started = sum(1 for c in cells if c.state != "ingen")
        if live:
            text = (
                f"{column.label}: {live} af {PEER_TOTAL} selskaber, der ligner OK, har det i drift."
            )
        elif started:
            text = (
                f"{column.label}: {started} af {PEER_TOTAL} selskaber, der ligner OK, "
                "er i gang. Ingen har det i drift endnu."
            )
        else:
            text = ""
        if text:
            return Headline(text=text, href="#overblik")
    nordic = [c for c in cases if c.region in ("danmark", "norden") and c.technology]
    live_nordic = [c for c in nordic if c.stage in LIVE_STAGES] or nordic
    if live_nordic:
        counts: dict[uuid.UUID, int] = {}
        for card in live_nordic:
            assert card.technology is not None
            counts[card.technology.id] = counts.get(card.technology.id, 0) + 1
        top = max(counts, key=lambda t: counts[t])
        label = next(
            c.technology.label for c in live_nordic if c.technology and c.technology.id == top
        )
        return Headline(
            text=(
                f"Ingen af de {PEER_TOTAL}, der ligner OK, har en dokumenteret AI-case endnu. "
                f"Længst fremme i Norden: {label}."
            ),
            href=f"/cases?teknologi={top}",
        )
    if cases:
        return Headline(
            text=(
                f"Radaren har fundet {len(cases)} cases, men ingen fra Danmark eller Norden endnu."
            ),
            href="/cases",
        )
    return Headline(text="Radaren har ikke fundet cases endnu.")


# --- Siden sidst ---


class SinceLine(BaseModel):
    text: str
    href: str | None = None
    source_url: str | None = None


class SinceLast(BaseModel):
    lines: list[SinceLine] = Field(default_factory=list)
    # Står der, når der ikke er linjer: intet nyt, eller første udgave.
    note: str | None = None


def snapshot(cases: list[CaseCard], technologies: list[TechnologyCard]) -> dict[str, Any]:
    """Det, næste version sammenlignes med. Gemmes ved godkendelse."""
    return {
        "cases": {case_key(c): c.stage or "" for c in cases},
        "status": {str(t.id): t.status for t in technologies if t.case_count or t.vendors},
    }


def since_last(
    cases: list[CaseCard],
    technologies: list[TechnologyCard],
    previous: dict[str, Any] | None,
    previous_at: datetime | None,
) -> SinceLast:
    if not previous:
        return SinceLast(note="Første udgave. Næste udgave viser, hvad der er nyt.")
    old_cases: dict[str, str] = previous.get("cases", {})
    old_status: dict[str, str] = previous.get("status", {})
    ranked: list[tuple[int, SinceLine]] = []
    for card in cases:
        key = case_key(card)
        technology = card.technology.label if card.technology else card.technology_name or "AI"
        stage = card.stage_label.lower() if card.stage_label else "fase ikke oplyst"
        if key not in old_cases:
            if card.peer:
                rank, text = 0, f"Nyt hos {card.company}: {technology} ({stage})."
            elif card.region in ("danmark", "norden"):
                where = card.country_label or card.region_label
                rank, text = 3, f"Ny case fra {where}: {card.company} – {technology} ({stage})."
            else:
                continue
        elif card.stage in LIVE_STAGES and old_cases[key] not in LIVE_STAGES:
            rank = 1 if card.peer else 3
            text = f"{card.company} har nu {technology} i drift."
        else:
            continue
        line = SinceLine(text=text, href=case_href(card), source_url=card.source.url)
        ranked.append((rank, line))
    for tech in technologies:
        old = old_status.get(str(tech.id))
        if tech.case_count == 0 and not tech.vendors:
            continue
        source = next((v.source.url for v in tech.vendors if v.source and v.source.url), None)
        href = f"/teknologier#tech-{tech.id}"
        if old is None:
            vendor = next((v.name for v in tech.vendors if not v.via_case), None)
            text = f"Nyt på markedet: {tech.label}" + (f" fra {vendor}." if vendor else ".")
            ranked.append((4, SinceLine(text=text, href=href, source_url=source)))
        elif old != tech.status and STATUS_ORDER.get(tech.status, 9) < STATUS_ORDER.get(old, 9):
            text = f"{tech.label} er nu {tech.status_label} (før: {STATUS_LABELS.get(old, old)})."
            ranked.append((2, SinceLine(text=text, href=href, source_url=source)))
    ranked.sort(key=lambda item: item[0])
    lines = [line for _, line in ranked[:_MAX_SINCE]]
    note = None
    if not lines:
        note = f"Intet nyt siden {short_date(previous_at)}." if previous_at else "Intet nyt."
    return SinceLast(lines=lines, note=note)
