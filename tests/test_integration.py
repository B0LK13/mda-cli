"""Opt-in live API tests (``pytest -m integration``)."""

from __future__ import annotations

import os

import pytest


@pytest.mark.integration
def test_anthropic_messages_smoke() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    from anthropic import APIStatusError

    from mda_cli.core import build_anthropic_client

    client = build_anthropic_client()
    model = os.environ.get("MDA_INTEGRATION_MODEL", "claude-3-5-haiku-20241022")
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=32,
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
        )
    except APIStatusError as e:
        body = str(getattr(e, "body", "") or e).lower()
        if "credit balance" in body or getattr(e, "status_code", None) in (402, 403):
            pytest.skip("Anthropic API credits unavailable for integration test")
        raise
    parts: list[str] = []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    assert parts
    assert "ok" in "".join(parts).lower()
