"""Provider-neutralt AI-lag med OpenAI-kompatibel adapter (Technical Master §10).

Kan konfigureres mod hosted OpenAI-kompatible endpoints, lokal Ollama eller
self-hosted vLLM. Alle kald bærer versioneret prompt-id, model-id og
document-id i logs (aldrig tokens, secrets eller fulde dokumenttekster).
"""

import logging
import time
import uuid
from functools import lru_cache
from typing import Any, Protocol

import httpx

from app.config import get_settings

logger = logging.getLogger("ai_radar.ai")


class AIProviderError(Exception):
    """Kald til AI-provider fejlede (transport eller ugyldigt svar)."""


class AIProvider(Protocol):
    def complete_text(
        self,
        *,
        prompt_id: str,
        prompt_version: str,
        system: str,
        user: str,
        document_id: uuid.UUID | None = None,
    ) -> str: ...


class OpenAICompatProvider:
    """Chat completions mod et OpenAI-kompatibelt endpoint."""

    def __init__(self, base_url: str, api_key: str, model_id: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_id = model_id

    def complete_text(
        self,
        *,
        prompt_id: str,
        prompt_version: str,
        system: str,
        user: str,
        document_id: uuid.UUID | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model_id,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        started = time.monotonic()
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AIProviderError(f"AI-kald fejlede ({exc.__class__.__name__}).") from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        body = response.json()
        usage = body.get("usage") or {}
        logger.info(
            "ai_call prompt=%s v=%s model=%s document=%s latency_ms=%d "
            "prompt_tokens=%s completion_tokens=%s",
            prompt_id,
            prompt_version,
            self._model_id,
            document_id,
            latency_ms,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("AI-svar havde uventet struktur.") from exc
        if not isinstance(content, str):
            raise AIProviderError("AI-svar manglede tekstindhold.")
        return content


@lru_cache
def get_ai_provider() -> AIProvider | None:
    """None når AI ikke er konfigureret — kaldere skal håndtere det eksplicit."""
    settings = get_settings()
    if not settings.ai_provider_base_url or not settings.ai_model_id:
        return None
    return OpenAICompatProvider(
        base_url=settings.ai_provider_base_url,
        api_key=settings.ai_provider_api_key,
        model_id=settings.ai_model_id,
    )
