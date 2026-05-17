from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli import config


def test_resolve_initial_folder_prefers_explicit(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    assert config.resolve_initial_folder(vault) == vault.resolve()


def test_resolve_initial_folder_file_uses_parent(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    md.write_text("# x", encoding="utf-8")
    assert config.resolve_initial_folder(md) == tmp_path.resolve()


def test_last_folder_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr(config, "config_path", lambda: cfg_file)
    folder = tmp_path / "obsidian"
    folder.mkdir()
    config.set_last_folder(folder)
    assert config.get_last_folder() == folder.resolve()
    assert config.resolve_initial_folder(None) == folder.resolve()
