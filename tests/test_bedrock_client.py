import json
import time
from io import BytesIO

import pytest

from eagle_eval import bedrock_client


def test_anthropic_payload_includes_temperature_by_default(monkeypatch):
    monkeypatch.delenv("AWS_BEDROCK_CLAUDE_NO_TEMPERATURE_MODEL_IDS", raising=False)

    payload = bedrock_client.build_anthropic_messages_payload("global.anthropic.claude-sonnet-4-5-20250929-v1:0", "Hello", max_tokens=12)

    assert payload["anthropic_version"] == "bedrock-2023-05-31"
    assert payload["max_tokens"] == 12
    assert payload["temperature"] == 0
    assert payload["messages"][0]["content"][0]["text"] == "Hello"


def test_anthropic_payload_omits_temperature_for_unsupported_models(monkeypatch):
    monkeypatch.setenv("AWS_BEDROCK_CLAUDE_NO_TEMPERATURE_MODEL_IDS", "custom-model")

    assert "temperature" not in bedrock_client.build_anthropic_messages_payload("custom-model", "Hello")
    assert "temperature" not in bedrock_client.build_anthropic_messages_payload("global.anthropic.claude-opus-4-7", "Hello")


def test_parse_anthropic_messages_response_joins_text_blocks():
    body = BytesIO(
        json.dumps(
            {
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "tool_use", "name": "ignored"},
                    {"type": "text", "text": "world"},
                ]
            }
        ).encode("utf-8")
    )

    assert bedrock_client.parse_anthropic_messages_response(body) == "Hello\nworld"


def test_generate_text_uses_env_model_and_runtime_client(monkeypatch):
    captured = {}

    class FakeClient:
        def invoke_model(self, **kwargs):
            captured.update(kwargs)
            return {"body": BytesIO(json.dumps({"content": [{"type": "text", "text": "OK"}]}).encode("utf-8"))}

    monkeypatch.setenv("AWS_BEDROCK_CLAUDE_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
    monkeypatch.setattr(bedrock_client, "_bedrock_client", lambda: FakeClient())

    assert bedrock_client.generate_text(None, "Reply OK", max_tokens=8) == "OK"
    assert captured["modelId"] == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert captured["contentType"] == "application/json"
    assert json.loads(captured["body"].decode("utf-8"))["max_tokens"] == 8


def test_int_env_falls_back_for_invalid_values(monkeypatch):
    monkeypatch.setenv("AWS_BEDROCK_READ_TIMEOUT_SECONDS", "not-a-number")

    assert bedrock_client._int_env("AWS_BEDROCK_READ_TIMEOUT_SECONDS", 120) == 120


def test_call_timeout_bounds_hanging_calls():
    with pytest.raises(TimeoutError):
        with bedrock_client._call_timeout(1):
            time.sleep(2)
