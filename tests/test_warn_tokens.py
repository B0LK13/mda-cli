from __future__ import annotations

from pathlib import Path

from mda_cli.core import Job, warn_large_inputs


def test_warn_large_inputs_max_tokens_budget(tmp_path: Path) -> None:
    big = tmp_path / "big.md"
    big.write_text("x" * 500_000, encoding="utf-8")
    jobs = [Job(src=big, dst=big.with_suffix(".restructured.md"))]
    messages: list[str] = []

    warn_large_inputs(jobs, max_tokens=4096, writer=messages.append)

    joined = "\n".join(messages)
    assert "WARNING" in joined
    assert "--max-tokens" in joined
