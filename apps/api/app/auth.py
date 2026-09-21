"""Authentication og authorization (Technical Master §13).

Supabase Auth udsteder JWT'er; API'et validerer signatur og audience og
slår rollen op i den kontrollerede profil-model. Tokens logges aldrig.
Auth er isoleret her, så en anden OIDC-provider senere kan anvendes.

To valideringsveje efter tokenets algoritme:
- ES256/RS256 (moderne Supabase signing keys): offentlig nøgle hentes fra
  projektets JWKS-endpoint (SUPABASE_URL) og caches.
- HS256 (legacy JWT secret): delt secret fra SUPABASE_JWT_SECRET —
  bruges også af unit tests.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Request
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.enums import UserRole
from app.errors import ApiError
from app.models import Profile

_ROLE_RANK: dict[UserRole, int] = {
    UserRole.reader: 0,
    UserRole.reviewer: 1,
    UserRole.admin: 2,
}


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID | None
    role: UserRole


@lru_cache
def _jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")


def _jwks_signing_key(token: str) -> Any:
    """Offentlig nøgle fra Supabase's JWKS — adskilt så tests kan erstatte den."""
    settings = get_settings()
    return _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key


def _decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "unauthorized", "Ugyldigt token.") from exc

    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise ApiError(
                503, "auth_not_configured", "Authentication er ikke konfigureret (JWT secret)."
            )
        key: Any = settings.supabase_jwt_secret
    elif algorithm in ("ES256", "RS256"):
        if not settings.supabase_url:
            raise ApiError(
                503, "auth_not_configured", "Authentication er ikke konfigureret (SUPABASE_URL)."
            )
        try:
            key = _jwks_signing_key(token)
        except jwt.PyJWKClientError as exc:
            raise ApiError(401, "unauthorized", "Tokenets nøgle kunne ikke verificeres.") from exc
    else:
        raise ApiError(401, "unauthorized", "Ukendt token-algoritme.")

    try:
        return jwt.decode(token, key, algorithms=[algorithm], audience="authenticated")
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "unauthorized", "Ugyldigt eller udløbet token.") from exc


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    settings = get_settings()
    header = request.headers.get("authorization")

    if header is None:
        if settings.auth_dev_bypass:
            return CurrentUser(user_id=None, role=UserRole.admin)
        raise ApiError(401, "unauthorized", "Manglende Authorization-header.")

    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "unauthorized", "Ugyldig Authorization-header.")

    payload = _decode_token(token)

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError as exc:
        raise ApiError(401, "unauthorized", "Token mangler gyldigt subject.") from exc

    profile = db.get(Profile, user_id)
    role = profile.role if profile is not None else UserRole.reader
    return CurrentUser(user_id=user_id, role=role)


def require_role(minimum: UserRole) -> Callable[..., CurrentUser]:
    """Dependency: 401 uden gyldig auth, 403 ved utilstrækkelig rolle."""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if _ROLE_RANK[user.role] < _ROLE_RANK[minimum]:
            raise ApiError(403, "forbidden", "Utilstrækkelig rolle til denne handling.")
        return user

    return dependency
