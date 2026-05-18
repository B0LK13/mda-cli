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
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, RichLog, TextArea

from mda_cli.backup import (
    new_run_id,
    restore_from_manifest,
    write_batch_manifest,
)
from mda_cli.core import (
    Job,
    JobResult,
    find_skill_dir,
    jobs_from_document_files,
    list_bundled_skills,
    load_system_prompt,
)
from mda_cli.document_io import (
    DocumentReadError,
    is_supported_extension,
    read_document_text,
    supported_extensions,
)
from mda_cli.preflight import build_batch_preflight, format_preflight_message
from mda_cli.preview import (
    DEFAULT_PREVIEW_MAX_CHARS,
    format_preview_error_banner,
    format_preview_metadata,
    truncate_preview_text,
)
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


class BatchPreflightScreen(ModalScreen[bool]):
    """Confirm batch run after showing file count and token/size warnings."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("n", "cancel", "Cancel", show=False),
        Binding("y", "continue_run", "Continue", show=False),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Label("Batch pre-flight", id="preflight-title")
        yield Label(self.message, id="preflight-body")
        with Horizontal(id="preflight-actions"):
            yield Button("Continue", variant="primary", id="preflight-continue")
            yield Button("Cancel", id="preflight-cancel")

    def on_mount(self) -> None:
        self.query_one("#preflight-continue", Button).focus()

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_continue_run(self) -> None:
        self.dismiss(True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "preflight-continue":
            self.dismiss(True)
        elif event.button.id == "preflight-cancel":
            self.dismiss(False)


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
    """File browser + live document preview + log. Select with Space, run with P."""

    CSS = """
    #main { height: 100%; }
    #left { width: 38%; height: 100%; border: heavy $primary; padding: 0 1; }
    #preview-col { width: 32%; height: 100%; border: heavy $primary; padding: 0 1; }
    #preview-col.hidden { display: none; }
    #right { width: 1fr; height: 100%; border: heavy $primary; padding: 0 1; }
    #listing { height: 1fr; min-height: 10; }
    #preview-meta { height: auto; max-height: 3; text-style: bold; }
    #preview-meta.error { color: $error; }
    #preview-body { height: 1fr; min-height: 8; }
    #log { height: 1fr; min-height: 10; background: $surface; }
    #api-status { height: auto; max-height: 3; color: $error; }
    Label { margin: 0 0 1 0; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit"),
        Binding("o", "cycle_output", "Output mode", show=True),
        Binding("i", "toggle_preview", "Preview", show=True),
        Binding("p", "run_mda", "Run MDA", show=True),
        Binding("u", "undo_last", "Undo batch", show=True),
        Binding("g", "focus_out_dir", "Out folder", show=True),
        Binding("h", "go_home", "Home", show=True),
        Binding("ctrl+j", "jump_path", "Jump", show=True),
        Binding("f", "filter_listing", "Filter", show=True),
        Binding("v", "toggle_hidden", "Hidden", show=True),
        Binding("a", "select_recursive_supported", "Recursive all", show=True),
        Binding("s", "cycle_skill", "Skill", show=True),
        Binding("shift+v", "scan_vault", "Vault scan", show=True),
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
        self._row_key_meta: dict[object, tuple[Path | None, str]] = {}
        self._selectable_row_keys: dict[Path, object] = {}
        self._row_key_seq = 0
        self._col_name_key: object | None = None
        self.name_filter: str = ""
        self.show_hidden: bool = False
        self.show_preview_pane: bool = True
        self._preview_cache: tuple[Path, float, str, str | None] | None = None
        self._preview_timer = None
        self._preview_load_id: int = 0
        self._last_api_error: str | None = None
        self._last_api_provider: str | None = None
        self._last_manifest_path: Path | None = None
        self._recursive_last_select: bool = False
        bundled = list_bundled_skills()
        self._skill_cycle_ids: list[str] = bundled if bundled else []
        if self.skill_id and self.skill_id not in self._skill_cycle_ids:
            self._skill_cycle_ids = [self.skill_id, *self._skill_cycle_ids]
        elif not self._skill_cycle_ids and self.skill_id:
            self._skill_cycle_ids = [self.skill_id]
        self._skill_cycle_index = 0
        if self.skill_id and self.skill_id in self._skill_cycle_ids:
            self._skill_cycle_index = self._skill_cycle_ids.index(self.skill_id)

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
                yield Label(id="skill-label")
                yield Label(id="filter-label")
                yield Input(
                    placeholder="Output folder when mode is out_dir (absolute or ~)",
                    id="out-dir",
                )
            with Vertical(id="preview-col"):
                yield Label("Preview", id="preview-title")
                yield Label("", id="preview-meta")
                yield TextArea("", id="preview-body", read_only=True)
            with Vertical(id="right"):
                yield Label("", id="api-status")
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#preview-body", TextArea).can_focus = False
        table = self.query_one("#listing", DataTable)
        name_k, _kind_k = table.add_columns(("Name", "name"), ("Kind", "kind"))
        self._col_name_key = name_k
        self.refresh_listing()
        exts = ", ".join(supported_extensions())
        self.log_msg(
            f"[dim]Supported:[/] {exts}\n"
            "[dim]Space[/] toggle file  [dim]Enter[/] open dir  [dim]Backspace[/] up  "
            "[dim]ctrl+j[/] jump  [dim]f[/] filter  [dim]v[/] hidden  "
            "[dim]a[/] recursive select  [dim]S[/] skill  [dim]Shift+V[/] vault scan  "
            "[dim]k/j[/] up/down  [dim]I[/] preview  [dim]O[/] output  [dim]P[/] run  "
            "[dim]U[/] undo last batch  [dim]G[/] out-folder  [dim]H[/] home"
        )
        self._apply_preview_pane_visibility()

    def _listing_table(self) -> DataTable:
        return self.query_one("#listing", DataTable)

    def _listing_accepts_browser_keys(self) -> DataTable | None:
        """Return the listing when browser keys should apply (not the out-dir field)."""
        focused = self.focused
        if focused is None:
            return None
        if focused.id == "out-dir":
            return None
        listing = self._listing_table()
        if focused is listing:
            return listing
        label_ids = {
            "path-label",
            "selection-label",
            "mode-label",
            "skill-label",
            "filter-label",
        }
        if focused.id in label_ids:
            return listing
        return None

    def _focus_listing_for_browser_keys(self) -> DataTable:
        listing = self._listing_table()
        if self.focused is not listing:
            listing.focus()
        return listing

    def on_key(self, event: events.Key) -> None:
        """Route navigation keys to the file listing; DataTable swallows them otherwise."""
        listing = self._listing_accepts_browser_keys()
        if listing is None:
            return

        if event.key == "enter":
            self._focus_listing_for_browser_keys()
            self.action_activate()
            event.prevent_default()
            event.stop()
        elif event.key == "space":
            self._focus_listing_for_browser_keys()
            self.action_toggle_select()
            event.prevent_default()
            event.stop()
        elif event.key == "backspace":
            self._focus_listing_for_browser_keys()
            self.action_go_up()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            listing.action_cursor_up()
            event.prevent_default()
            event.stop()
            self._schedule_preview_update()
        elif event.key == "j":
            listing.action_cursor_down()
            event.prevent_default()
            event.stop()
            self._schedule_preview_update()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.control.id != "listing":
            return
        self._schedule_preview_update()

    def log_msg(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def _set_api_error(self, message: str | None, *, provider: str | None = None) -> None:
        self._last_api_error = message
        self._last_api_provider = provider
        label = self.query_one("#api-status", Label)
        if message:
            short = message if len(message) <= 120 else message[:117] + "..."
            if provider:
                label.update(f"Last API error ({provider}): {short}")
            else:
                label.update(f"Last API error: {short}")
        else:
            label.update("")

    def _set_api_provider_ok(self, provider: str) -> None:
        self._last_api_error = None
        self._last_api_provider = provider
        label = self.query_one("#api-status", Label)
        label.update(f"Provider: {provider}")

    def _set_batch_progress(self, current: int, total: int, path: Path) -> None:
        self.query_one("#selection-label", Label).update(
            f"Running batch {current}/{total}: {path.name}"
        )

    def _mode_label(self) -> str:
        if self.output_mode == "sibling":
            return "Output mode: sibling (*.restructured.md next to source)"
        if self.output_mode == "in_place":
            return "Output mode: in-place (overwrite source)"
        return "Output mode: out_dir (use input below)"

    def _skill_label(self) -> str:
        sid = self.skill_id or "(default)"
        if self._skill_cycle_ids:
            idx = self._skill_cycle_index + 1
            total = len(self._skill_cycle_ids)
            return f"Skill: {sid} ({idx}/{total}, press S to cycle)"
        return f"Skill: {sid}"

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

        preserve_path = self._highlighted_preview_path()

        table = self._listing_table()
        table.clear()
        self._rows.clear()
        self._row_key_meta.clear()
        self._selectable_row_keys.clear()

        self.query_one("#path-label", Label).update(str(self.cwd))
        self.query_one("#mode-label", Label).update(self._mode_label())
        self.query_one("#skill-label", Label).update(self._skill_label())
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

        up_key = self._alloc_row_key()
        table.add_row("..", "parent", key=up_key)
        self._rows.append((self.cwd.parent, "up"))
        self._row_key_meta[up_key] = (self.cwd.parent, "up")

        for p in dirs:
            dir_key = self._alloc_row_key()
            table.add_row(f"{p.name}/", "dir", key=dir_key)
            self._rows.append((p, "dir"))
            self._row_key_meta[dir_key] = (p, "dir")

        for p in files:
            selectable = is_supported_extension(p)
            kind = p.suffix.lower().lstrip(".") or "file"
            if not selectable:
                kind = "file"
            pr = p.resolve()
            mark = "* " if pr in self.selected else ""
            file_key = self._alloc_row_key()
            table.add_row(f"{mark}{p.name}", kind, key=file_key)
            row_kind = kind if selectable else "file"
            self._rows.append((pr, row_kind))
            self._row_key_meta[file_key] = (pr, row_kind)
            if selectable:
                self._selectable_row_keys[pr] = file_key

        if prev_focus_id == "out-dir":
            self.query_one("#out-dir", Input).focus()
        else:
            table.focus()
        self._restore_listing_cursor(preserve_path)
        self.call_after_refresh(self._schedule_preview_update)

    def _restore_listing_cursor(self, path: Path | None) -> None:
        if path is None:
            return
        table = self._listing_table()
        row_key = self._selectable_row_keys.get(path.resolve())
        if row_key is None:
            return
        try:
            row_index = table.get_row_index(row_key)
        except Exception:
            return
        table.move_cursor(row=row_index, column=0)

    def _apply_preview_pane_visibility(self) -> None:
        col = self.query_one("#preview-col")
        if self.show_preview_pane:
            col.remove_class("hidden")
        else:
            col.add_class("hidden")

    def action_toggle_preview(self) -> None:
        self.show_preview_pane = not self.show_preview_pane
        self._apply_preview_pane_visibility()
        if self.show_preview_pane:
            self._schedule_preview_update()
        else:
            self._clear_preview_pane()

    def _clear_preview_pane(self) -> None:
        self.query_one("#preview-meta", Label).update("")
        self.query_one("#preview-body", TextArea).load_text("")

    def _meta_for_row_key(self, row_key: object) -> tuple[Path | None, str] | None:
        return self._row_key_meta.get(row_key)

    def _cursor_row_meta(self) -> tuple[Path | None, str] | None:
        table = self._listing_table()
        coord = table.cursor_coordinate
        if coord is None:
            return None
        try:
            cell_key = table.coordinate_to_cell_key(coord)
        except Exception:
            row = coord.row
            if row < 0 or row >= len(self._rows):
                return None
            return self._rows[row]
        return self._row_key_meta.get(cell_key.row_key)

    def _preview_path_from_meta(
        self, meta: tuple[Path | None, str] | None
    ) -> Path | None:
        if meta is None:
            return None
        path, kind = meta
        if path is None or kind in ("up", "dir", "parent"):
            return None
        if not is_supported_extension(path):
            return None
        return path

    def _highlighted_preview_path(self) -> Path | None:
        return self._preview_path_from_meta(self._cursor_row_meta())

    def _schedule_preview_update(self) -> None:
        if not self.show_preview_pane:
            return
        if self._preview_timer is not None:
            self._preview_timer.stop()
        self._preview_timer = self.set_timer(0.15, self._on_preview_debounce)

    def _on_preview_debounce(self) -> None:
        self._preview_timer = None
        path = self._highlighted_preview_path()
        if path is None:
            self._preview_load_id += 1
            self._clear_preview_pane()
            return
        self._start_preview_load(path)

    def _start_preview_load(self, path: Path) -> None:
        self._preview_load_id += 1
        load_id = self._preview_load_id
        try:
            mtime = path.stat().st_mtime
        except OSError as e:
            self._render_preview(path, "", f"Cannot read file: {e}", truncated=False)
            return
        cached = self._preview_cache
        if cached is not None and cached[0] == path and cached[1] == mtime:
            body, truncated = truncate_preview_text(
                cached[2], max_chars=DEFAULT_PREVIEW_MAX_CHARS
            )
            self._render_preview(path, body, cached[3], truncated=truncated)
            return
        self.query_one("#preview-meta", Label).update(format_preview_metadata(path))
        self.query_one("#preview-body", TextArea).load_text("Loading…")
        self._load_preview_worker(path, load_id, mtime)

    @work(exclusive=True)
    async def _load_preview_worker(self, path: Path, load_id: int, mtime: float) -> None:
        try:
            raw = await asyncio.to_thread(read_document_text, path)
            err: str | None = None
        except DocumentReadError as e:
            raw, err = "", str(e)
        except OSError as e:
            raw, err = "", f"Cannot read file: {e}"
        if load_id != self._preview_load_id:
            return
        self._preview_cache = (path, mtime, raw, err)
        truncated = False
        body = raw
        if err is None:
            body, truncated = truncate_preview_text(raw, max_chars=DEFAULT_PREVIEW_MAX_CHARS)
        self._render_preview(path, body, err, truncated=truncated)

    def _render_preview(
        self,
        path: Path,
        body: str,
        error: str | None,
        *,
        truncated: bool,
    ) -> None:
        meta_label = self.query_one("#preview-meta", Label)
        meta = format_preview_metadata(path, error=error)
        if error:
            meta_label.add_class("error")
            meta_label.update(f"[red]{meta}[/]")
        else:
            meta_label.remove_class("error")
            meta_label.update(meta)
        if error:
            text = format_preview_error_banner(error)
            if body:
                text = f"{text}\n\n--- partial content ---\n{body}"
        elif body == "":
            text = "(empty)"
        else:
            text = body
        if truncated:
            text = f"{text}\n\n… truncated"
        self.query_one("#preview-body", TextArea).load_text(text)

    def _sync_selectable_row_star(self, path: Path) -> None:
        if self._col_name_key is None:
            return
        rk = self._selectable_row_keys.get(path)
        if rk is None:
            return
        table = self._listing_table()
        mark = "* " if path in self.selected else ""
        table.update_cell(rk, self._col_name_key, f"{mark}{path.name}")

    def _cursor_row_index(self) -> int | None:
        table = self._listing_table()
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
        self._recursive_last_select = True
        self.selected.update(found)
        self.refresh_listing()

    def action_activate(self) -> None:
        meta = self._cursor_row_meta()
        if meta is None:
            return
        path, kind = meta
        if path is None:
            return
        if kind == "up":
            self.cwd = path.resolve()
            self.refresh_listing()
        elif kind == "dir":
            self.cwd = path.resolve()
            self.refresh_listing()

    def action_toggle_select(self) -> None:
        meta = self._cursor_row_meta()
        if meta is None:
            return
        path, _kind = meta
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

    def action_cycle_skill(self) -> None:
        if not self._skill_cycle_ids:
            self.log_msg("[yellow]No bundled skills to cycle.[/]")
            return
        self._skill_cycle_index = (self._skill_cycle_index + 1) % len(self._skill_cycle_ids)
        self.skill_id = self._skill_cycle_ids[self._skill_cycle_index]
        self.query_one("#skill-label", Label).update(self._skill_label())
        self.log_msg(f"[cyan]Skill set to[/] {self.skill_id}")

    @work
    async def action_scan_vault(self) -> None:
        """Run categorize-vault-notes ``scan_vault`` on the current folder."""
        import io
        import sys

        from mda_cli.cli import run_skill_script

        vault = self.cwd
        self.log_msg(f"[cyan]Vault scan[/] {vault} (recursive)…")

        def run_scan() -> int:
            buf = io.StringIO()
            old_out = sys.stdout
            sys.stdout = buf
            try:
                code = run_skill_script(
                    "scan_vault",
                    [str(vault), "--recursive"],
                    skill_dir_arg=None,
                    skill_id="categorize-vault-notes",
                    list_only=False,
                )
            finally:
                sys.stdout = old_out
            return code, buf.getvalue()

        code, output = await asyncio.to_thread(run_scan)
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]
        preview = lines[:40]
        for line in preview:
            self.log_msg(f"[dim]{line}[/]")
        if len(lines) > len(preview):
            self.log_msg(f"[dim]… {len(lines) - len(preview)} more line(s)[/]")
        if code != 0:
            self.log_msg("[red]Vault scan failed.[/]")
        else:
            self.log_msg("[green]Vault scan complete.[/]")

    def action_focus_out_dir(self) -> None:
        self.query_one("#out-dir", Input).focus()

    def _run_batch_sync(
        self,
        skill_dir: Path,
        jobs: list[Job],
        *,
        backup_in_place: bool,
        skill_id: str,
    ) -> tuple[list[JobResult], Path]:
        def thread_log(msg: str) -> None:
            self.call_from_thread(self.log_msg, msg)

        system = load_system_prompt(skill_dir)
        client, ctx = build_restructure_client(
            cli_provider=self.provider,
            model=self.model,
            max_tokens=self.max_tokens,
        )
        results: list[JobResult] = []
        total = len(jobs)
        self.call_from_thread(self._set_api_error, None)
        for index, job in enumerate(jobs, start=1):
            self.call_from_thread(self._set_batch_progress, index, total, job.src)
            thread_log(f"[cyan]Batch {index}/{total}:[/] {job.src.name}")
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
                    backup_in_place=backup_in_place,
                )
                results.append(result)
                if result.used_openrouter_fallback:
                    thread_log(
                        f"[green]Used OpenRouter fallback for {job.src.name}[/]"
                    )
                    self.call_from_thread(
                        self._set_api_provider_ok,
                        result.provider_used or "openrouter",
                    )
                if not result.ok:
                    err = result.error or "processing failed"
                    api_provider = result.provider_used or ctx.provider
                    if err and "OpenRouter retry failed:" in err:
                        api_provider = "anthropic+openrouter"
                    self.call_from_thread(
                        self._set_api_error,
                        err,
                        provider=api_provider,
                    )
                    thread_log(f"[red]FAILED[/] {job.src}: {err}")
            except Exception as e:
                err = str(e)
                self.call_from_thread(
                    self._set_api_error,
                    err,
                    provider=ctx.provider,
                )
                thread_log(f"[red]FAILED[/] {job.src}: {e}")
                results.append(
                    JobResult(job=job, ok=False, action="failed", error=err),
                )
        self.call_from_thread(
            self.query_one("#selection-label", Label).update,
            self._selection_label(),
        )
        ok = sum(1 for r in results if r.ok)
        thread_log(f"[bold]Done.[/] {ok}/{total} succeeded.")
        run_id = new_run_id()
        manifest_path = write_batch_manifest(
            run_id=run_id,
            results=results,
            skill_id=skill_id,
            provider=ctx.provider,
            target=self.cwd,
            in_place=backup_in_place,
            backup_enabled=backup_in_place,
        )
        thread_log(f"[dim]Manifest:[/] {manifest_path}")
        return results, manifest_path

    def _output_mode_label(self) -> str:
        if self.output_mode == "sibling":
            return "sibling (*.restructured.md)"
        if self.output_mode == "in_place":
            return "in-place (overwrite source)"
        return "out_dir"

    @work
    async def action_undo_last(self) -> None:
        manifest_path = self._last_manifest_path
        if manifest_path is None or not manifest_path.is_file():
            self.log_msg(
                "[yellow]Nothing to undo.[/] Run a batch with **P** first "
                "(in-place mode keeps backups for undo)."
            )
            return

        def do_restore() -> tuple[int, int, list[str], str | None]:
            return restore_from_manifest(manifest_path, dry_run=False)

        applied, skipped, messages, error = await asyncio.to_thread(do_restore)
        if error:
            self.log_msg(f"[red]Undo failed:[/] {error}")
            return
        for line in messages[:20]:
            self.log_msg(f"[dim]{line}[/]")
        if len(messages) > 20:
            self.log_msg(f"[dim]… {len(messages) - 20} more line(s)[/]")
        self.log_msg(
            f"[green]Undo complete.[/] Restored {applied} file(s); skipped {skipped}."
        )

    @work
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

        preflight = build_batch_preflight(
            jobs,
            max_tokens=self.max_tokens,
            output_mode=self._output_mode_label(),
        )
        preflight_body = format_preflight_message(preflight)
        if self._recursive_last_select:
            preflight_body = (
                f"Recursive selection under: {self.cwd}\n\n{preflight_body}"
            )
        confirmed = await self.push_screen_wait(BatchPreflightScreen(preflight_body))
        if not confirmed:
            self.log_msg("[yellow]Batch cancelled.[/]")
            return

        self.log_msg(f"[cyan]Skill:[/] {skill_res.skill_id} ({skill_dir})")
        for j in jobs:
            self.log_msg(f"[dim]{j.src} → {j.dst}[/]")

        backup_in_place = in_place
        _results, manifest_path = await asyncio.to_thread(
            self._run_batch_sync,
            skill_dir,
            jobs,
            backup_in_place=backup_in_place,
            skill_id=skill_res.skill_id,
        )
        self._last_manifest_path = manifest_path


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
