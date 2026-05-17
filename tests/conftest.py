from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    d = tmp_path / "markdown-document-architect"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: markdown-document-architect\n---\n# Skill\n",
        encoding="utf-8",
    )
    (d / "MDA-STANDARD.md").write_text("# Standard\n", encoding="utf-8")
    return d
