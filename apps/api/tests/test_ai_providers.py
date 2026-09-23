"""AI-adaptere: korrekt tekst ud, og fejl der fortæller den rigtige historie.

En forkert nøgle, model eller kvote er en konfigurationsfejl og må hverken
prøves igen eller markere et uskyldigt dokument som ai_schema_error.
"""

import json
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import httpx2
import pytest
from anthropic.types import TextBlock
from fastapi.testclient import TestClient

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.provider import AIProviderRejected, AIRefusal, OpenAICompatProvider
from app.main import app
from app.routes.documents import ai_provider_dep
from tests.conftest import _upload_document


def _response(text: str, stop_reason: str = "end_turn") -> Any:
    return SimpleNamespace(
        content=[TextBlock(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class FakeMessages:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _claude(result: Any) -> tuple[AnthropicProvider, FakeMessages]:
    messages = FakeMessages(result)
    provider = AnthropicProvider(
        api_key="ikke-brugt", model_id="claude-test", client=SimpleNamespace(messages=messages)
    )
    return provider, messages


def _call(provider: Any) -> str:
    text: str = provider.complete_text(
        prompt_id="relevance_classification", prompt_version="1.0.0", system="s", user="u"
    )
    return text


def _status_error(status: int) -> anthropic.APIStatusError:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIStatusError(
        "afvist", response=httpx2.Response(status, request=request), body=None
    )


def test_claude_adapter_returns_text_and_strips_json_fence() -> None:
    provider, messages = _claude(_response('```json\n{"relevant": true, "reason": "x"}\n```'))

    assert json.loads(_call(provider)) == {"relevant": True, "reason": "x"}
    sent = messages.calls[0]
    assert sent["model"] == "claude-test"
    assert sent["system"] == "s"
    assert sent["messages"] == [{"role": "user", "content": "u"}]


@pytest.mark.parametrize("status", [401, 403, 404, 429])
def test_claude_client_errors_become_rejections(status: int) -> None:
    provider, _ = _claude(_status_error(status))
    with pytest.raises(AIProviderRejected) as rejected:
        _call(provider)
    assert rejected.value.status_code == status


def test_claude_refusal_is_its_own_error() -> None:
    provider, _ = _claude(_response("", stop_reason="refusal"))
    with pytest.raises(AIRefusal):
        _call(provider)


def test_openai_compat_401_becomes_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.ai.provider.httpx.post", fake_post)
    provider = OpenAICompatProvider(base_url="https://x.example/v1", api_key="k", model_id="m")
    with pytest.raises(AIProviderRejected) as rejected:
        _call(provider)
    assert rejected.value.status_code == 401


def test_bad_key_leaves_document_untouched_and_is_not_retried(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    document_id = _upload_document(client, admin_headers)
    provider, messages = _claude(_status_error(401))
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        response = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "ai_provider_rejected"
    assert "AI_PROVIDER_API_KEY" in error["message"]
    # Ét kald, ingen retry — og dokumentet kan køres igen, når nøglen er rettet.
    assert len(messages.calls) == 1
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["processing_status"] == "normalized"
    assert document["error_code"] is None


def test_refusal_sends_document_to_manual_follow_up(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    document_id = _upload_document(client, admin_headers)
    provider, _ = _claude(_response("", stop_reason="refusal"))
    app.dependency_overrides[ai_provider_dep] = lambda: provider
    try:
        response = client.post(
            f"/api/v1/review/documents/{document_id}/process", headers=admin_headers
        )
    finally:
        app.dependency_overrides.pop(ai_provider_dep, None)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    document = client.get(f"/api/v1/review/documents/{document_id}", headers=admin_headers).json()
    assert document["error_code"] == "ai_refused"
