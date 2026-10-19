"""Til OK: direktørens side (Product Master §19–22).

Det første skærmbillede — overskrift, konkurrentoverblik, siden sidst og
gevinstspænd — beregnes af serveren (market/overview.py). AI'en skriver kun
forslag, beslutningsspørgsmål og tabellernes tekst og vælger blandt fund,
der findes; serveren slår hver henvisning op igen ved læsning, så et skjult
fund aldrig vises, og hver case står højst én gang i tabellerne.

Admin ser kladden; alle andre ser den senest godkendte version. Ved
godkendelse gemmes et øjebliksbillede, som næste version sammenlignes med.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import (
    AIDocumentRejected,
    AIProvider,
    AIProviderError,
    AIProviderRejected,
    AIRefusal,
)
from app.ai.schemas import AISchemaError
from app.audit import AuditAction, AuditEntity, record
from app.auth import CurrentUser, require_role
from app.config import get_settings
from app.db import get_db
from app.enums import RunStatus, UserRole
from app.errors import ApiError
from app.mailer import send_brief
from app.market.catalog import AREA_LABELS, OK_PROBLEMS
from app.market.overview import (
    Gain,
    Headline,
    Matrix,
    OkStatus,
    SinceLast,
    build_matrix,
    case_href,
    gain_for,
    headline,
    short_date,
    since_last,
    snapshot,
)
from app.market.spreadsheet import SheetRow, build_workbook, effect_percent
from app.market.store import (
    Answer,
    StoredAnswer,
    decision_key,
    latest_answers,
    ok_status,
    record_answer,
    set_ok_status,
)
from app.market.views import (
    CaseCard,
    CaseSummary,
    TechnologyCard,
    case_cards,
    case_summary,
    technology_cards,
    technology_label,
    visible_rows,
)
from app.models_claims import Technology
from app.models_runs import WorkerRun
from app.models_settings import AppSetting
from app.pipeline.market import OK_BRIEF_KEY, generate_ok_brief
from app.routes.documents import ai_provider_dep

router = APIRouter(tags=["ok-brief"])

OK_BRIEF_PUBLISHED_KEY = "ok_brief_published"
_AUDIT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-radar:setting:ok_brief")
_STATUS_AUDIT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-radar:setting:ok_public_status")
_MONTHS = (
    "januar februar marts april maj juni juli august september oktober november december"
).split()
# Rækkefølgen på Til OK.
_AREA_ORDER = ("kundeservice", "support", "salg")
_MAX_FOLLOW_UPS = 3


# --- Svarmodeller ---


class StatusTechnology(BaseModel):
    id: uuid.UUID
    label: str
    status: str
    status_label: str


class Reference(BaseModel):
    """Hvem vi kan ringe til: virksomheden bag casen."""

    company: str
    country: str | None
    href: str
    source_url: str | None


class RecommendationOut(BaseModel):
    action: str
    owner: str
    duration: str
    first_step: str = ""
    technology: StatusTechnology | None = None
    reference: Reference | None = None
    vendor: str | None = None
    gain: Gain | None = None


class DecisionOut(BaseModel):
    key: str
    question: str
    owner: str = ""
    duration: str = ""
    first_step: str = ""
    technology: StatusTechnology | None = None
    gain: Gain | None = None
    answer: Answer | None = None
    answered_at: datetime | None = None
    # Kun spørgsmål i den godkendte version kan besvares.
    answerable: bool = False


class FollowUp(BaseModel):
    question: str
    answered_at: datetime
    label: str


class MoreCase(BaseModel):
    id: uuid.UUID
    company: str
    country: str | None
    what: str
    source_url: str | None


class ProblemRow(BaseModel):
    key: str
    title: str
    technology: StatusTechnology | None
    proof: CaseSummary
    because: str
    next_step: str
    more: list[MoreCase]
    vendors: list[str]
    reference: str
    # Hvad OK selv skal slå op internt; radaren kender aldrig OK's tal.
    lookup: str = ""
    # Laveste andel i casens effekt (brøk), til regnearket.
    effect_pct: float | None = None
    gain: Gain | None = None


class AreaRows(BaseModel):
    area: str
    label: str
    rows: list[ProblemRow]


class Undocumented(BaseModel):
    title: str
    area_label: str


class OkBriefOut(BaseModel):
    generated_at: datetime | None = None
    month_label: str | None = None
    prompt_version: str | None = None
    technology_count: int = 0
    case_count: int = 0
    headline: Headline | None = None
    matrix: Matrix = Field(default_factory=Matrix)
    since_last: SinceLast = Field(default_factory=SinceLast)
    decisions: list[DecisionOut] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    areas: list[AreaRows] = Field(default_factory=list)
    undocumented: list[Undocumented] = Field(default_factory=list)
    # godkendt: direktøren ser denne version · kladde: ny version venter på
    # konsulentens godkendelse (kun Admin ser kladden) · ingen: intet godkendt.
    state: Literal["godkendt", "kladde", "ingen"] = "ingen"
    approved_at: datetime | None = None
    # Kun til Admin: hvad der skete med mailen ved seneste godkendelse.
    mail_status: str | None = None
    # Gemmes direktørens svar i radaren? Fra, indtil OK har godkendt det.
    decisions_stored: bool = False


# --- Opbygning ---


@dataclass
class _Data:
    cases: list[CaseCard]
    technologies: list[TechnologyCard]

    @classmethod
    def load(cls, db: Session) -> "_Data":
        rows = visible_rows(db)
        return cls(cases=case_cards(db, rows), technologies=technology_cards(db, rows))


def _stored(db: Session, key: str) -> dict[str, Any]:
    row = db.get(AppSetting, key)
    return row.value if row else {}


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _stored_decisions(value: dict[str, Any]) -> list[dict[str, Any]]:
    """Spørgsmål fra versionen; ældre versioner gemte dem som tekst."""
    return [{"question": d} if isinstance(d, str) else d for d in value.get("decisions", [])]


def _brief_out(
    db: Session,
    data: _Data,
    value: dict[str, Any],
    since: SinceLast,
    answerable_keys: set[str],
) -> OkBriefOut:
    cases, technologies = data.cases, data.technologies
    # Et gemt fund kan siden være slået sammen med andre: slå op på alle id'er.
    case_by_item = {item_id: card for card in cases for item_id in card.item_ids}
    tech_by_id = {t.id: t for t in technologies}

    def find_case(raw: str | None) -> CaseCard | None:
        try:
            return case_by_item.get(uuid.UUID(raw)) if raw else None
        except ValueError:
            return None

    def find_tech(raw: str | None) -> TechnologyCard | None:
        try:
            return tech_by_id.get(uuid.UUID(raw)) if raw else None
        except ValueError:
            return None

    def status_tech(tech: TechnologyCard | None) -> StatusTechnology | None:
        if tech is None:
            return None
        return StatusTechnology(
            id=tech.id, label=tech.label, status=tech.status, status_label=tech.status_label
        )

    searched_at = db.scalar(
        select(func.max(WorkerRun.finished_at)).where(WorkerRun.status == RunStatus.succeeded)
    )
    matrix = build_matrix(cases, technologies, ok_status(db), searched_at)
    stored_answers = get_settings().store_decisions
    answers = latest_answers(db) if stored_answers else {}

    decisions: list[DecisionOut] = []
    for entry in _stored_decisions(value):
        key = decision_key(entry["question"])
        tech = find_tech(entry.get("technology_id"))
        given: StoredAnswer | None = answers.get(key)
        decisions.append(
            DecisionOut(
                key=key,
                question=entry["question"],
                owner=entry.get("owner", ""),
                duration=entry.get("duration", ""),
                first_step=entry.get("first_step", ""),
                technology=status_tech(tech),
                gain=gain_for(tech.id if tech else None, cases),
                answer=given.answer if given else None,
                answered_at=given.answered_at if given else None,
                answerable=stored_answers and key in answerable_keys,
            )
        )
    current_keys = {d.key for d in decisions}
    follow_ups = [
        FollowUp(
            question=a.question,
            answered_at=a.answered_at,
            label=f"Du sagde ja {short_date(a.answered_at)}",
        )
        for a in sorted(answers.values(), key=lambda a: a.answered_at, reverse=True)
        if a.answer == "ja" and a.key not in current_keys
    ][:_MAX_FOLLOW_UPS]

    recommendations: list[RecommendationOut] = []
    for r in value.get("recommendations", []):
        tech = find_tech(r.get("technology_id"))
        case = find_case(r.get("case_id"))
        vendor = case.vendor if case and case.vendor else None
        if vendor is None and tech is not None:
            vendor = next((v.name for v in tech.vendors if not v.via_case), None)
        recommendations.append(
            RecommendationOut(
                action=r["action"],
                owner=r.get("owner", ""),
                duration=r.get("duration", ""),
                first_step=r.get("first_step", ""),
                technology=status_tech(tech),
                reference=Reference(
                    company=case.company,
                    country=case.country_label,
                    href=case_href(case),
                    source_url=case.source.url,
                )
                if case
                else None,
                vendor=vendor,
                gain=gain_for(tech.id if tech else None, cases),
            )
        )

    shown: set[uuid.UUID] = set()  # hver case højst én gang i tabellerne
    by_area: dict[str, list[ProblemRow]] = {a: [] for a in _AREA_ORDER}
    undocumented: list[Undocumented] = []
    stored = {p["key"]: p for p in value.get("problems", [])}
    for problem in OK_PROBLEMS:
        entry = stored.get(problem.key, {})
        best = find_case(entry.get("best_case_id"))
        if best is not None and best.id in shown:
            best = None
        if best is None:
            undocumented.append(
                Undocumented(title=problem.name, area_label=AREA_LABELS[problem.area])
            )
            continue
        shown.add(best.id)
        more: list[MoreCase] = []
        for raw in entry.get("more_case_ids", []):
            card = find_case(raw)
            if card is not None and card.id not in shown:
                shown.add(card.id)
                more.append(
                    MoreCase(
                        id=card.id,
                        company=card.company,
                        country=card.country_label,
                        what=card.what_they_did or card.effect or "",
                        source_url=card.source.url,
                    )
                )
        tech = find_tech(entry.get("technology_id"))
        if tech is None and best.technology is not None:
            tech = tech_by_id.get(best.technology.id)
        vendors = [v.name for v in (tech.vendors if tech else []) if not v.via_case][:3]
        if not vendors and best.vendor:
            vendors = [best.vendor]
        by_area[problem.area].append(
            ProblemRow(
                key=problem.key,
                title=problem.name,
                technology=status_tech(tech),
                proof=case_summary(best),
                because=entry.get("why_comparable", ""),
                next_step=entry.get("next_step", ""),
                more=more,
                vendors=vendors,
                reference=best.company,
                lookup=problem.lookup,
                effect_pct=effect_percent(best.effect),
                gain=gain_for(tech.id if tech else None, cases),
            )
        )

    generated_at = _parse(value.get("generated_at"))
    return OkBriefOut(
        generated_at=generated_at,
        month_label=(
            f"{_MONTHS[generated_at.month - 1]} {generated_at.year}" if generated_at else None
        ),
        prompt_version=value.get("prompt_version"),
        technology_count=sum(1 for t in technologies if t.case_count or t.vendors),
        case_count=len(cases),
        headline=headline(cases, matrix),
        matrix=matrix,
        since_last=since,
        decisions=decisions,
        follow_ups=follow_ups,
        decisions_stored=stored_answers,
        recommendations=recommendations[:3],
        areas=[
            AreaRows(area=a, label=AREA_LABELS[a], rows=by_area[a])
            for a in _AREA_ORDER
            if by_area[a]
        ],
        undocumented=undocumented,
    )


def _published_keys(published: dict[str, Any]) -> set[str]:
    return {decision_key(d["question"]) for d in _stored_decisions(published)}


def _visible_brief(db: Session, user: CurrentUser) -> OkBriefOut:
    """Admin ser kladden (eller den godkendte version, når kladden er
    godkendt); alle andre ser den senest godkendte version."""
    data = _Data.load(db)
    published = _stored(db, OK_BRIEF_PUBLISHED_KEY)
    keys = _published_keys(published)
    approved_at = _parse(published.get("approved_at"))
    if user.role == UserRole.admin:
        draft = _stored(db, OK_BRIEF_KEY)
        if published and draft.get("generated_at") == published.get("generated_at"):
            value, state = published, "godkendt"
        elif draft:
            value, state = draft, "kladde"
        else:
            return OkBriefOut(state="ingen")
        if state == "godkendt":
            since = SinceLast.model_validate(published.get("since_last") or {})
        else:
            since = since_last(
                data.cases, data.technologies, published.get("snapshot"), approved_at
            )
        out = _brief_out(db, data, value, since, keys)
        return out.model_copy(
            update={
                "state": state,
                "approved_at": approved_at,
                "mail_status": published.get("mail_status"),
            }
        )
    if not published:
        return OkBriefOut(state="ingen")
    since = SinceLast.model_validate(published.get("since_last") or {})
    out = _brief_out(db, data, published, since, keys)
    return out.model_copy(update={"state": "godkendt", "approved_at": approved_at})


# --- Endpoints ---


@router.get("/ok-brief", response_model=OkBriefOut)
def get_ok_brief(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> OkBriefOut:
    """Konsulenten godkender forsiden, før direktøren ser den (beslutning
    2026-10-14: én fejl på forsiden koster mere end fem minutters kontrol)."""
    return _visible_brief(db, user)


@router.get("/ok-brief/regneark.xlsx", response_class=Response)
def get_ok_brief_spreadsheet(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> Response:
    """Regneark med den version af Til OK, brugeren ser. Kun radarens
    offentlige fund og formler — OK's tal skrives ind på OK's egen pc."""
    brief = _visible_brief(db, user)
    rows = [
        SheetRow(
            problem_key=row.key,
            area_label=area.label,
            problem=row.title,
            technology=row.technology.label if row.technology else "Ikke oplyst",
            case=" · ".join(filter(None, [row.proof.company, row.proof.country])),
            effect=row.proof.text,
            source_url=row.proof.source_url,
            effect_pct=row.effect_pct,
        )
        for area in brief.areas
        for row in area.rows
    ]
    return Response(
        content=build_workbook(rows, brief.month_label),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="til-ok-regnestykke.xlsx"'},
    )


class ApproveOut(BaseModel):
    approved_at: datetime
    mail: str


@router.post("/ok-brief/approve", response_model=ApproveOut)
def approve_ok_brief(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> ApproveOut:
    """Godkend den nyeste kladde: direktøren ser den, og den sendes som mail,
    hvis SMTP er sat op. "Siden sidst" fastfryses mod forrige godkendte
    version, og et nyt øjebliksbillede gemmes til næste gang."""
    draft = _stored(db, OK_BRIEF_KEY)
    if not draft:
        raise ApiError(409, "no_draft", "Der er ingen Til OK at godkende endnu.")
    data = _Data.load(db)
    previous = _stored(db, OK_BRIEF_PUBLISHED_KEY)
    since = since_last(
        data.cases,
        data.technologies,
        previous.get("snapshot"),
        _parse(previous.get("approved_at")),
    )
    approved_at = datetime.now(UTC)
    value = {
        **draft,
        "approved_at": approved_at.isoformat(),
        "approved_by_user_id": str(user.user_id) if user.user_id else None,
        "snapshot": snapshot(data.cases, data.technologies),
        "since_last": since.model_dump(mode="json"),
    }
    row = db.get(AppSetting, OK_BRIEF_PUBLISHED_KEY)
    if row is None:
        db.add(AppSetting(key=OK_BRIEF_PUBLISHED_KEY, value=value))
    else:
        row.value = value
        row.updated_at = approved_at
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.published,
        actor_user_id=user.user_id,
        changes={"generated_at": draft.get("generated_at")},
    )
    db.commit()
    out = _brief_out(db, data, value, since, _published_keys(value))
    # Mail kun, når der er noget nyt eller noget at tage stilling til:
    # "Intet nyt" tre gange lærer modtageren at ignorere mailen.
    has_news = bool(since.lines or out.decisions or out.follow_ups)
    mail = send_brief(out.model_dump(mode="json")) if has_news else "ikke sendt (intet nyt)"
    stored = db.get(AppSetting, OK_BRIEF_PUBLISHED_KEY)
    if stored is not None:
        stored.value = {**stored.value, "mail_status": mail}
        db.commit()
    return ApproveOut(approved_at=approved_at, mail=mail)


@router.post("/ok-brief/generate", response_model=OkBriefOut)
def post_generate_ok_brief(
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(ai_provider_dep),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> OkBriefOut:
    try:
        value = generate_ok_brief(db, provider)
    except AIProviderRejected as exc:
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except (AISchemaError, AIRefusal, AIDocumentRejected, AIProviderError) as exc:
        raise ApiError(502, "ok_brief_failed", "Til OK kunne ikke opdateres. Prøv igen.") from exc
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"decisions": len(value["decisions"]), "discarded": value["discarded"]},
    )
    db.commit()
    return _visible_brief(db, user)


class DecisionAnswerIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    answer: Answer


class DecisionAnswerOut(BaseModel):
    key: str
    answer: Answer
    answered_at: datetime


@router.post("/ok-brief/decisions", response_model=DecisionAnswerOut)
def answer_decision(
    body: DecisionAnswerIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> DecisionAnswerOut:
    """Direktørens ja / nej / senere til et spørgsmål i den godkendte Til OK.
    Kun beslutning og dato gemmes — ingen OK-tal — og kun når
    STORE_DECISIONS er slået til efter OK's godkendelse."""
    if not get_settings().store_decisions:
        raise ApiError(
            409,
            "decisions_not_stored",
            "Svar gemmes ikke i radaren, før OK har godkendt det. Svar på mødet.",
        )
    published = _stored(db, OK_BRIEF_PUBLISHED_KEY)
    question = next(
        (
            d["question"]
            for d in _stored_decisions(published)
            if decision_key(d["question"]) == body.key
        ),
        None,
    )
    if question is None:
        raise ApiError(404, "decision_not_found", "Spørgsmålet findes ikke i den godkendte Til OK.")
    stored = record_answer(db, question, body.answer, user.user_id)
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.updated,
        actor_user_id=user.user_id,
        changes={"beslutning": question, "svar": body.answer},
    )
    db.commit()
    return DecisionAnswerOut(key=stored.key, answer=stored.answer, answered_at=stored.answered_at)


# --- OK's offentlige status (Admin) ---


class OkStatusRow(BaseModel):
    technology_id: uuid.UUID
    label: str
    stage: Literal["drift", "pilot"] | None = None
    source_url: str | None = None
    note: str | None = None


class OkStatusIn(BaseModel):
    stage: Literal["drift", "pilot"] | None = None
    source_url: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=200)

    @field_validator("source_url")
    @classmethod
    def _public_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.startswith("https://"):
            raise ValueError("Kilden skal være en offentlig https-adresse, fx på ok.dk.")
        return value


@router.get("/ok-public-status", response_model=list[OkStatusRow])
def list_ok_public_status(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> list[OkStatusRow]:
    """OK's egen række i konkurrentoverblikket. Kun offentligt kendt brug
    med en offentlig kilde, fx en chatbot på ok.dk."""
    current = ok_status(db)
    cards = [t for t in technology_cards(db) if not t.is_new]
    return [
        OkStatusRow(
            technology_id=t.id,
            label=t.label,
            stage=current[str(t.id)].stage if str(t.id) in current else None,
            source_url=current[str(t.id)].source_url if str(t.id) in current else None,
            note=current[str(t.id)].note if str(t.id) in current else None,
        )
        for t in sorted(cards, key=lambda t: t.label.casefold())
    ]


@router.put("/ok-public-status/{technology_id}", response_model=OkStatusRow)
def put_ok_public_status(
    technology_id: uuid.UUID,
    body: OkStatusIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> OkStatusRow:
    technology = db.get(Technology, technology_id)
    if technology is None:
        raise ApiError(404, "not_found", "Teknologien findes ikke.")
    if body.stage is not None and body.source_url is None:
        raise ApiError(422, "validation_error", "Angiv en offentlig kilde, fx siden på ok.dk.")
    status = (
        OkStatus(stage=body.stage, source_url=body.source_url, note=body.note)
        if body.stage is not None and body.source_url is not None
        else None
    )
    set_ok_status(db, technology_id, status)
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_STATUS_AUDIT_ID,
        action=AuditAction.updated,
        actor_user_id=user.user_id,
        changes={"teknologi": technology.name, "status": body.stage, "kilde": body.source_url},
    )
    db.commit()
    return OkStatusRow(
        technology_id=technology_id,
        label=technology_label(technology),
        stage=status.stage if status else None,
        source_url=status.source_url if status else None,
        note=status.note if status else None,
    )
