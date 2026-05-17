"""Textual TUI: browse the filesystem, multi-select Markdown files, run MDA."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Input, Label, RichLog

from mda_cli.core import Job, find_skill_dir, jobs_from_document_files, load_system_prompt
from mda_cli.document_io import is_supported_extension, supported_extensions
from mda_cli.providers import (
    build_restructure_client,
    ensure_api_credentials,
    process_job_with_provider,
    resolve_provider_name,
)


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


class JumpPathScreen(ModalScreen[Path | None]):
    """Enter a filesystem path to jump the listing to."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def compose(self) -> ComposeResult:
        yield Label("Directory path (Enter = go, Esc = cancel):")
        yield Input(placeholder="C:\\path or ~/projects/foo", id="jump-in")

    def on_mount(self) -> None:
        self.query_one("#jump-in", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "jump-in":
            return
        raw = event.value.strip()
        if not raw:
            self.dismiss(None)
            return
        p = Path(raw).expanduser()
        if not p.exists():
            self.dismiss(None)
            return
        if p.is_file():
            p = p.parent
        self.dismiss(p.resolve())


class FilterScreen(ModalScreen[str | None]):
    """Filter listing by substring (case-insensitive); empty clears filter."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, initial: str) -> None:
        super().__init__()
        self.initial = initial

    def compose(self) -> ComposeResult:
        yield Label("Name filter (Enter = apply, Esc = cancel):")
        yield Input(placeholder="substring…", id="filter-in")

    def on_mount(self) -> None:
        inp = self.query_one("#filter-in", Input)
        inp.value = self.initial
        inp.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "filter-in":
            return
        self.dismiss(event.value.strip().lower())


class MdaNavigatorApp(App[None]):
    """Two-pane browser + log. Select supported documents with Space, run with P."""

    CSS = """
    #main { height: 100%; }
    #left { width: 45%; height: 100%; border: heavy $primary; padding: 0 1; }
    #right { width: 1fr; height: 100%; border: heavy $primary; padding: 0 1; }
    #listing { height: 1fr; min-height: 10; }
    #log { height: 1fr; min-height: 10; background: $surface; }
    Label { margin: 0 0 1 0; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit"),
        Binding("o", "cycle_output", "Output mode", show=True),
        Binding("p", "run_mda", "Run MDA", show=True),
        Binding("g", "focus_out_dir", "Out folder", show=True),
        Binding("h", "go_home", "Home", show=True),
        Binding("ctrl+j", "jump_path", "Jump", show=True),
        Binding("f", "filter_listing", "Filter", show=True),
        Binding("v", "toggle_hidden", "Hidden", show=True),
        Binding("a", "select_recursive_supported", "Recursive all", show=True),
    ]

    def __init__(
        self,
        *,
        start: Path | None,
        skill_dir: Path | None,
        skill_id: str | None = None,
        model: str,
        max_tokens: int,
        max_attempts: int = 3,
        provider: str | None = None,
    ) -> None:
        super().__init__()
        base = (start or Path.cwd()).expanduser()
        if base.is_file():
            self.cwd = base.resolve().parent
        else:
            self.cwd = base.resolve()
        self.skill_dir_arg = skill_dir
        self.skill_id = skill_id
        self.model = model
        self.max_tokens = max_tokens
        self.max_attempts = max_attempts
        self.provider = provider
        self.selected: set[Path] = set()
        self.output_mode: str = "sibling"  # sibling | in_place | out_dir
        self._rows: list[tuple[Path | None, str]] = []
        self._selectable_row_keys: dict[Path, object] = {}
        self._row_key_seq = 0
        self._col_name_key: object | None = None
        self.name_filter: str = ""
        self.show_hidden: bool = False

    def _alloc_row_key(self) -> str:
        self._row_key_seq += 1
        return f"lr{self._row_key_seq}"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Label(id="path-label")
                yield DataTable(id="listing", zebra_stripes=True, cursor_type="row")
                yield Label(id="selection-label")
                yield Label(id="mode-label")
                yield Label(id="filter-label")
                yield Input(
                    placeholder="Output folder when mode is out_dir (absolute or ~)",
                    id="out-dir",
                )
            with Vertical(id="right"):
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#listing", DataTable)
        name_k, _kind_k = table.add_columns(("Name", "name"), ("Kind", "kind"))
        self._col_name_key = name_k
        self.refresh_listing()
        exts = ", ".join(supported_extensions())
        self.log_msg(
            f"[dim]Supported:[/] {exts}\n"
            "[dim]Space[/] toggle file  [dim]Enter[/] open dir  [dim]Backspace[/] up  "
            "[dim]ctrl+j[/] jump  [dim]f[/] filter  [dim]v[/] hidden  "
            "[dim]a[/] recursive select  [dim]k/j[/] up/down  [dim]O[/] output  [dim]P[/] run  "
            "[dim]G[/] out-folder  [dim]H[/] home"
        )

    def on_key(self, event: events.Key) -> None:
        """Route navigation keys to the file listing; DataTable swallows them otherwise."""
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
            self.action_activate()
            event.prevent_default()
            event.stop()
        elif event.key == "space":
            self.action_toggle_select()
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

    def log_msg(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def _mode_label(self) -> str:
        if self.output_mode == "sibling":
            return "Output mode: sibling (*.restructured.md next to source)"
        if self.output_mode == "in_place":
            return "Output mode: in-place (overwrite source)"
        return "Output mode: out_dir (use input below)"

    def _selection_label(self) -> str:
        if not self.selected:
            return "Selected: (none)"
        n = len(self.selected)
        if n <= 3:
            names = ", ".join(p.name for p in sorted(self.selected))
            return f"Selected ({n}): {names}"
        return f"Selected: {n} file(s)"

    def _filter_status(self) -> str:
        base = f"Filter: {self.name_filter!r}" if self.name_filter else "Filter: (none)"
        hid = "show hidden" if self.show_hidden else "hide hidden/dotfiles"
        return f"{base}  |  {hid}"

    def _entry_name_ok(self, name: str) -> bool:
        if not self.name_filter:
            return True
        return self.name_filter in name.lower()

    def _path_visible(self, path: Path, *, is_dir: bool) -> bool:
        del is_dir  # reserved for future use
        if not self.show_hidden:
            if path.name.startswith("."):
                return False
            if _is_windows_hidden(path):
                return False
        return self._entry_name_ok(path.name)

    def refresh_listing(self) -> None:
        prev_focus_id: str | None = None
        w = self.focused
        if w is not None and hasattr(w, "id") and w.id is not None:
            prev_focus_id = str(w.id)

        table = self.query_one("#listing", DataTable)
        table.clear()
        self._rows.clear()
        self._selectable_row_keys.clear()

        self.query_one("#path-label", Label).update(str(self.cwd))
        self.query_one("#mode-label", Label).update(self._mode_label())
        self.query_one("#selection-label", Label).update(self._selection_label())
        self.query_one("#filter-label", Label).update(self._filter_status())

        if self._col_name_key is None:
            return

        if not self.cwd.is_dir():
            self.log_msg(f"[red]Not a directory:[/] {self.cwd}")
            return

        try:
            entries = list(self.cwd.iterdir())
        except OSError as e:
            self.log_msg(f"[red]Cannot read directory:[/] {e}")
            return

        dirs = sorted([p for p in entries if p.is_dir()], key=lambda p: p.name.lower())
        files = sorted([p for p in entries if p.is_file()], key=lambda p: p.name.lower())

        dirs = [p for p in dirs if self._path_visible(p, is_dir=True)]
        files = [p for p in files if self._path_visible(p, is_dir=False)]

        table.add_row("..", "parent", key=self._alloc_row_key())
        self._rows.append((self.cwd.parent, "up"))

        for p in dirs:
            table.add_row(f"{p.name}/", "dir", key=self._alloc_row_key())
            self._rows.append((p, "dir"))

        for p in files:
            selectable = is_supported_extension(p)
            kind = p.suffix.lower().lstrip(".") or "file"
            if not selectable:
                kind = "file"
            pr = p.resolve()
            mark = "* " if pr in self.selected else ""
            rk = table.add_row(f"{mark}{p.name}", kind, key=self._alloc_row_key())
            row_kind = kind if selectable else "file"
            self._rows.append((pr, row_kind))
            if selectable:
                self._selectable_row_keys[pr] = rk

        if prev_focus_id == "out-dir":
            self.query_one("#out-dir", Input).focus()
        else:
            self.query_one("#listing", DataTable).focus()

    def _sync_selectable_row_star(self, path: Path) -> None:
        if self._col_name_key is None:
            return
        rk = self._selectable_row_keys.get(path)
        if rk is None:
            return
        table = self.query_one("#listing", DataTable)
        mark = "* " if path in self.selected else ""
        table.update_cell(rk, self._col_name_key, f"{mark}{path.name}")

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

    @work
    async def action_jump_path(self) -> None:
        path = await self.push_screen_wait(JumpPathScreen())
        if path is None:
            return
        if not path.is_dir():
            self.log_msg(f"[yellow]Not a directory:[/] {path}")
            return
        self.cwd = path
        self.refresh_listing()

    @work
    async def action_filter_listing(self) -> None:
        res = await self.push_screen_wait(FilterScreen(self.name_filter))
        if res is None:
            return
        self.name_filter = res
        self.refresh_listing()

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self.refresh_listing()

    def action_select_recursive_supported(self) -> None:
        from mda_cli.document_io import is_restructured_output_name

        cap = 500
        found: list[Path] = []
        for ext in supported_extensions():
            for p in sorted(self.cwd.rglob(f"*{ext}")):
                if not p.is_file():
                    continue
                if is_restructured_output_name(p.name):
                    continue
                found.append(p.resolve())
        found = sorted(set(found))
        if len(found) > cap:
            self.log_msg(
                f"[yellow]Recursive select:[/] {len(found)} files found; "
                f"only first {cap} added."
            )
            found = found[:cap]
        else:
            self.log_msg(f"[cyan]Recursive select:[/] {len(found)} file(s) under {self.cwd}")
        self.selected.update(found)
        self.refresh_listing()

    def action_activate(self) -> None:
        idx = self._cursor_row_index()
        if idx is None:
            return
        path, kind = self._rows[idx]
        if path is None:
            return
        if kind == "up":
            self.cwd = path.resolve()
            self.refresh_listing()
        elif kind == "dir":
            self.cwd = path.resolve()
            self.refresh_listing()

    def action_toggle_select(self) -> None:
        idx = self._cursor_row_index()
        if idx is None:
            return
        path, kind = self._rows[idx]
        if path is None or not is_supported_extension(path):
            return
        if path in self.selected:
            self.selected.remove(path)
        else:
            self.selected.add(path)
        self._sync_selectable_row_star(path)
        self.query_one("#selection-label", Label).update(self._selection_label())

    def action_cycle_output(self) -> None:
        order = ("sibling", "in_place", "out_dir")
        i = order.index(self.output_mode)
        self.output_mode = order[(i + 1) % len(order)]
        self.query_one("#mode-label", Label).update(self._mode_label())

    def action_focus_out_dir(self) -> None:
        self.query_one("#out-dir", Input).focus()

    def _run_batch_sync(self, skill_dir: Path, jobs: list[Job]) -> None:
        def thread_log(msg: str) -> None:
            self.call_from_thread(self.log_msg, msg)

        system = load_system_prompt(skill_dir)
        client, ctx = build_restructure_client(
            cli_provider=self.provider,
            model=self.model,
            max_tokens=self.max_tokens,
        )
        ok = 0
        for job in jobs:
            try:
                result = process_job_with_provider(
                    job,
                    client,
                    ctx,
                    max_tokens=self.max_tokens,
                    system=system,
                    progress=False,
                    log=thread_log,
                    max_attempts=self.max_attempts,
                )
                if result.ok:
                    ok += 1
            except Exception as e:
                thread_log(f"[red]FAILED[/] {job.src}: {e}")
        thread_log(f"[bold]Done.[/] {ok}/{len(jobs)} succeeded.")

    async def action_run_mda(self) -> None:
        if not self.selected:
            self.log_msg(
                "[yellow]No files selected.[/] Highlight a supported row and press Space."
            )
            return
        try:
            provider = resolve_provider_name(cli_provider=self.provider)
            ensure_api_credentials(provider)
        except SystemExit as e:
            self.log_msg(f"[red]{e}[/]")
            return

        skill_res, err = find_skill_dir(self.skill_dir_arg, skill_id=self.skill_id)
        if err or skill_res is None:
            self.log_msg(f"[red]{err or 'Could not resolve skill dir'}[/]")
            return
        skill_dir = skill_res.path

        out_dir: Path | None = None
        in_place = False
        if self.output_mode == "in_place":
            in_place = True
        elif self.output_mode == "out_dir":
            raw = self.query_one("#out-dir", Input).value.strip()
            if not raw:
                self.log_msg(
                    "[yellow]Type an output folder in the bottom-left field (or press G).[/]"
                )
                return
            out_dir = Path(raw).expanduser().resolve()
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                self.log_msg(f"[red]Cannot create output folder:[/] {e}")
                return

        try:
            jobs = jobs_from_document_files(
                sorted(self.selected),
                out_dir=out_dir,
                in_place=in_place,
                skill_id=skill_res.skill_id,
            )
        except ValueError as e:
            self.log_msg(f"[red]{e}[/]")
            return

        self.log_msg(f"[cyan]Skill:[/] {skill_res.skill_id} ({skill_dir})")
        for j in jobs:
            self.log_msg(f"[dim]{j.src} → {j.dst}[/]")

        await asyncio.to_thread(self._run_batch_sync, skill_dir, jobs)


def run_tui(
    *,
    start: Path | None,
    skill_dir: Path | None,
    skill_id: str | None = None,
    model: str,
    max_tokens: int,
    max_attempts: int = 3,
    provider: str | None = None,
) -> int:
    from mda_cli.folder_picker import pick_folder

    folder = pick_folder(start=start)
    if folder is None:
        return 0

    MdaNavigatorApp(
        start=folder,
        skill_dir=skill_dir,
        skill_id=skill_id,
        model=model,
        max_tokens=max_tokens,
        max_attempts=max_attempts,
        provider=provider,
    ).run()
    return 0
