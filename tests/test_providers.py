from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mda_cli.providers import (
    OpenRouterAPIError,
    OpenRouterClient,
    anthropic_api_key_set,
    anthropic_error_warrants_fallback,
    build_restructure_client,
    openrouter_api_key_set,
    openrouter_fallback_enabled,
    resolve_model,
    resolve_provider_name,
)


def test_resolve_provider_cli_override() -> None:
    assert resolve_provider_name(cli_provider="openrouter") == "openrouter"
    assert resolve_provider_name(cli_provider="anthropic") == "anthropic"


def test_resolve_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("MDA_PROVIDER", "openrouter")
    assert resolve_provider_name() == "openrouter"


def test_resolve_provider_prefers_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("MDA_PROVIDER", raising=False)
    assert resolve_provider_name() == "anthropic"


def test_resolve_provider_openrouter_when_only_or_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    assert resolve_provider_name() == "openrouter"


def test_resolve_model_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MDA_OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    assert resolve_model("openrouter", None) == "anthropic/claude-3.5-sonnet"
    monkeypatch.setenv("MDA_MODEL", "claude-test")
    assert resolve_model("anthropic", None) == "claude-test"


def test_openrouter_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")

    payload = {
        "choices": [{"message": {"content": "# Done\n\nBody\n"}}],
    }

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(payload).encode()

    with patch("urllib.request.urlopen", return_value=FakeResp()):
        out = OpenRouterClient().restructure(
            model="anthropic/claude-sonnet-4",
            max_tokens=100,
            system="sys",
            content="user",
            progress=False,
            max_attempts=1,
        )
    assert "Done" in out


def test_openrouter_client_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")

    err = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=None,
    )
    err.read = MagicMock(return_value=b'{"error":"bad key"}')  # type: ignore[method-assign]

    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="OpenRouter"):
            OpenRouterClient().restructure(
                model="anthropic/claude-sonnet-4",
                max_tokens=100,
                system="sys",
                content="user",
                progress=False,
                max_attempts=1,
            )


def test_build_restructure_client_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MDA_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    client, ctx = build_restructure_client(cli_provider=None)
    assert ctx.provider == "openrouter"
    assert client.provider == "openrouter"


def test_anthropic_fallback_flag_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MDA_OPENROUTER_FALLBACK", raising=False)
    assert openrouter_fallback_enabled() is True


def test_api_key_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert anthropic_api_key_set() is True
    assert openrouter_api_key_set() is False


def test_openrouter_error_user_message() -> None:
    err = OpenRouterAPIError("x", status_code=402)
    assert "402" in err.user_message()


def test_anthropic_error_warrants_fallback_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import RateLimitError

    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.delenv("MDA_OPENROUTER_FALLBACK", raising=False)
    exc = RateLimitError(
        message="rate",
        response=MagicMock(status_code=429),
        body=None,
    )
    assert anthropic_error_warrants_fallback(exc) is True
