from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from mda_cli.cli import build_parser, main


def test_parser_tui_allows_no_target() -> None:
    args = build_parser().parse_args(["--tui"])
    assert args.tui is True
    assert args.target is None


def test_parser_tui_with_start_path() -> None:
    args = build_parser().parse_args(["--tui", r"C:\Users\Admin"])
    assert args.tui is True
    assert args.target == Path(r"C:\Users\Admin")


def test_main_no_args_opens_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []

    def fake_run_tui(**kwargs: object) -> int:
        called.append(True)
        return 0

    monkeypatch.setattr("mda_cli.tui.run_tui", fake_run_tui)
    assert main([]) == 0
    assert called == [True]


def test_parser_default_no_target_implies_tui() -> None:
    args = build_parser().parse_args([])
    assert args.target is None
    assert args.tui is False


def test_main_rejects_dry_run_with_tui() -> None:
    with pytest.raises(SystemExit):
        main(["--tui", "--dry-run"])


def test_main_rejects_backup_without_in_place() -> None:
    with pytest.raises(SystemExit):
        main(["--backup"])


def test_main_tui_delegates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict = {}

    def fake_run_tui(**kwargs: object) -> int:
        captured.update(kwargs)
        return 7

    monkeypatch.setattr("mda_cli.tui.run_tui", fake_run_tui)
    assert main(["--tui", str(tmp_path)]) == 7
    assert captured["start"] == tmp_path
    assert captured["skill_dir"] is None
    assert captured["max_attempts"] == 3


def test_main_bare_path_uses_batch_not_tui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, skill_dir: Path
) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Hello", encoding="utf-8")
    monkeypatch.setenv("MDA_SKILL_DIR", str(skill_dir))
    monkeypatch.setenv("MDA_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    def fail_tui(**kwargs: object) -> int:
        raise AssertionError("TUI should not run in batch mode")

    monkeypatch.setattr("mda_cli.tui.run_tui", fail_tui)
    with pytest.raises(SystemExit):
        main([str(md)])


def test_subprocess_help() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "--tui" in r.stdout


def test_subprocess_version() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "mda" in r.stdout.lower() or "0.2" in r.stdout


def test_subprocess_check_ok(skill_dir: Path) -> None:
    env = os.environ.copy()
    env["MDA_SKILL_DIR"] = str(skill_dir)
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", "--check"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "Check OK" in r.stdout
    assert "Skill source: env" in r.stdout


def test_subprocess_check_bundled_without_external_skill() -> None:
    env = os.environ.copy()
    env.pop("MDA_SKILL_DIR", None)
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", "--check"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "Bundled skills:" in r.stdout
    assert "categorize-vault-notes" in r.stdout
    assert "Skill source: bundled" in r.stdout or "Skill source:" in r.stdout
    assert "Check OK" in r.stdout


def test_subprocess_dry_run_no_api_key(tmp_path: Path, skill_dir: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Hello", encoding="utf-8")
    env = os.environ.copy()
    env["MDA_SKILL_DIR"] = str(skill_dir)
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", str(md), "--dry-run"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "doc.md" in r.stdout
    assert "restructured" in r.stdout


def test_subprocess_batch_fails_without_api_key(tmp_path: Path, skill_dir: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Hello", encoding="utf-8")
    env = os.environ.copy()
    env["MDA_SKILL_DIR"] = str(skill_dir)
    env["MDA_PROVIDER"] = "anthropic"
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("MDA_USE_OPENROUTER", None)
    r = subprocess.run(
        [sys.executable, "-m", "mda_cli", str(md)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0
    assert "ANTHROPIC_API_KEY" in (r.stderr + r.stdout)
