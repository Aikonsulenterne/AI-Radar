"""Kørsler af ingestion/AI-workeren: ugentligt og on demand.

Render free tier har ingen baggrundsproces, så workeren køres i API'et:
POST /runs opretter en kørsel og udfører den efter svaret. Den ugentlige
udløser (GitHub Actions) autentificerer med X-Worker-Token; "Kør nu" i admin
med Admin-login. Kørslen henter kun kuraterede kilder fra Source Registry og
foreslår claims — publicering kræver fortsat et menneske.
"""

import hmac
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.provider import AIProvider, get_ai_provider
from app.auth import CurrentUser, get_current_user, require_role
from app.config import get_settings
from app.db import get_db, get_session_factory
from app.enums import RunTrigger, UserRole
from app.errors import ApiError
from app.models_runs import WorkerRun
from app.schemas_runs import RunRequest, WorkerRunOut
from app.worker import execute_run, start_run

router = APIRouter(prefix="/runs", tags=["runs"])


def run_ai_provider() -> AIProvider | None:
    """None betyder: kilder hentes, men dokumenterne AI-behandles ikke."""
    return get_ai_provider()


def _authorize(request: Request, db: Session) -> CurrentUser | None:
    """Worker-token (planlagt udløser) eller Admin-login. None = token."""
    token = request.headers.get("x-worker-token")
    if token is not None:
        expected = get_settings().worker_trigger_token
        if expected and hmac.compare_digest(token.encode(), expected.encode()):
            return None
        raise ApiError(401, "unauthorized", "Ugyldigt worker-token.")
    user = get_current_user(request, db)
    return require_role(UserRole.admin)(user)


@router.post("", response_model=WorkerRunOut, status_code=202)
def trigger_run(
    request: Request,
    background: BackgroundTasks,
    body: RunRequest | None = None,
    db: Session = Depends(get_db),
    factory: sessionmaker[Session] = Depends(get_session_factory),
    provider: AIProvider | None = Depends(run_ai_provider),
) -> WorkerRunOut:
    user = _authorize(request, db)
    run = start_run(
        db,
        trigger=RunTrigger.schedule if user is None else RunTrigger.manual,
        force_all=(body or RunRequest()).force_all,
        started_by=user.user_id if user is not None else None,
    )
    background.add_task(execute_run, factory, provider, run.id)
    return WorkerRunOut.model_validate(run)


@router.get("", response_model=list[WorkerRunOut])
def list_runs(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[WorkerRunOut]:
    _authorize(request, db)
    rows = db.scalars(select(WorkerRun).order_by(WorkerRun.started_at.desc()).limit(limit)).all()
    return [WorkerRunOut.model_validate(row) for row in rows]


@router.get("/{run_id}", response_model=WorkerRunOut)
def get_run(run_id: uuid.UUID, request: Request, db: Session = Depends(get_db)) -> WorkerRunOut:
    _authorize(request, db)
    run = db.get(WorkerRun, run_id)
    if run is None:
        raise ApiError(404, "not_found", "Kørslen findes ikke.")
    return WorkerRunOut.model_validate(run)
