"""Full-screen folder picker shown before the file browser."""

from __future__ import annotations

import os
import string
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


def list_windows_drives() -> list[Path]:
    """Return existing Windows drive roots (e.g. ``C:\\``, ``D:\\``)."""
    drives: list[Path] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(Path(root))
    return drives


def list_unix_mount_roots() -> list[Path]:
    """Return common filesystem roots on Linux, macOS, and WSL."""
    roots: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        if not resolved.is_dir() or resolved in seen:
            return
        seen.add(resolved)
        roots.append(resolved)

    add(Path("/"))

    mnt = Path("/mnt")
    if mnt.is_dir():
        try:
            for child in sorted(mnt.iterdir(), key=lambda p: p.name.lower()):
                if child.is_dir():
                    add(child)
        except OSError:
            pass

    for base in (Path("/media"), Path("/run/media")):
        if not base.is_dir():
            continue
        try:
            for user_dir in sorted(base.iterdir(), key=lambda p: p.name.lower()):
                if not user_dir.is_dir():
                    continue
                for mount in sorted(user_dir.iterdir(), key=lambda p: p.name.lower()):
                    if mount.is_dir():
                        add(mount)
        except OSError:
            pass

    return sorted(roots, key=lambda p: str(p).lower())


def list_disks() -> list[Path]:
    """Return selectable disk/volume roots for the current platform."""
    if os.name == "nt":
        return list_windows_drives()
    return list_unix_mount_roots()


def is_volume_root(path: Path) -> bool:
    """True when ``path`` is a top-level volume root (drive or mount)."""
    if os.name == "nt":
        try:
            resolved = path.resolve()
        except OSError:
            return False
        drive = resolved.drive
        if not drive:
            return False
        return resolved == Path(f"{drive}\\")

    posix = path.as_posix().rstrip("/") or "/"
    if posix == "/":
        return True
    segments = [part for part in posix.split("/") if part]
    if len(segments) == 2 and segments[0] == "mnt":
        return True
    if len(segments) == 3 and segments[0] == "media":
        return True
    if len(segments) == 4 and segments[0] == "run" and segments[1] == "media":
        return True
    return False


def _disk_row_label(path: Path) -> str:
    if os.name == "nt" and path.drive:
        return f"{path.drive}\\"
    return str(path)


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
        Binding("d", "show_disks", "Disks", show=True),
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
        self._disk_only_view = False

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
                "Enter = open  |  Backspace = up  |  D = disks  |  U = use folder  |  H = home  |  Q = quit",
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

    def _add_disk_rows(self, table: DataTable) -> None:
        for disk in list_disks():
            table.add_row(
                _disk_row_label(disk),
                "disk",
                "",
                key=self._alloc_row_key(),
            )
            self._rows.append((disk, "disk"))

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

        if self._disk_only_view:
            self._add_disk_rows(table)
            table.focus()
            return

        if not self.cwd.is_dir():
            return

        if is_volume_root(self.cwd):
            self._add_disk_rows(table)

        try:
            entries = list(self.cwd.iterdir())
        except OSError:
            table.focus()
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
        if self._disk_only_view:
            self._disk_only_view = False
            self.refresh_listing()
            return
        parent = self.cwd.parent
        if parent == self.cwd:
            return
        self.cwd = parent.resolve()
        self.refresh_listing()

    def action_go_home(self) -> None:
        self._disk_only_view = False
        self.cwd = Path.home().resolve()
        self.refresh_listing()

    def action_show_disks(self) -> None:
        self._disk_only_view = not self._disk_only_view
        self.refresh_listing()

    def action_open(self) -> None:
        idx = self._cursor_row_index()
        if idx is None:
            return
        path, kind = self._rows[idx]
        if path is None:
            return
        if kind == "disk":
            self.cwd = path.resolve()
            self._disk_only_view = False
        elif kind == "up":
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
