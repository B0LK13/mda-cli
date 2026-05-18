from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mda_cli.providers import (
    AnthropicClient,
    OpenRouterAPIError,
    OpenRouterClient,
    RestructureOutcome,
    anthropic_api_key_set,
    anthropic_error_warrants_fallback,
    anthropic_failure_user_message,
    anthropic_fallback_reason,
    build_restructure_client,
    openrouter_api_key_set,
    openrouter_fallback_enabled,
    provider_check_lines,
    restructure_with_provider,
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


def test_anthropic_error_warrants_fallback_400_billing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    exc = APIStatusError(
        message="credit",
        response=MagicMock(status_code=400),
        body={"error": {"message": "Your credit balance is too low"}},
    )
    wrapped = RuntimeError("fail")
    wrapped.__cause__ = exc
    assert anthropic_error_warrants_fallback(wrapped) is True


def test_anthropic_400_falls_back_to_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.delenv("MDA_OPENROUTER_FALLBACK", raising=False)

    api_exc = APIStatusError(
        message="credit balance too low",
        response=MagicMock(status_code=400),
        body={"error": {"message": "Your credit balance is too low"}},
    )
    runtime_err = RuntimeError("Anthropic billing/credits error (400).")
    runtime_err.__cause__ = api_exc

    client, ctx = build_restructure_client()
    assert ctx.allow_fallback is True

    with patch.object(AnthropicClient, "restructure", side_effect=runtime_err):
        with patch.object(
            OpenRouterClient,
            "restructure",
            return_value="# OK\n\nbody",
        ) as or_mock:
            outcome = restructure_with_provider(
                client,
                ctx,
                max_tokens=100,
                system="sys",
                content="doc",
                progress=False,
                max_attempts=1,
            )

    assert isinstance(outcome, RestructureOutcome)
    assert outcome.used_openrouter_fallback is True
    assert outcome.provider_used == "openrouter"
    assert "OK" in outcome.text
    or_mock.assert_called_once()


def test_anthropic_400_no_openrouter_key_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    api_exc = APIStatusError(
        message="credit balance too low",
        response=MagicMock(status_code=400),
        body={"error": {"message": "Your credit balance is too low"}},
    )
    runtime_err = RuntimeError("Anthropic billing/credits error (400).")
    runtime_err.__cause__ = api_exc

    client, ctx = build_restructure_client()
    assert ctx.allow_fallback is False

    with patch.object(AnthropicClient, "restructure", side_effect=runtime_err):
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            restructure_with_provider(
                client,
                ctx,
                max_tokens=100,
                system="sys",
                content="doc",
                progress=False,
                max_attempts=1,
            )


def test_anthropic_fallback_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.setenv("MDA_OPENROUTER_FALLBACK", "0")

    api_exc = APIStatusError(
        message="credit",
        response=MagicMock(status_code=402),
        body=None,
    )
    runtime_err = RuntimeError("fail")
    runtime_err.__cause__ = api_exc

    client, ctx = build_restructure_client()
    assert ctx.allow_fallback is False

    with patch.object(AnthropicClient, "restructure", side_effect=runtime_err):
        with pytest.raises(RuntimeError, match="MDA_OPENROUTER_FALLBACK=0"):
            restructure_with_provider(
                client,
                ctx,
                max_tokens=100,
                system="sys",
                content="doc",
                progress=False,
                max_attempts=1,
            )


def test_provider_check_lines_fallback_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    lines = provider_check_lines()
    assert any("fallback: ready" in line for line in lines)


def test_anthropic_error_warrants_fallback_runtime_message_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    runtime_err = RuntimeError(
        "Anthropic billing/credits error (400). Add credits at console.anthropic.com, "
        "or set OPENROUTER_API_KEY for automatic fallback."
    )
    assert anthropic_error_warrants_fallback(runtime_err) is True
    assert anthropic_fallback_reason(runtime_err) == "billing"


def test_anthropic_fallback_notifies_and_combines_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")
    monkeypatch.delenv("MDA_OPENROUTER_FALLBACK", raising=False)

    api_exc = APIStatusError(
        message="credit balance too low",
        response=MagicMock(status_code=400),
        body={"error": {"message": "Your credit balance is too low"}},
    )
    runtime_err = RuntimeError("Anthropic billing/credits error (400).")
    runtime_err.__cause__ = api_exc

    client, ctx = build_restructure_client()
    notices: list[str] = []

    with patch.object(AnthropicClient, "restructure", side_effect=runtime_err):
        with patch.object(
            OpenRouterClient,
            "restructure",
            side_effect=RuntimeError("OpenRouter: Insufficient credits (402)."),
        ):
            with pytest.raises(RuntimeError, match="OpenRouter retry failed") as raised:
                restructure_with_provider(
                    client,
                    ctx,
                    max_tokens=100,
                    system="sys",
                    content="doc",
                    progress=False,
                    notify=notices.append,
                    max_attempts=1,
                )

    assert any("retrying via OpenRouter" in n for n in notices)
    assert "billing" in notices[0].lower()
    assert "Anthropic billing/credits error" in str(raised.value)
    assert "OpenRouter" in str(raised.value)


def test_process_job_with_provider_logs_fallback_notify(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or")

    src = tmp_path / "note.md"
    src.write_text("# Hi\n", encoding="utf-8")
    from mda_cli.core import Job

    job = Job(src=src, dst=tmp_path / "note.restructured.md")
    api_exc = APIStatusError(
        message="credit",
        response=MagicMock(status_code=400),
        body={"error": {"message": "Your credit balance is too low"}},
    )
    runtime_err = RuntimeError("Anthropic billing/credits error (400).")
    runtime_err.__cause__ = api_exc

    client, ctx = build_restructure_client()
    logs: list[str] = []

    with patch.object(AnthropicClient, "restructure", side_effect=runtime_err):
        with patch.object(
            OpenRouterClient,
            "restructure",
            return_value="# OK\n\nbody",
        ):
            from mda_cli.providers import process_job_with_provider

            result = process_job_with_provider(
                job,
                client,
                ctx,
                max_tokens=100,
                system="sys",
                progress=False,
                log=logs.append,
                max_attempts=1,
            )

    assert result.ok is True
    assert result.used_openrouter_fallback is True
    assert any("retrying via OpenRouter" in line for line in logs)


def test_anthropic_failure_user_message_suggests_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("anthropic")
    from anthropic import APIStatusError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    exc = APIStatusError(
        message="credit",
        response=MagicMock(status_code=400),
        body={"error": {"message": "insufficient credits"}},
    )
    wrapped = RuntimeError("x")
    wrapped.__cause__ = exc
    msg = anthropic_failure_user_message(wrapped)
    assert "OPENROUTER_API_KEY" in msg
