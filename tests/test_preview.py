from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.preview import (
    DEFAULT_PREVIEW_MAX_CHARS,
    format_preview_display,
    format_preview_error_banner,
    format_preview_metadata,
    truncate_preview_text,
)


def test_truncate_preview_text_short() -> None:
    body, truncated = truncate_preview_text("hello", max_chars=100)
    assert body == "hello"
    assert truncated is False


def test_truncate_preview_text_long() -> None:
    raw = "x" * (DEFAULT_PREVIEW_MAX_CHARS + 500)
    body, truncated = truncate_preview_text(raw, max_chars=DEFAULT_PREVIEW_MAX_CHARS)
    assert len(body) == DEFAULT_PREVIEW_MAX_CHARS
    assert truncated is True


def test_format_preview_display_empty() -> None:
    text = format_preview_display(metadata="meta", body="", truncated=False)
    assert "meta" in text
    assert "(empty)" in text


def test_format_preview_display_truncated() -> None:
    text = format_preview_display(metadata="m", body="abc", truncated=True)
    assert "… truncated" in text


def test_format_preview_error_banner() -> None:
    text = format_preview_error_banner("PDF extra not installed")
    assert "EXTRACTION ERROR" in text
    assert "PDF extra not installed" in text


def test_format_preview_metadata(tmp_path: Path) -> None:
    p = tmp_path / "note.md"
    p.write_text("# Hi", encoding="utf-8")
    meta = format_preview_metadata(p)
    assert "note.md" in meta
    assert ".md" in meta


@pytest.mark.asyncio
async def test_tui_preview_body_not_focusable(skill_dir: Path, tmp_path: Path) -> None:
    from textual.widgets import TextArea

    from mda_cli.tui import MdaNavigatorApp

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "one.md").write_text("# One", encoding="utf-8")

    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        preview = app.query_one("#preview-body", TextArea)
        assert preview.can_focus is False
        await pilot.press("down")
        await pilot.press("space")
        assert app.selected
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_highlight_updates_preview(skill_dir: Path, tmp_path: Path) -> None:
    from textual.widgets import TextArea

    from mda_cli.tui import MdaNavigatorApp

    docs = tmp_path / "docs"
    docs.mkdir()
    sample = docs / "sample.md"
    sample.write_text("# Preview me\n\nBody line.\n", encoding="utf-8")

    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        await pilot.press("down")  # .. -> sample.md
        await pilot.pause(delay=0.25)
        preview = app.query_one("#preview-body", TextArea)
        assert "Preview me" in preview.text or "Body line" in preview.text
        await pilot.press("q")
