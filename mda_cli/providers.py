"""LLM provider selection: Anthropic (primary) and OpenRouter (fallback / alternate)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from mda_cli.core import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    friendly_api_message as _friendly_anthropic,
    strip_outer_fence,
)

ProviderName = Literal["anthropic", "openrouter"]

DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# HTTP status codes that trigger OpenRouter fallback when MDA_OPENROUTER_FALLBACK is on.
_FALLBACK_STATUS_CODES = frozenset({402, 403, 429, 500, 502, 503, 504, 529})


def _truthy_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def anthropic_api_key_set() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def openrouter_api_key_set() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def openrouter_fallback_enabled() -> bool:
    return _truthy_env("MDA_OPENROUTER_FALLBACK", default=True)


def resolve_provider_name(*, cli_provider: str | None = None) -> ProviderName:
    """Pick the primary provider for this run (before automatic fallback)."""
    if cli_provider:
        p = cli_provider.strip().lower()
        if p not in ("anthropic", "openrouter"):
            sys.exit(f"ERROR: unknown provider {cli_provider!r} (use anthropic or openrouter).")
        return p  # type: ignore[return-value]

    env_provider = os.environ.get("MDA_PROVIDER", "").strip().lower()
    if env_provider in ("anthropic", "openrouter"):
        return env_provider  # type: ignore[return-value]

    if _truthy_env("MDA_USE_OPENROUTER"):
        return "openrouter"

    if anthropic_api_key_set():
        return "anthropic"
    if openrouter_api_key_set():
        return "openrouter"
    return "anthropic"


def resolve_model(provider: ProviderName, cli_model: str | None) -> str:
    if cli_model:
        return cli_model
    if provider == "openrouter":
        return os.environ.get("MDA_OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip() or (
            DEFAULT_OPENROUTER_MODEL
        )
    return os.environ.get("MDA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def ensure_api_credentials(provider: ProviderName) -> None:
    if provider == "openrouter":
        if not openrouter_api_key_set():
            sys.exit("ERROR: OPENROUTER_API_KEY environment variable not set.")
        return
    if not anthropic_api_key_set():
        if openrouter_api_key_set():
            sys.exit(
                "ERROR: ANTHROPIC_API_KEY not set. "
                "Set it, or use --provider openrouter / MDA_PROVIDER=openrouter."
            )
        sys.exit("ERROR: ANTHROPIC_API_KEY environment variable not set.")


def provider_check_lines(*, cli_provider: str | None = None) -> list[str]:
    """Human-readable lines for ``mda --check`` (no secrets)."""
    primary = resolve_provider_name(cli_provider=cli_provider)
    lines = [
        f"ANTHROPIC_API_KEY set: {'yes' if anthropic_api_key_set() else 'no'}",
        f"OPENROUTER_API_KEY set: {'yes' if openrouter_api_key_set() else 'no'}",
        f"Default provider (this run): {primary}",
        f"MDA_OPENROUTER_FALLBACK: {'on' if openrouter_fallback_enabled() else 'off'}",
    ]
    if primary == "openrouter":
        model = resolve_model("openrouter", None)
        lines.append(f"OpenRouter model: {model}")
    else:
        lines.append(f"Anthropic model (MDA_MODEL): {resolve_model('anthropic', None)}")
    return lines


def anthropic_error_warrants_fallback(exc: BaseException) -> bool:
    if not openrouter_fallback_enabled() or not openrouter_api_key_set():
        return False
    try:
        from anthropic import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:
        return False

    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return True
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return False
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", None) or 0
        return int(code) in _FALLBACK_STATUS_CODES
    if isinstance(exc, RuntimeError) and exc.__cause__ is not None:
        return anthropic_error_warrants_fallback(exc.__cause__)
    return False


def friendly_api_message(exc: BaseException, *, provider: ProviderName | None = None) -> str:
    """Actionable API error text; names the provider when known."""
    prefix = ""
    if provider == "openrouter":
        prefix = "OpenRouter: "
    elif provider == "anthropic":
        prefix = "Anthropic: "

    if provider == "openrouter" or isinstance(exc, OpenRouterAPIError):
        if isinstance(exc, OpenRouterAPIError):
            return prefix + exc.user_message()
        return prefix + str(exc)

    try:
        from anthropic import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:
        return prefix + str(exc)

    if isinstance(
        exc,
        (
            AuthenticationError,
            PermissionDeniedError,
            RateLimitError,
            APIConnectionError,
            APITimeoutError,
            APIStatusError,
        ),
    ):
        return prefix + _friendly_anthropic(exc)
    return prefix + str(exc)


class OpenRouterAPIError(Exception):
    """OpenRouter HTTP/API failure (no secrets in messages)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    def user_message(self) -> str:
        code = self.status_code
        base = str(self)
        if code == 401:
            return "API authentication failed (401). Check OPENROUTER_API_KEY."
        if code == 402:
            return "Insufficient credits (402). Add credits or change MDA_OPENROUTER_MODEL."
        if code == 403:
            return "API permission denied (403). Check OPENROUTER_API_KEY and model access."
        if code == 429:
            return "API rate limit (429). Wait and retry."
        if code == 529:
            return "Provider overloaded (529). Retry later or enable fallback."
        if code is not None and code >= 500:
            return f"API server error ({code}). Retry later."
        return base


class RestructureClient(Protocol):
    provider: ProviderName

    def restructure(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        content: str,
        progress: bool,
        progress_writer: Callable[[str], None] | None = None,
        max_attempts: int = 3,
    ) -> str: ...


@dataclass
class _RunContext:
    provider: ProviderName
    model: str
    max_tokens: int
    allow_fallback: bool


def build_restructure_client(
    *,
    cli_provider: str | None = None,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    allow_fallback: bool | None = None,
) -> tuple[RestructureClient, _RunContext]:
    """Return client + context for ``restructure`` calls."""
    provider = resolve_provider_name(cli_provider=cli_provider)
    resolved_model = resolve_model(provider, model)
    fb = openrouter_fallback_enabled() if allow_fallback is None else allow_fallback
    ctx = _RunContext(
        provider=provider,
        model=resolved_model,
        max_tokens=max_tokens,
        allow_fallback=fb and provider == "anthropic" and openrouter_api_key_set(),
    )
    if provider == "openrouter":
        return OpenRouterClient(), ctx
    return AnthropicClient(), ctx


class AnthropicClient:
    provider: ProviderName = "anthropic"

    def __init__(self) -> None:
        from mda_cli.core import build_anthropic_client

        self._client = build_anthropic_client()

    def restructure(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        content: str,
        progress: bool,
        progress_writer: Callable[[str], None] | None = None,
        max_attempts: int = 3,
    ) -> str:
        from mda_cli.core import restructure as anthropic_restructure

        return anthropic_restructure(
            self._client,
            model=model,
            max_tokens=max_tokens,
            system=system,
            content=content,
            progress=progress,
            progress_writer=progress_writer,
            max_attempts=max_attempts,
        )


class OpenRouterClient:
    provider: ProviderName = "openrouter"

    def restructure(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        content: str,
        progress: bool,
        progress_writer: Callable[[str], None] | None = None,
        max_attempts: int = 3,
    ) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise OpenRouterAPIError("OPENROUTER_API_KEY is not set.")

        raw_timeout = os.environ.get("MDA_API_TIMEOUT", "").strip()
        timeout = float(raw_timeout) if raw_timeout else DEFAULT_API_TIMEOUT

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mda-cli",
            "X-Title": "mda-cli",
        }

        last_exc: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                req = urllib.request.Request(
                    OPENROUTER_CHAT_URL,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices") or []
                if not choices:
                    raise OpenRouterAPIError("OpenRouter returned no choices.")
                message = choices[0].get("message") or {}
                text = message.get("content") or ""
                if progress and progress_writer is not None:
                    progress_writer("\n")
                elif progress:
                    sys.stderr.write("\n")
                return str(text)
            except urllib.error.HTTPError as e:
                code = e.code
                detail = ""
                try:
                    err_body = json.loads(e.read().decode("utf-8"))
                    detail = str(err_body.get("error", err_body))
                except Exception:
                    detail = e.reason or ""
                last_exc = OpenRouterAPIError(
                    detail or f"HTTP {code}",
                    status_code=code,
                )
                if code not in _FALLBACK_STATUS_CODES or attempt >= max_attempts - 1:
                    raise RuntimeError(
                        friendly_api_message(last_exc, provider="openrouter")
                    ) from last_exc
                time.sleep(min(60.0, 2.0**attempt))
            except urllib.error.URLError as e:
                last_exc = OpenRouterAPIError(f"Network error: {e.reason}")
                if attempt >= max_attempts - 1:
                    raise RuntimeError(
                        friendly_api_message(last_exc, provider="openrouter")
                    ) from last_exc
                time.sleep(min(60.0, 2.0**attempt))
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    friendly_api_message(
                        OpenRouterAPIError("Invalid JSON from OpenRouter."),
                        provider="openrouter",
                    )
                ) from e

        assert last_exc is not None
        raise RuntimeError(friendly_api_message(last_exc, provider="openrouter")) from last_exc


def restructure_with_provider(
    client: RestructureClient,
    ctx: _RunContext,
    *,
    max_tokens: int,
    system: str,
    content: str,
    progress: bool,
    progress_writer: Callable[[str], None] | None = None,
    max_attempts: int = 3,
) -> str:
    """Call primary provider; optionally fall back to OpenRouter on Anthropic failures."""
    try:
        return client.restructure(
            model=ctx.model,
            max_tokens=max_tokens,
            system=system,
            content=content,
            progress=progress,
            progress_writer=progress_writer,
            max_attempts=max_attempts,
        )
    except RuntimeError as e:
        if not ctx.allow_fallback or not anthropic_error_warrants_fallback(e):
            raise
        fb_model = resolve_model("openrouter", None)
        fb_client = OpenRouterClient()
        if progress_writer is not None:
            progress_writer(
                f"\n[fallback] Anthropic failed; retrying via OpenRouter ({fb_model})…\n"
            )
        elif progress:
            sys.stderr.write(
                f"\n[fallback] Anthropic failed; retrying via OpenRouter ({fb_model})…\n"
            )
        return fb_client.restructure(
            model=fb_model,
            max_tokens=max_tokens,
            system=system,
            content=content,
            progress=progress,
            progress_writer=progress_writer,
            max_attempts=max_attempts,
        )


def process_job_with_provider(
    job,
    client: RestructureClient,
    ctx: _RunContext,
    *,
    max_tokens: int,
    system: str,
    progress: bool,
    log: Callable[[str], None] | None = None,
    progress_writer: Callable[[str], None] | None = None,
    max_attempts: int = 3,
    backup_in_place: bool = False,
):
    """Same contract as ``core.process_job`` but provider-aware."""
    from mda_cli.core import JobResult, read_markdown_text, write_output_text

    def _emit(msg: str) -> None:
        if log is not None:
            log(msg)
        else:
            print(msg, file=sys.stderr)

    _emit(f"-> {job.src}")
    raw = read_markdown_text(job.src)
    bytes_in = len(raw.encode("utf-8"))
    if not raw.strip():
        _emit(f"   skip (empty): {job.src}")
        return JobResult(
            job=job,
            ok=True,
            action="skipped-empty",
            changed=False,
            bytes_in=bytes_in,
        )

    try:
        output = restructure_with_provider(
            client,
            ctx,
            max_tokens=max_tokens,
            system=system,
            content=raw,
            progress=progress,
            progress_writer=progress_writer,
            max_attempts=max_attempts,
        )
    except RuntimeError as e:
        _emit(f"   FAILED: {e}")
        return JobResult(
            job=job,
            ok=False,
            action="failed",
            error=str(e),
            bytes_in=bytes_in,
        )

    stripped = output.strip()
    if stripped.startswith("ERROR:"):
        _emit(f"   {stripped}")
        return JobResult(
            job=job,
            ok=False,
            action="failed",
            error=stripped,
            bytes_in=bytes_in,
        )

    output = strip_outer_fence(output)
    try:
        changed, backup_path, bytes_out = write_output_text(
            job.dst,
            output,
            create_backup=backup_in_place and job.src.resolve() == job.dst.resolve(),
        )
    except OSError as e:
        msg = f"write failed: {e}"
        _emit(f"   FAILED: {msg}")
        return JobResult(
            job=job,
            ok=False,
            action="failed",
            error=msg,
            bytes_in=bytes_in,
        )

    if changed:
        extra = f" (backup {backup_path})" if backup_path is not None else ""
        _emit(f"   wrote {job.dst}{extra}")
        action = "wrote"
    else:
        _emit(f"   unchanged {job.dst}")
        action = "unchanged"

    return JobResult(
        job=job,
        ok=True,
        action=action,
        changed=changed,
        backup_path=backup_path,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
    )
