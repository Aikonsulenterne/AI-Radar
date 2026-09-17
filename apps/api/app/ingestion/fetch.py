"""Web fetch (Technical Master §8, trin 1) — den ene simple fetch-metode i Slice 1.

RSS tilføjes senere. Systemet omgår aldrig paywalls eller adgangskontrol.
"""

from dataclasses import dataclass

import httpx

from app.errors import ApiError

_USER_AGENT = "AI-Radar/0.1 (internt intelligence-vaerktoej, OK)"


@dataclass(frozen=True)
class FetchResult:
    data: bytes
    content_type: str
    final_url: str


def fetch_url(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ApiError(
            502, "fetch_failed", f"Kilden svarede med HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        # Sikker fejlbesked: aldrig interne detaljer eller headers.
        raise ApiError(
            502, "fetch_failed", f"Kilden kunne ikke hentes ({exc.__class__.__name__})."
        ) from exc

    data = response.content
    if len(data) > max_bytes:
        raise ApiError(502, "fetch_too_large", "Dokumentet overskrider størrelsesgrænsen.")

    content_type = response.headers.get("content-type", "application/octet-stream")
    return FetchResult(data=data, content_type=content_type, final_url=str(response.url))
