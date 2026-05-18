from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.document_io import count_supported_files_in_dir
from mda_cli.folder_picker import (
    FolderPickerApp,
    is_volume_root,
    list_disks,
    list_unix_mount_roots,
    list_windows_drives,
)


def test_count_supported_files_in_dir_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.md").write_text("# C", encoding="utf-8")
    assert count_supported_files_in_dir(tmp_path) == 2
    assert count_supported_files_in_dir(sub) == 1


def test_list_windows_drives(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_exists(path: str) -> bool:
        return path in ("C:\\", "E:\\")

    monkeypatch.setattr("mda_cli.folder_picker.os.path.exists", fake_exists)
    drives = list_windows_drives()
    assert drives == [Path("C:\\"), Path("E:\\")]


def test_list_unix_mount_roots_includes_root() -> None:
    import os

    if os.name == "nt":
        pytest.skip("unix-only")
    roots = list_unix_mount_roots()
    assert Path("/").resolve() in roots
    assert roots == sorted(roots, key=lambda p: str(p).lower())


def test_list_disks_delegates_by_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    win = [Path("C:\\")]
    unix = [Path("/")]

    monkeypatch.setattr("mda_cli.folder_picker.os.name", "nt")
    monkeypatch.setattr("mda_cli.folder_picker.list_windows_drives", lambda: win)
    assert list_disks() == win

    monkeypatch.setattr("mda_cli.folder_picker.os.name", "posix")
    monkeypatch.setattr("mda_cli.folder_picker.list_unix_mount_roots", lambda: unix)
    assert list_disks() == unix


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (Path("/"), True),
        (Path("/mnt/c"), True),
        (Path("/media/user/USB"), True),
        (Path("/run/media/user/USB"), True),
        (Path("/home/user"), False),
        (Path("/mnt"), False),
    ],
)
def test_is_volume_root_unix(path: Path, expected: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mda_cli.folder_picker.os.name", "posix")
    assert is_volume_root(path) is expected


def test_is_volume_root_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mda_cli.folder_picker.os.name", "nt")
    assert is_volume_root(Path("C:\\")) is True
    assert is_volume_root(Path("C:\\Users")) is False


@pytest.mark.asyncio
async def test_folder_picker_use_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "one.md").write_text("# One", encoding="utf-8")

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


@pytest.mark.asyncio
async def test_folder_picker_disk_only_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disks = [tmp_path / "disk-a", tmp_path / "disk-b"]
    for d in disks:
        d.mkdir()
    target = disks[1]

    monkeypatch.setattr("mda_cli.folder_picker.list_disks", lambda: disks)
    monkeypatch.setattr("mda_cli.folder_picker.set_last_folder", lambda p: None)

    app = FolderPickerApp(start=tmp_path / "start")
    (tmp_path / "start").mkdir()
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert app._disk_only_view is True
        await pilot.press("down")
        await pilot.press("enter")
        assert app.cwd.resolve() == target.resolve()
        assert app._disk_only_view is False
        await pilot.press("q")


@pytest.mark.asyncio
async def test_folder_picker_disks_at_volume_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disk = tmp_path / "vol"
    disk.mkdir()
    sub = disk / "nested"
    sub.mkdir()

    monkeypatch.setattr("mda_cli.folder_picker.list_disks", lambda: [disk])
    monkeypatch.setattr("mda_cli.folder_picker.is_volume_root", lambda p: p.resolve() == disk.resolve())

    app = FolderPickerApp(start=disk)
    async with app.run_test() as pilot:
        kinds = [kind for _, kind in app._rows]
        assert kinds.count("disk") == 1
        assert "up" in kinds
        await pilot.press("down")  # disk row
        await pilot.press("down")  # ..
        await pilot.press("down")  # nested/
        await pilot.press("enter")
        assert app.cwd.resolve() == sub.resolve()
        await pilot.press("q")
