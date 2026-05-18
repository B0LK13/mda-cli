"""TUI document preview helpers (truncation, metadata, formatting)."""

from __future__ import annotations

from pathlib import Path

DEFAULT_PREVIEW_MAX_CHARS = 10_000


def truncate_preview_text(
    text: str,
    *,
    max_chars: int = DEFAULT_PREVIEW_MAX_CHARS,
) -> tuple[str, bool]:
    """Return preview body and whether it was truncated."""
    if max_chars <= 0:
        return "", bool(text)
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def format_file_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def format_preview_metadata(
    path: Path,
    *,
    error: str | None = None,
) -> str:
    """Single-line metadata for the preview header."""
    try:
        stat = path.stat()
        size = format_file_size(stat.st_size)
    except OSError:
        size = "?"
    ext = path.suffix.lower() or "(no ext)"
    base = f"{path.name}  |  {ext}  |  {size}  |  {path.parent}"
    if error:
        return f"{base}  |  [error]"
    return base


def format_preview_display(
    *,
    metadata: str,
    body: str,
    truncated: bool,
    error: str | None = None,
) -> str:
    """Full preview pane text (plain; Rich markup applied in TUI if needed)."""
    lines = [metadata, ""]
    if error:
        lines.append(error)
    elif body == "":
        lines.append("(empty)")
    else:
        lines.append(body)
        if truncated:
            lines.append("")
            lines.append("… truncated")
    return "\n".join(lines)
