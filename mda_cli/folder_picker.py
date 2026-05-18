"""Full-screen folder picker shown before the file browser."""

from __future__ import annotations

import os
from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Label

from mda_cli.config import resolve_initial_folder, set_last_folder
from mda_cli.document_io import count_supported_files_in_dir, supported_extensions


def _is_windows_hidden(path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes

        attrs = ctypes.windll.kernel32.GetFileAttributesW(os.fspath(path))
        if attrs == -1:
            return False
        return bool(attrs & 2)
    except Exception:
        return False


class FolderPickerApp(App[Path | None]):
    """Browse directories and confirm a working folder for MDA."""

    CSS = """
    #picker-main { height: 100%; padding: 0 1; }
    #title { text-style: bold; }
    #path-label { margin: 0 0 1 0; }
    #hint { margin: 0 0 1 0; color: $text-muted; }
    #listing { height: 1fr; min-height: 12; border: heavy $primary; }
    """

    BINDINGS = [
        Binding("q", "quit_cancel", "Quit", show=True),
        Binding("escape", "quit_cancel", "Quit"),
        Binding("u", "use_folder", "Use this folder", show=True),
        Binding("h", "go_home", "Home", show=True),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
    ]

    TITLE = "MDA — Select folder"

    def __init__(self, *, start: Path | None) -> None:
        super().__init__()
        self.cwd = resolve_initial_folder(start)
        self._rows: list[tuple[Path | None, str]] = []
        self._row_key_seq = 0
        self.selected_folder: Path | None = None

    def _alloc_row_key(self) -> str:
        self._row_key_seq += 1
        return f"fp{self._row_key_seq}"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="picker-main"):
            yield Label("Select folder", id="title")
            yield Label(id="path-label")
            yield Label(id="file-count-label")
            yield Label(
                "Enter = open  |  Backspace = up  |  U = use folder  |  H = home  |  Q = quit",
                id="hint",
            )
            yield DataTable(id="listing", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#listing", DataTable)
        exts_label = "files"
        table.add_columns(("Name", "name"), ("Kind", "kind"), (exts_label, "count"))
        self.refresh_listing()

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if focused is None:
            return
        try:
            listing = self.query_one("#listing", DataTable)
        except Exception:
            return
        if focused is not listing:
            return

        if event.key == "enter":
            self.action_open()
            event.prevent_default()
            event.stop()
        elif event.key == "backspace":
            self.action_go_up()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            listing.action_cursor_up()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            listing.action_cursor_down()
            event.prevent_default()
            event.stop()

    def refresh_listing(self) -> None:
        table = self.query_one("#listing", DataTable)
        table.clear()
        self._rows.clear()

        self.query_one("#path-label", Label).update(str(self.cwd))
        here_n = count_supported_files_in_dir(self.cwd)
        exts = ", ".join(supported_extensions())
        self.query_one("#file-count-label", Label).update(
            f"Supported files in this folder ({exts}): {here_n}"
        )

        if not self.cwd.is_dir():
            return

        try:
            entries = list(self.cwd.iterdir())
        except OSError:
            return

        dirs = sorted([p for p in entries if p.is_dir()], key=lambda p: p.name.lower())
        visible_dirs = [
            p
            for p in dirs
            if not p.name.startswith(".") and not _is_windows_hidden(p)
        ]

        table.add_row("..", "parent", "", key=self._alloc_row_key())
        self._rows.append((self.cwd.parent, "up"))

        for p in visible_dirs:
            md_n = count_supported_files_in_dir(p)
            md_label = str(md_n) if md_n else "—"
            table.add_row(f"{p.name}/", "dir", md_label, key=self._alloc_row_key())
            self._rows.append((p, "dir"))

        table.focus()

    def _cursor_row_index(self) -> int | None:
        table = self.query_one("#listing", DataTable)
        coord = table.cursor_coordinate
        if coord is None:
            return None
        row = coord.row
        if row < 0 or row >= len(self._rows):
            return None
        return row

    def action_go_up(self) -> None:
        parent = self.cwd.parent
        if parent == self.cwd:
            return
        self.cwd = parent.resolve()
        self.refresh_listing()

    def action_go_home(self) -> None:
        self.cwd = Path.home().resolve()
        self.refresh_listing()

    def action_open(self) -> None:
        idx = self._cursor_row_index()
        if idx is None:
            return
        path, kind = self._rows[idx]
        if path is None:
            return
        if kind == "up":
            self.cwd = path.resolve()
        elif kind == "dir":
            self.cwd = path.resolve()
        self.refresh_listing()

    def action_use_folder(self) -> None:
        if not self.cwd.is_dir():
            return
        folder = self.cwd.resolve()
        set_last_folder(folder)
        self.selected_folder = folder
        self.exit(folder)

    def action_quit_cancel(self) -> None:
        self.selected_folder = None
        self.exit(None)


def pick_folder(*, start: Path | None) -> Path | None:
    """Run the folder picker; return the chosen directory or ``None`` if cancelled."""
    app = FolderPickerApp(start=start)
    result = app.run()
    if isinstance(result, Path):
        return result
    return app.selected_folder
