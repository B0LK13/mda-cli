"""Core MDA transform logic (Anthropic Messages API)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.resources import files as importlib_files
from pathlib import Path
from typing import Literal

from mda_cli.document_io import (
    DocumentReadError,
    count_supported_files_in_dir,
    is_restructured_output_name,
    is_supported_extension,
    read_document_text,
    read_markdown_text,
    restructured_output_path,
    supported_extensions,
)

try:
    from anthropic import (
        Anthropic,
        APIConnectionError,
        APIStatusError,
        APITimeoutError,
        AuthenticationError,
        PermissionDeniedError,
        RateLimitError,
    )
except ImportError:
    sys.stderr.write(
        "ERROR: 'anthropic' package not installed. Run: pip install anthropic\n"
    )
    raise SystemExit(2) from None


DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 16_000
DEFAULT_API_TIMEOUT = 600.0
LARGE_FILE_BYTES = 400_000
LARGE_BATCH_TOTAL_BYTES = 2_000_000

_system_prompt_cache: dict[tuple[str, float | None, float | None], str] = {}


def clear_system_prompt_cache() -> None:
    """Clear the in-process system prompt cache (for tests)."""
    _system_prompt_cache.clear()


def count_markdown_in_dir(directory: Path, *, include_restructured: bool = False) -> int:
    """Count ``.md`` files directly in ``directory`` (not recursive)."""
    return count_supported_files_in_dir(
        directory,
        include_restructured=include_restructured,
        extensions=(".md",),
    )


def _system_prompt_cache_key(skill_dir: Path) -> tuple[str, float | None, float | None]:
    sd = skill_dir.resolve()
    skill_file = sd / "SKILL.md"
    standard_file = sd / "MDA-STANDARD.md"
    m_skill = skill_file.stat().st_mtime if skill_file.exists() else None
    m_std = standard_file.stat().st_mtime if standard_file.exists() else None
    return (str(sd), m_skill, m_std)


def anthropic_error_body_text(exc: APIStatusError) -> str:
    """Best-effort string from an Anthropic APIStatusError body (no secrets)."""
    body = getattr(exc, "body", None)
    if body is None:
        return ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            if isinstance(msg, str):
                return msg
        return str(body)
    return str(body)


def anthropic_error_is_billing_related(exc: APIStatusError) -> bool:
    text = anthropic_error_body_text(exc).lower()
    if not text:
        text = str(getattr(exc, "message", exc)).lower()
    return any(
        token in text
        for token in (
            "credit balance",
            "credit balance is too low",
            "insufficient",
            "billing",
            "purchase credits",
            "add credits",
            "payment",
            "too low to access",
        )
    )


def friendly_api_message(exc: BaseException) -> str:
    """Short, actionable message for common API failures (no secrets)."""
    if isinstance(exc, AuthenticationError):
        return (
            "Anthropic authentication failed (401). Check ANTHROPIC_API_KEY, "
            "or set OPENROUTER_API_KEY for automatic fallback."
        )
    if isinstance(exc, PermissionDeniedError):
        return (
            "Anthropic permission denied (403). Check your API key and account access, "
            "or set OPENROUTER_API_KEY for automatic fallback."
        )
    if isinstance(exc, RateLimitError):
        return "Anthropic rate limit (429). Wait and retry, or reduce request volume."
    if isinstance(exc, APITimeoutError):
        return (
            "Request timed out. Retry later or raise MDA_API_TIMEOUT (seconds), "
            "e.g. MDA_API_TIMEOUT=900."
        )
    if isinstance(exc, APIConnectionError):
        return "Network error talking to Anthropic. Check your connection and DNS."
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", None)
        if code == 401:
            return (
                "Anthropic authentication failed (401). Check ANTHROPIC_API_KEY, "
                "or set OPENROUTER_API_KEY for automatic fallback."
            )
        if code == 402:
            return (
                "Anthropic insufficient credits (402). Add credits at console.anthropic.com, "
                "or set OPENROUTER_API_KEY for automatic fallback."
            )
        if code == 429:
            return "Anthropic rate limit (429). Wait and retry."
        if code == 400 and anthropic_error_is_billing_related(exc):
            return (
                "Anthropic billing/credits error (400). Add credits at console.anthropic.com, "
                "or set OPENROUTER_API_KEY for automatic fallback."
            )
        body = anthropic_error_body_text(exc) or getattr(exc, "body", None)
        if code is not None:
            return f"Anthropic API error ({code}). {body or type(exc).__name__}"
        return str(exc)
    return str(exc)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    if isinstance(exc, APIStatusError):
        code = getattr(exc, "status_code", 0) or 0
        return code in (408, 429, 500, 502, 503, 504)
    return False


def build_anthropic_client(
    *,
    timeout: float | None = None,
    max_retries: int = 0,
) -> Anthropic:
    """Anthropic client with explicit timeout; streaming retries are handled in ``restructure``."""
    if timeout is None:
        raw = os.environ.get("MDA_API_TIMEOUT", "").strip()
        timeout = float(raw) if raw else DEFAULT_API_TIMEOUT
    return Anthropic(timeout=timeout, max_retries=max_retries)


DEFAULT_SKILL_ID = "markdown-document-architect"

SkillSource = Literal["explicit", "env", "claude", "cursor", "bundled"]


def normalize_skill_id(raw: str | None) -> str:
    """Return a non-empty skill id (default MDA restructure skill)."""
    if raw is None:
        return DEFAULT_SKILL_ID
    cleaned = raw.strip()
    return cleaned if cleaned else DEFAULT_SKILL_ID


def resolve_skill_id(*, cli_skill: str | None = None) -> str:
    """Skill id from CLI ``--skill``, then ``MDA_SKILL``, else default."""
    if cli_skill is not None and cli_skill.strip():
        return normalize_skill_id(cli_skill)
    env_skill = os.environ.get("MDA_SKILL", "").strip()
    if env_skill:
        return normalize_skill_id(env_skill)
    return DEFAULT_SKILL_ID


@dataclass(frozen=True)
class SkillResolution:
    path: Path
    source: SkillSource
    skill_id: str = DEFAULT_SKILL_ID


@dataclass
class Job:
    src: Path
    dst: Path


@dataclass
class JobResult:
    job: Job
    ok: bool
    action: Literal["wrote", "unchanged", "skipped-empty", "failed"]
    error: str | None = None
    changed: bool = False
    backup_path: Path | None = None
    bytes_in: int = 0
    bytes_out: int = 0
    provider_used: str | None = None
    used_openrouter_fallback: bool = False


def warn_large_inputs(
    jobs: list[Job],
    *,
    max_tokens: int | None = None,
    writer: Callable[[str], None] | None = None,
) -> None:
    """Warn when inputs may stress context limits (heuristic by file size)."""
    emit = writer or (lambda m: sys.stderr.write(m + "\n"))
    total = 0
    for job in jobs:
        try:
            st = job.src.stat()
        except OSError:
            continue
        total += st.st_size
        if st.st_size >= LARGE_FILE_BYTES:
            emit(
                f"WARNING: large source file {job.src.name} "
                f"({st.st_size // 1024} KiB); consider splitting before MDA."
            )
    if total >= LARGE_BATCH_TOTAL_BYTES:
        emit(
            f"WARNING: batch input is large (~{total // 1024} KiB total); "
            "watch for context or rate limits."
        )
    if max_tokens is not None and max_tokens > 0 and jobs:
        # Rough input token estimate (~4 chars/token); output capped per file by max_tokens.
        est_input_tokens = max(1, total // 4)
        est_output_tokens = max_tokens * len(jobs)
        est_total = est_input_tokens + est_output_tokens
        per_file_budget = max_tokens
        if est_input_tokens > per_file_budget * len(jobs):
            emit(
                f"WARNING: estimated input tokens (~{est_input_tokens:,}) may exceed "
                f"--max-tokens ({per_file_budget:,}) per file for {len(jobs)} job(s); "
                "reduce batch size or raise --max-tokens."
            )
        if est_total > 200_000:
            emit(
                f"WARNING: rough token budget ~{est_total:,} "
                f"(input ~{est_input_tokens:,} + output up to {est_output_tokens:,}); "
                "use --max-files, --max-tokens, or a dry-run first."
            )


def bundled_skills_root() -> Path:
    """Root directory for packaged skills inside ``mda_cli``."""
    return Path(importlib_files("mda_cli")).joinpath("bundled_skills")


def list_bundled_skills() -> list[str]:
    """Skill ids shipped in ``mda_cli/bundled_skills/`` (sorted)."""
    root = bundled_skills_root()
    if not root.is_dir():
        legacy = Path(importlib_files("mda_cli")).joinpath("bundled_skill")
        if (legacy / "SKILL.md").is_file():
            return [DEFAULT_SKILL_ID]
        return []
    ids = [
        p.name
        for p in root.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    ]
    return sorted(ids)


def bundled_skill_dir(skill_id: str | None = None) -> Path:
    """Shipped skill directory for ``skill_id`` (wheel/sdist)."""
    sid = normalize_skill_id(skill_id)
    root = bundled_skills_root()
    candidate = root / sid
    if (candidate / "SKILL.md").is_file():
        return candidate
    legacy = Path(importlib_files("mda_cli")).joinpath("bundled_skill")
    if sid == DEFAULT_SKILL_ID and (legacy / "SKILL.md").is_file():
        return legacy
    return candidate


def find_skill_dir(
    explicit: Path | None,
    *,
    skill_id: str | None = None,
) -> tuple[SkillResolution | None, str | None]:
    """Return ``(resolution, None)`` or ``(None, error_message)`` (no process exit)."""
    sid = resolve_skill_id(cli_skill=skill_id)

    if explicit is not None:
        p = explicit.expanduser().resolve()
        if not (p / "SKILL.md").exists():
            return None, f"ERROR: SKILL.md not found in {p}"
        return SkillResolution(p, "explicit", sid), None

    env = os.environ.get("MDA_SKILL_DIR", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if not (p / "SKILL.md").exists():
            return None, f"ERROR: MDA_SKILL_DIR is set but SKILL.md missing: {p}"
        return SkillResolution(p, "env", sid), None

    home = Path.home()
    external: list[tuple[Path, SkillSource]] = [
        (home / ".claude" / "skills" / sid, "claude"),
        (home / ".cursor" / "skills" / sid, "cursor"),
    ]
    for c, source in external:
        if (c / "SKILL.md").exists():
            return SkillResolution(c.resolve(), source, sid), None

    bundled = bundled_skill_dir(sid)
    if (bundled / "SKILL.md").exists():
        return SkillResolution(bundled.resolve(), "bundled", sid), None

    bundled_ids = list_bundled_skills()
    tried = [str(c) for c, _ in external] + [str(bundled)]
    hint = (
        f"Bundled skills: {', '.join(bundled_ids) or '(none)'}.\n"
        if bundled_ids
        else ""
    )
    return None, (
        "ERROR: Could not find skill directory (needs SKILL.md).\n"
        f"Skill id: {sid}\n"
        f"{hint}"
        "Set MDA_SKILL_DIR, pass --skill-dir, install under ~/.claude/skills/, "
        "or use --skill with a bundled id.\n"
        f"Tried: {', '.join(tried)}"
    )


def resolve_skill_dir(
    explicit: Path | None,
    *,
    skill_id: str | None = None,
) -> SkillResolution:
    """Find the folder containing SKILL.md (and optional companion docs)."""
    res, err = find_skill_dir(explicit, skill_id=skill_id)
    if err:
        sys.exit(err)
    assert res is not None
    return res


def list_skill_scripts(skill_dir: Path) -> list[str]:
    """Basenames of ``*.py`` files in ``skill_dir/scripts/``."""
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return []
    return sorted(p.name for p in scripts.glob("*.py") if p.is_file())


def resolve_skill_script(skill_dir: Path, name: str) -> Path | None:
    """Resolve ``name`` or ``name.py`` under ``skill_dir/scripts/``."""
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return None
    stem = name.removesuffix(".py")
    for candidate in (scripts / name, scripts / f"{stem}.py"):
        if candidate.is_file():
            return candidate.resolve()
    return None


def load_system_prompt(skill_dir: Path) -> str:
    key = _system_prompt_cache_key(skill_dir)
    hit = _system_prompt_cache.get(key)
    if hit is not None:
        return hit

    skill_file = skill_dir / "SKILL.md"
    standard_file = skill_dir / "MDA-STANDARD.md"
    if not skill_file.exists():
        sys.exit(f"ERROR: skill file not found: {skill_file}")
    parts: list[str] = [read_markdown_text(skill_file)]
    if standard_file.exists():
        parts.append(
            "\n\n---\n\n"
            "## Bundled governing standard (read and apply)\n\n"
            "The following is `MDA-STANDARD.md` from this skill directory.\n\n"
        )
        parts.append(read_markdown_text(standard_file))
    else:
        categories = skill_dir / "references" / "CATEGORIES.md"
        if categories.exists():
            parts.append(
                "\n\n---\n\n"
                "## Reference taxonomy (read and apply)\n\n"
                "The following is `references/CATEGORIES.md` from this skill directory.\n\n"
            )
            parts.append(read_markdown_text(categories))
        else:
            sys.stderr.write(
                f"WARNING: no MDA-STANDARD.md or references/CATEGORIES.md; "
                f"system prompt is SKILL.md only.\n"
            )
    result = "".join(parts)
    _system_prompt_cache[key] = result
    return result


def _iter_supported_files(target: Path, *, recursive: bool) -> list[Path]:
    exts = supported_extensions()
    if target.is_file():
        if not is_supported_extension(target):
            sys.exit(
                f"ERROR: unsupported file type {target.suffix!r}. "
                f"Supported: {', '.join(exts)}"
            )
        return [target]
    if not target.is_dir():
        sys.exit(f"ERROR: not a file or directory: {target}")

    files: list[Path] = []
    if recursive:
        for ext in exts:
            files.extend(p for p in target.glob(f"**/*{ext}") if p.is_file())
    else:
        for ext in exts:
            files.extend(p for p in target.glob(f"*{ext}") if p.is_file())
    files = sorted({p.resolve() for p in files})
    return [f for f in files if not is_restructured_output_name(f.name)]


def collect_jobs(
    target: Path,
    *,
    recursive: bool,
    out_dir: Path | None,
    in_place: bool,
    max_files: int | None = None,
    skill_id: str | None = None,
) -> list[Job]:
    files = _iter_supported_files(target, recursive=recursive)

    if max_files is not None and len(files) > max_files:
        sys.exit(
            f"ERROR: {len(files)} supported files found; limit is --max-files={max_files}. "
            "Narrow the path, drop -r, or raise the limit."
        )

    jobs: list[Job] = []
    for src in files:
        if in_place:
            dst = src
        elif out_dir is not None:
            if target.is_dir():
                rel = src.relative_to(target)
                dst = out_dir / rel
            else:
                dst = out_dir / src.name
        else:
            dst = restructured_output_path(src, skill_id=skill_id)
        jobs.append(Job(src=src, dst=dst))
    return jobs


def jobs_from_document_files(
    sources: Sequence[Path],
    *,
    out_dir: Path | None,
    in_place: bool,
    skill_id: str | None = None,
) -> list[Job]:
    """Build jobs from an explicit list of supported files (e.g. TUI multi-select)."""
    out_base = out_dir.expanduser().resolve() if out_dir is not None else None
    seen_dst: set[Path] = set()
    jobs: list[Job] = []
    for src in sorted({p.expanduser().resolve() for p in sources}):
        if not src.is_file():
            raise ValueError(f"not a file: {src}")
        if not is_supported_extension(src):
            exts = ", ".join(supported_extensions())
            raise ValueError(f"unsupported file type {src.suffix!r} (supported: {exts}): {src}")
        if in_place:
            dst = src
        elif out_base is not None:
            dst = out_base / src.name
            if dst in seen_dst:
                stem = src.stem
                n = 2
                suffix = dst.suffix
                while (out_base / f"{stem}_{n}{suffix}") in seen_dst:
                    n += 1
                dst = out_base / f"{stem}_{n}{suffix}"
        else:
            dst = restructured_output_path(src, skill_id=skill_id)
        seen_dst.add(dst)
        jobs.append(Job(src=src, dst=dst))
    return jobs


def jobs_from_markdown_files(
    sources: Sequence[Path],
    *,
    out_dir: Path | None,
    in_place: bool,
    skill_id: str | None = None,
) -> list[Job]:
    """Alias for :func:`jobs_from_document_files` (backward compatibility)."""
    return jobs_from_document_files(
        sources,
        out_dir=out_dir,
        in_place=in_place,
        skill_id=skill_id,
    )


def strip_outer_fence(text: str) -> str:
    """Strip a single outer markdown code fence if the model returned one."""
    s = text.strip()
    for opener, closing in (
        ("````markdown", "````"),
        ("````md", "````"),
        ("```markdown", "```"),
        ("```md", "```"),
    ):
        if s.startswith(opener):
            after = s[len(opener) :].lstrip("\n")
            if after.rstrip().endswith(closing):
                return after.rstrip()[: -len(closing)].rstrip() + "\n"
    return text


def next_backup_path(path: Path) -> Path:
    """Return a non-conflicting sibling backup path for ``path``."""
    candidate = path.with_name(f"{path.name}.bak")
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = path.with_name(f"{path.name}.bak{n}")
        if not candidate.exists():
            return candidate
        n += 1


def _write_text_atomic(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically on the destination filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
            temp_name = handle.name
        os.replace(temp_name, path)
    except Exception:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except OSError:
                pass
        raise


def write_output_text(
    dst: Path,
    text: str,
    *,
    create_backup: bool = False,
) -> tuple[bool, Path | None, int]:
    """Persist output text safely, returning ``(changed, backup_path, bytes_out)``."""
    bytes_out = len(text.encode("utf-8"))
    if dst.exists() and dst.is_file():
        try:
            existing = read_markdown_text(dst).replace("\r\n", "\n").replace("\r", "\n")
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            if existing == normalized:
                return False, None, bytes_out
        except OSError:
            pass

    backup_path: Path | None = None
    if create_backup and dst.exists() and dst.is_file():
        backup_path = next_backup_path(dst)
        shutil.copy2(dst, backup_path)

    _write_text_atomic(dst, text)
    return True, backup_path, bytes_out


def restructure(
    client: Anthropic,
    *,
    model: str,
    max_tokens: int,
    system: str,
    content: str,
    progress: bool,
    progress_writer: Callable[[str], None] | None = None,
    max_attempts: int = 3,
) -> str:
    chunks: list[str] = []
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        chunks.clear()
        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
            ) as stream:
                for delta in stream.text_stream:
                    chunks.append(delta)
                    if progress:
                        if progress_writer is not None:
                            progress_writer(".")
                        else:
                            sys.stderr.write(".")
                            sys.stderr.flush()
            if progress:
                if progress_writer is not None:
                    progress_writer("\n")
                else:
                    sys.stderr.write("\n")
            return "".join(chunks)
        except (APIStatusError, APIConnectionError, APITimeoutError, RateLimitError) as e:
            last_exc = e
            if not _is_retryable(e) or attempt >= max_attempts - 1:
                raise RuntimeError(friendly_api_message(e)) from e
            delay = min(60.0, 2.0**attempt)
            time.sleep(delay)
    assert last_exc is not None
    raise RuntimeError(friendly_api_message(last_exc)) from last_exc


def process_job(
    job: Job,
    client: Anthropic,
    *,
    model: str,
    max_tokens: int,
    system: str,
    progress: bool,
    log: Callable[[str], None] | None = None,
    progress_writer: Callable[[str], None] | None = None,
    max_attempts: int = 3,
    backup_in_place: bool = False,
) -> JobResult:
    def _emit(msg: str) -> None:
        if log is not None:
            log(msg)
        else:
            print(msg, file=sys.stderr)

    _emit(f"-> {job.src}")
    try:
        raw = read_document_text(job.src)
    except DocumentReadError as e:
        _emit(f"   FAILED: {e}")
        return JobResult(
            job=job,
            ok=False,
            action="failed",
            error=str(e),
        )

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
        output = restructure(
            client,
            model=model,
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
    else:
        _emit(f"   unchanged {job.dst}")

    return JobResult(
        job=job,
        ok=True,
        action="wrote" if changed else "unchanged",
        changed=changed,
        backup_path=backup_path,
        bytes_in=bytes_in,
        bytes_out=bytes_out,
    )


def job_result_record(
    result: JobResult,
    *,
    provider: str | None = None,
) -> dict[str, object]:
    return {
        "src": str(result.job.src),
        "dst": str(result.job.dst),
        "ok": result.ok,
        "action": result.action,
        "changed": result.changed,
        "error": result.error,
        "bytes_in": result.bytes_in,
        "bytes_out": result.bytes_out,
        "backup_path": str(result.backup_path) if result.backup_path is not None else None,
        "provider": provider,
    }


def print_json_line(record: dict[str, object]) -> None:
    print(json.dumps(record, ensure_ascii=False), flush=True)
