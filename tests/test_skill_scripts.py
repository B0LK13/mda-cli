from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.cli import main


def test_script_list_lists_categorize_scripts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("MDA_SKILL_DIR", raising=False)
    assert main(["script", "--list", "--skill", "categorize-vault-notes"]) == 0
    out = capsys.readouterr().out
    assert "scan_vault.py" in out
    assert "plan_moves.py" in out


def test_script_scan_vault_dry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "a.md").write_text("---\narea: inbox\ntags: []\n---\n# A\n", encoding="utf-8")
    monkeypatch.delenv("MDA_SKILL_DIR", raising=False)
    assert (
        main(
            [
                "script",
                "scan_vault",
                "--skill",
                "categorize-vault-notes",
                "--",
                str(tmp_path),
            ]
        )
        == 0
    )
