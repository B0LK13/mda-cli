from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.cli import main

_BUNDLED_CATEGORIZE = (
    Path(__file__).resolve().parents[1] / "mda_cli" / "bundled_skills" / "categorize-vault-notes"
)


def test_plan_moves_dry_run_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("---\nfolder: inbox\n---\n# Note\n", encoding="utf-8")
    dest = vault / "inbox" / "note.md"

    monkeypatch.setenv("MDA_SKILL_DIR", str(_BUNDLED_CATEGORIZE))
    assert (
        main(
            [
                "script",
                "plan_moves",
                "--skill",
                "categorize-vault-notes",
                "--",
                str(vault),
            ]
        )
        == 0
    )
    assert note.resolve() == (vault / "note.md").resolve()
    assert not dest.exists()


def test_plan_moves_apply_moves_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "note.md"
    note.write_text("---\nfolder: inbox\n---\n# Note\n", encoding="utf-8")
    dest = vault / "inbox" / "note.md"

    monkeypatch.setenv("MDA_SKILL_DIR", str(_BUNDLED_CATEGORIZE))
    assert (
        main(
            [
                "script",
                "plan_moves",
                "--skill",
                "categorize-vault-notes",
                "--",
                str(vault),
                "--apply",
            ]
        )
        == 0
    )
    assert not note.exists()
    assert dest.is_file()
