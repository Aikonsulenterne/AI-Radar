"""Testopsætning.

Miljøet sættes FØR app-moduler importeres: rigtig JWT-validering (test-secret),
lokal storage i temp-mappe og SQLite in-memory som unit-test-database.
Migrations valideres mod rigtig PostgreSQL i CI (migrations-jobbet).
"""

import os
import tempfile

os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-0123456789-abcdefghijklm"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_ROOT"] = tempfile.mkdtemp(prefix="ai-radar-test-storage-")
os.environ["DATABASE_URL"] = "sqlite://"

import time  # noqa: E402
import uuid  # noqa: E402
from collections.abc import Generator  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.enums import UserRole  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Profile  # noqa: E402

SessionFactory = sessionmaker[Session]


@pytest.fixture()
def db_session_factory() -> Generator[SessionFactory, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    yield factory
    engine.dispose()


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
