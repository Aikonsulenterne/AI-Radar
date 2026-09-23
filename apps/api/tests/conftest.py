"""Testopsætning.

Miljøet sættes FØR app-moduler importeres: rigtig JWT-validering (test-secret),
lokal storage i temp-mappe og SQLite in-memory som standard-testdatabase.

Med TEST_DATABASE_URL kører samme testsuite mod PostgreSQL, hvor skemaet
kommer fra supabase/migrations i stedet for ORM'ens create_all. Det er den
kørsel, der fanger uoverensstemmelser mellem ORM-modeller og migrations —
dem kan SQLite ikke se, fordi SQLite-skemaet bygges af modellerne selv.
"""

import os
import tempfile
from urllib.parse import urlsplit

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# Suiten truncater alle tabeller før hver test. Et fejlagtigt peg på staging
# eller production ville slette alt, så kun lokale databaser accepteres.
if TEST_DATABASE_URL and urlsplit(TEST_DATABASE_URL).hostname not in ("localhost", "127.0.0.1"):
    raise RuntimeError(
        "TEST_DATABASE_URL skal pege på en lokal database — testsuiten sletter alle data."
    )

os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-0123456789-abcdefghijklm"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_ROOT"] = tempfile.mkdtemp(prefix="ai-radar-test-storage-")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "sqlite://"
os.environ["SUPABASE_URL"] = "https://test-projekt.supabase.co"

import time  # noqa: E402
import uuid  # noqa: E402
from collections.abc import Generator  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.enums import UserRole  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Profile  # noqa: E402

SessionFactory = sessionmaker[Session]


def _truncate_all(engine: Engine) -> None:
    """Tøm alle tabeller i det migrerede skema, så hver test starter ens."""
    with engine.begin() as connection:
        tables = connection.execute(
            text("select tablename from pg_tables where schemaname = 'public'")
        ).scalars()
        names = ", ".join(f'"{name}"' for name in tables)
        if names:
            connection.execute(text(f"truncate {names} restart identity cascade"))


@pytest.fixture()
def db_session_factory() -> Generator[SessionFactory, None, None]:
    if TEST_DATABASE_URL:
        # Skemaet ejes af migrations (kørt før pytest); create_all bruges ikke.
        engine = create_engine(TEST_DATABASE_URL)
        _truncate_all(engine)
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    _seed_technologies(factory)
    yield factory
    engine.dispose()


def _seed_technologies(factory: SessionFactory) -> None:
    """Spejler supabase/seed.sql for de teknologier og problemer, testene bruger."""
    from app.enums import EntityType, TechHorizon
    from app.models_claims import EntityAlias, Technology
    from app.models_opportunities import ProblemTaxonomy

    with factory() as session:
        technology = Technology(
            name="Agent Assist",
            slug="agent-assist",
            definition="AI-støtte til medarbejdere under kundekontakt.",
            horizon=TechHorizon.now,
        )
        session.add(technology)
        session.flush()
        session.add(
            EntityAlias(
                entity_type=EntityType.technology,
                entity_id=technology.id,
                alias="Agent Assist",
                normalized_alias="agent assist",
            )
        )
        session.add(
            ProblemTaxonomy(
                name="Store mailmængder",
                description="Høj volumen af indgående mails belaster behandlingen.",
                area="Kundecenter",
            )
        )
        session.commit()


@pytest.fixture()
def client(db_session_factory: SessionFactory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = db_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, "test-secret-0123456789-abcdefghijklm", algorithm="HS256")


def _seed_user(factory: SessionFactory, role: UserRole) -> dict[str, str]:
    user_id = uuid.uuid4()
    with factory() as session:
        session.add(Profile(user_id=user_id, role=role))
        session.commit()
    return {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture()
def admin_headers(db_session_factory: SessionFactory) -> dict[str, str]:
    return _seed_user(db_session_factory, UserRole.admin)


@pytest.fixture()
def reviewer_headers(db_session_factory: SessionFactory) -> dict[str, str]:
    return _seed_user(db_session_factory, UserRole.reviewer)


@pytest.fixture()
def reader_headers(db_session_factory: SessionFactory) -> dict[str, str]:
    return _seed_user(db_session_factory, UserRole.reader)


# --- Delt fake AI-provider og dokument-helper (Slice 2/3-tests) ---

import json  # noqa: E402
from typing import Any  # noqa: E402

from app.routes.documents import ai_provider_dep  # noqa: E402

DOC_TEXT = (
    "Danske Bank bruger Agent Assist i kundeservice. "
    "Banken rapporterer 20 procent lavere efterbehandlingstid."
)

EXTRACTION_RESPONSE = {
    "claims": [
        {
            "claim_type": "adoption",
            "predicate": "USES_CAPABILITY",
            "subject_name": "Danske Bank",
            "object_name": "Agent Assist",
            "object_text": None,
            "supporting_excerpt": "Danske Bank bruger Agent Assist i kundeservice.",
        },
        {
            "claim_type": "effect",
            "predicate": "REPORTED_EFFECT",
            "subject_name": "Danske Bank",
            "object_name": None,
            "object_text": "20 procent lavere efterbehandlingstid",
            "supporting_excerpt": "Banken rapporterer 20 procent lavere efterbehandlingstid.",
        },
        {
            "claim_type": "effect",
            "predicate": "REPORTED_EFFECT",
            "subject_name": "Danske Bank",
            "object_name": None,
            "object_text": "opfundet effekt",
            "supporting_excerpt": "Dette uddrag findes ikke i dokumentet.",
        },
    ]
}


class FakeProvider:
    """Returnerer faste svar pr. prompt-id; kan fejle med ugyldig JSON."""

    def __init__(
        self,
        relevance: dict[str, Any] | None = None,
        extraction: dict[str, Any] | None = None,
        invalid_json: bool = False,
        opportunity: dict[str, Any] | None = None,
    ) -> None:
        self.relevance = relevance or {"relevant": True, "reason": "AI-adoption omtalt"}
        self.extraction = extraction or EXTRACTION_RESPONSE
        self.invalid_json = invalid_json
        self.opportunity = opportunity
        self.calls: list[str] = []
        self.prompts: list[str] = []

    def complete_text(
        self,
        *,
        prompt_id: str,
        prompt_version: str,
        system: str,
        user: str,
        document_id: uuid.UUID | None = None,
    ) -> str:
        self.calls.append(prompt_id)
        self.prompts.append(user)
        if self.invalid_json:
            return "not json at all"
        if prompt_id == "relevance_classification":
            return json.dumps(self.relevance)
        if prompt_id == "opportunity_proposal":
            return json.dumps(self.opportunity or {"proposal": None, "reason": "intet match"})
        return json.dumps(self.extraction)


@pytest.fixture()
def fake_provider() -> Any:
    provider = FakeProvider()
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    yield provider
    app.dependency_overrides.pop(ai_provider_dep, None)


def _upload_document(client: TestClient, headers: dict[str, str]) -> str:
    source = client.post(
        "/api/v1/sources",
        json={
            "name": "Testmedie",
            "source_type": "media",
            "retrieval_method": "manual_upload",
            "access_class": "public",
        },
        headers=headers,
    ).json()
    upload = client.post(
        f"/api/v1/sources/{source['id']}/documents",
        files={"file": ("artikel.txt", DOC_TEXT.encode(), "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    document_id: str = upload.json()["document"]["id"]
    return document_id
