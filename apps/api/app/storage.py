"""Storage-adapters (Technical Master §7).

Originale dokumenter gemmes i private buckets; databasen gemmer storage-path
som autoritativ reference. Signed URLs udstedes kortvarigt. Supabase-adgang
er isoleret her, så objektlageret senere kan udskiftes (S3-kompatibelt).
"""

from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Protocol

import httpx

from app.config import get_settings
from app.errors import ApiError


class StorageAdapter(Protocol):
    def save(self, path: str, data: bytes, content_type: str) -> None: ...

    def signed_url(self, path: str, expires_seconds: int = 300) -> str | None: ...


def _validate_relative_path(path: str) -> PurePosixPath:
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ApiError(500, "storage_error", "Ugyldig storage-sti.")
    return pure


class LocalStorage:
    """Filsystem-lager til lokal udvikling og tests. Ingen signerede URLs."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, path: str, data: bytes, content_type: str) -> None:
        target = self._root / _validate_relative_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def signed_url(self, path: str, expires_seconds: int = 300) -> str | None:
        return None


class SupabaseStorage:
    """Supabase Storage via REST. Service-role key bruges kun server-side."""

    def __init__(self, base_url: str, service_role_key: str, bucket: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._key = service_role_key
        self._bucket = bucket

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._key}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def save(self, path: str, data: bytes, content_type: str) -> None:
        _validate_relative_path(path)
        url = f"{self._base_url}/storage/v1/object/{self._bucket}/{path}"
        try:
            response = httpx.post(
                url, content=data, headers=self._headers(content_type), timeout=30.0
            )
        except httpx.HTTPError as exc:
            raise ApiError(502, "storage_failed", "Dokumentlageret kunne ikke nås.") from exc
        # 409: objektet findes allerede — idempotent nok, da path er hash-baseret.
        if response.status_code not in (200, 201, 409):
            raise ApiError(502, "storage_failed", "Dokumentet kunne ikke gemmes i lageret.")

    def signed_url(self, path: str, expires_seconds: int = 300) -> str | None:
        _validate_relative_path(path)
        url = f"{self._base_url}/storage/v1/object/sign/{self._bucket}/{path}"
        try:
            response = httpx.post(
                url,
                json={"expiresIn": expires_seconds},
                headers=self._headers("application/json"),
                timeout=30.0,
            )
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        signed = response.json().get("signedURL")
        if not isinstance(signed, str):
            return None
        return f"{self._base_url}/storage/v1{signed}"


@lru_cache
def get_storage() -> StorageAdapter:
    settings = get_settings()
    if settings.storage_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Supabase Storage kræver SUPABASE_URL og service-role key.")
        return SupabaseStorage(
            base_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_storage_bucket,
        )
    return LocalStorage(Path(settings.storage_local_root))
