from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.tui import FilterScreen, JumpPathScreen, MdaNavigatorApp


@pytest.mark.asyncio
async def test_tui_mount_stylesheet_and_select_supported(skill_dir: Path, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "one.md").write_text("# One\n", encoding="utf-8")
    note = docs / "note.txt"
    note.write_text("x", encoding="utf-8")

    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        assert app.cwd.resolve() == docs.resolve()
        await pilot.press("down")  # .. -> note.txt
        await pilot.press("space")
        assert app.selected == {note.resolve()}
        await pilot.press("down")  # one.md
        await pilot.press("space")
        assert app.selected == {note.resolve(), (docs / "one.md").resolve()}
        await pilot.press("o")
        assert app.output_mode == "in_place"
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_enter_opens_subdirectory(skill_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "inside"
    sub.mkdir()
    (sub / "a.md").write_text("# A", encoding="utf-8")
    app = MdaNavigatorApp(
        start=root,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        await pilot.press("down")  # .. -> inside/
        await pilot.press("enter")
        assert app.cwd.resolve() == sub.resolve()
        await pilot.press("q")


@pytest.mark.asyncio
async def test_run_tui_runs_folder_picker_first(
    monkeypatch: pytest.MonkeyPatch, skill_dir: Path, tmp_path: Path
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("# A", encoding="utf-8")
    navigator_starts: list[Path] = []

    def fake_pick_folder(*, start: Path | None) -> Path | None:
        assert start is None or start == vault
        return vault.resolve()

    class FakeNavigator:
        def __init__(self, **kwargs: object) -> None:
            navigator_starts.append(kwargs["start"])  # type: ignore[index]

        def run(self) -> None:
            return None

    monkeypatch.setattr("mda_cli.folder_picker.pick_folder", fake_pick_folder)
    monkeypatch.setattr("mda_cli.tui.MdaNavigatorApp", FakeNavigator)

    from mda_cli.tui import run_tui

    assert run_tui(start=vault, skill_dir=skill_dir, model="x", max_tokens=100) == 0
    assert navigator_starts == [vault.resolve()]


@pytest.mark.asyncio
async def test_tui_jump_path_worker(skill_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "doc.md").write_text("# Doc", encoding="utf-8")

    app = MdaNavigatorApp(
        start=root,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )

    async def fake_push_screen_wait(screen, *, mode=None):  # noqa: ARG001
        return target.resolve()

    app.push_screen_wait = fake_push_screen_wait  # type: ignore[method-assign]

    async with app.run_test() as pilot:
        worker = app.action_jump_path()
        await worker.wait()
        assert app.cwd.resolve() == target.resolve()
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_jump_path_via_binding(skill_dir: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "other"
    target.mkdir()

    app = MdaNavigatorApp(
        start=root,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        await pilot.press("ctrl+j")
        assert isinstance(app.screen, JumpPathScreen)
        jump_in = app.screen.query_one("#jump-in")
        jump_in.value = str(target)
        await pilot.press("enter")
        await pilot.pause()
        assert app.cwd.resolve() == target.resolve()
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_filter_listing_worker(skill_dir: Path, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "alpha.md").write_text("# A", encoding="utf-8")
    (docs / "beta.md").write_text("# B", encoding="utf-8")

    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )

    async def fake_push_screen_wait(screen, *, mode=None):  # noqa: ARG001
        return "alpha"

    app.push_screen_wait = fake_push_screen_wait  # type: ignore[method-assign]

    async with app.run_test() as pilot:
        worker = app.action_filter_listing()
        await worker.wait()
        assert app.name_filter == "alpha"
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_filter_via_binding(skill_dir: Path, tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "alpha.md").write_text("# A", encoding="utf-8")
    (docs / "keep.txt").write_text("x", encoding="utf-8")

    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        await pilot.press("f")
        assert isinstance(app.screen, FilterScreen)
        filt_in = app.screen.query_one("#filter-in")
        filt_in.value = "alpha"
        await pilot.press("enter")
        await pilot.pause()
        assert app.name_filter == "alpha"
        names = {p.name for p, _ in app._rows if p is not None}
        assert "alpha.md" in names
        assert "keep.txt" not in names
        await pilot.press("q")


@pytest.mark.asyncio
async def test_tui_start_file_uses_parent(skill_dir: Path, tmp_path: Path) -> None:
    f = tmp_path / "x.md"
    f.write_text("# X", encoding="utf-8")
    app = MdaNavigatorApp(
        start=f,
        skill_dir=skill_dir,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        assert app.cwd == f.parent.resolve()
        await pilot.press("q")
