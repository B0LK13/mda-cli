from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.document_io import count_supported_files_in_dir
from mda_cli.folder_picker import FolderPickerApp


def test_count_supported_files_in_dir_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("# C", encoding="utf-8")
    assert count_supported_files_in_dir(tmp_path) == 2
    assert count_supported_files_in_dir(sub) == 1


@pytest.mark.asyncio
async def test_folder_picker_use_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "one.md").write_text("# One", encoding="utf-8")

    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("mda_cli.folder_picker.set_last_folder", lambda p: None)

    app = FolderPickerApp(start=vault)
    async with app.run_test() as pilot:
        assert app.cwd.resolve() == vault.resolve()
        await pilot.press("u")
    assert app.selected_folder == vault.resolve()


@pytest.mark.asyncio
async def test_folder_picker_enter_subdirectory(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "inside"
    sub.mkdir()
    app = FolderPickerApp(start=root)
    async with app.run_test() as pilot:
        await pilot.press("down")  # .. -> inside/
        await pilot.press("enter")
        assert app.cwd.resolve() == sub.resolve()
        await pilot.press("q")
