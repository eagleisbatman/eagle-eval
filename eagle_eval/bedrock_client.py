"""Amazon Bedrock Claude client helpers."""

from __future__ import annotations

import json
import os
import signal
import threading
from contextlib import contextmanager
from typing import Any

ANTHROPIC_VERSION = "bedrock-2023-05-31"


def generate_text(model: str | None, prompt: str, max_tokens: int = 4096) -> str:
    """Generate text with Anthropic Claude through Amazon Bedrock."""
    model_id = _resolve_model(model)
    payload = build_anthropic_messages_payload(model_id, prompt, max_tokens=max_tokens)
    with _call_timeout(_int_env("AWS_BEDROCK_CALL_TIMEOUT_SECONDS", 180)):
        client = _bedrock_client()
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
    return parse_anthropic_messages_response(response["body"])


def build_anthropic_messages_payload(model_id: str, prompt: str, max_tokens: int = 4096) -> dict:
    payload = {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }
    if _supports_temperature(model_id):
        payload["temperature"] = 0
    return payload


def parse_anthropic_messages_response(body: Any) -> str:
    raw = body.read() if hasattr(body, "read") else body
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    payload = json.loads(raw)
    parts = []
    for item in payload.get("content", []):
        if item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts)


def _bedrock_client():
    import boto3
    from botocore.config import Config

    profile = os.environ.get("AWS_PROFILE") or None
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or None
    config = Config(
        connect_timeout=_int_env("AWS_BEDROCK_CONNECT_TIMEOUT_SECONDS", 10),
        read_timeout=_int_env("AWS_BEDROCK_READ_TIMEOUT_SECONDS", 120),
        retries={"max_attempts": _int_env("AWS_BEDROCK_MAX_ATTEMPTS", 3), "mode": "standard"},
    )
    return boto3.Session(profile_name=profile, region_name=region).client("bedrock-runtime", config=config)


def _resolve_model(model: str | None) -> str:
    resolved = (model or os.environ.get("AWS_BEDROCK_CLAUDE_MODEL_ID") or "").strip()
    if not resolved:
        raise RuntimeError("Bedrock requires a model id or AWS_BEDROCK_CLAUDE_MODEL_ID")
    return resolved


def _supports_temperature(model_id: str) -> bool:
    no_temperature = {
        item.strip()
        for item in os.environ.get("AWS_BEDROCK_CLAUDE_NO_TEMPERATURE_MODEL_IDS", "").split(",")
        if item.strip()
    }
    no_temperature.update({"us.anthropic.claude-opus-4-7", "global.anthropic.claude-opus-4-7"})
    return model_id not in no_temperature


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@contextmanager
def _call_timeout(seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM") or threading.current_thread() is not threading.main_thread():
        yield
        return

    def raise_timeout(signum, frame):
        raise TimeoutError(f"Bedrock call exceeded {seconds} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
