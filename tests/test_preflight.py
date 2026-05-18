from __future__ import annotations

from pathlib import Path

from mda_cli.core import Job
from mda_cli.preflight import build_batch_preflight, format_preflight_message


def test_build_batch_preflight_token_warning(tmp_path: Path) -> None:
    big = tmp_path / "big.md"
    big.write_text("x" * 500_000, encoding="utf-8")
    jobs = [Job(src=big, dst=big.with_suffix(".restructured.md"))]
    summary = build_batch_preflight(jobs, max_tokens=4096, output_mode="sibling")
    assert summary.file_count == 1
    assert summary.output_mode == "sibling"
    assert summary.total_bytes >= 500_000
    assert any("max-tokens" in w.lower() or "token" in w.lower() for w in summary.warnings)
    body = format_preflight_message(summary)
    assert "Files selected: 1" in body
    assert "Token estimate" in body
    assert "Warnings:" in body


def test_build_batch_preflight_no_warnings_small_batch(tmp_path: Path) -> None:
    small = tmp_path / "note.md"
    small.write_text("# Hi\n", encoding="utf-8")
    jobs = [Job(src=small, dst=small)]
    summary = build_batch_preflight(jobs, max_tokens=16_000, output_mode="in_place")
    assert summary.file_count == 1
    assert summary.warnings == ()
    body = format_preflight_message(summary)
    assert "No size or token warnings" in body
