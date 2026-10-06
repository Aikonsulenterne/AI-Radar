"""Claude-adapter bag samme AIProvider-interface som den OpenAI-kompatible.

Vælges med AI_PROVIDER=anthropic. Pipelinen, prompts og schema-validering er
uændrede: adapteren returnerer modellens tekst, og call_with_schema validerer
den som før. Samme logregler: prompt-id, version, model og tokenforbrug —
aldrig nøgler eller dokumenttekst.
"""

import logging
import time
import uuid
from typing import Any

import anthropic
from anthropic.types import TextBlock

from app.ai.provider import AIDocumentRejected, AIProviderError, AIProviderRejected, AIRefusal

logger = logging.getLogger("ai_radar.ai")

# Rigeligt til et claim-udtræk inkl. modellens tænkning, og under SDK'ets
# grænse for ikke-streamede kald.
_MAX_TOKENS = 16_000


def _strip_code_fence(text: str) -> str:
    """Promptene beder om rå JSON; en ```json-indpakning fjernes defensivt."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        stripped = stripped[first_newline + 1 :] if first_newline != -1 else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


def _credit_exhausted(exc: anthropic.APIStatusError) -> bool:
    """Anthropic svarer 400 (ikke 402/429), når kreditten er brugt op."""
    body: dict[str, Any] = exc.body if isinstance(exc.body, dict) else {}
    raw_error = body.get("error")
    error: dict[str, Any] = raw_error if isinstance(raw_error, dict) else {}
    message = str(error.get("message") or exc.message or "").lower()
    return exc.status_code in (400, 402) and "credit balance" in message


class AnthropicProvider:
    """Messages API via Anthropics officielle SDK."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        client: Any | None = None,
        prompt_models: dict[str, str] | None = None,
    ) -> None:
        self._model_id = model_id
        self._prompt_models = prompt_models or {}
        self._client = client or anthropic.Anthropic(api_key=api_key, timeout=300.0)

    def complete_text(
        self,
        *,
        prompt_id: str,
        prompt_version: str,
        system: str,
        user: str,
        document_id: uuid.UUID | None = None,
    ) -> str:
        model_id = self._prompt_models.get(prompt_id, self._model_id)
        started = time.monotonic()
        try:
            response = self._client.messages.create(
                model=model_id,
                max_tokens=_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIStatusError as exc:
            if _credit_exhausted(exc):
                raise AIProviderRejected(402) from exc
            if exc.status_code == 400:
                raise AIDocumentRejected(
                    "AI-udbyderen afviste forespørgslen for dette dokument (HTTP 400)."
                ) from exc
            if 400 <= exc.status_code < 500:
                raise AIProviderRejected(exc.status_code) from exc
            raise AIProviderError(f"AI-udbyderen svarede med HTTP {exc.status_code}.") from exc
        except anthropic.APIConnectionError as exc:
            raise AIProviderError(f"AI-kald fejlede ({exc.__class__.__name__}).") from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "ai_call prompt=%s v=%s model=%s document=%s latency_ms=%d "
            "prompt_tokens=%s completion_tokens=%s",
            prompt_id,
            prompt_version,
            model_id,
            document_id,
            latency_ms,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        if response.stop_reason == "refusal":
            raise AIRefusal("Modellen afviste at behandle dokumentet.")

        text = "".join(block.text for block in response.content if isinstance(block, TextBlock))
        if not text.strip():
            raise AIProviderError("AI-svar manglede tekstindhold.")
        return _strip_code_fence(text)
