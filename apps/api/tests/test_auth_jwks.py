"""ES256-tokens (moderne Supabase signing keys) valideres via JWKS."""

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.enums import UserRole
from app.models import Profile
from tests.conftest import SessionFactory


def test_es256_token_is_validated_via_jwks(
    client: TestClient,
    db_session_factory: SessionFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    monkeypatch.setattr(auth_module, "_jwks_signing_key", lambda token: public_key)

    user_id = uuid.uuid4()
    with db_session_factory() as session:
        session.add(Profile(user_id=user_id, role=UserRole.reader))
        session.commit()

    token = jwt.encode(
        {"sub": str(user_id), "aud": "authenticated", "exp": int(time.time()) + 3600},
        private_key,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )
    response = client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # Manipuleret token (forkert nøgle) afvises.
    other_key = ec.generate_private_key(ec.SECP256R1())
    forged = jwt.encode(
        {"sub": str(user_id), "aud": "authenticated", "exp": int(time.time()) + 3600},
        other_key,
        algorithm="ES256",
    )
    forged_response = client.get("/api/v1/sources", headers={"Authorization": f"Bearer {forged}"})
    assert forged_response.status_code == 401


def test_unknown_algorithm_is_rejected(client: TestClient) -> None:
    token = jwt.encode({"sub": "x", "aud": "authenticated"}, "secret", algorithm="HS384")
    response = client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
