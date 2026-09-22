"""Web fetch (Technical Master §8, trin 1).

Bruges både til direkte web_fetch-kilder og til de artikellinks, et RSS-feed
udpeger. Systemet omgår aldrig paywalls eller adgangskontrol.
"""

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.errors import ApiError

_USER_AGENT = "AI-Radar/0.1 (internt intelligence-vaerktoej, OK)"


@dataclass(frozen=True)
class FetchResult:
    data: bytes
    content_type: str
    final_url: str


def ensure_public_http_url(url: str) -> None:
    """Afviser links, der ikke peger på det offentlige web.

    Links fra et feed er untrusted data (Technical Master §9): uden denne
    kontrol kunne en kilde få serveren til at hente interne adresser og gemme
    svaret som et dokument. DNS-navne, der peger på interne IP'er, fanges
    ikke her — kun skema og adresseliteraler.
    """
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise ApiError(422, "unsafe_url", "Kun http- og https-links hentes.")

    host = parsed.hostname
    if not host:
        raise ApiError(422, "unsafe_url", "Linket mangler et værtsnavn.")
    if host == "localhost" or host.endswith(".localhost"):
        raise ApiError(422, "unsafe_url", "Interne adresser hentes ikke.")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ApiError(422, "unsafe_url", "Interne adresser hentes ikke.")


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
