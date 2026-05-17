"""User preferences (last folder, etc.) stored outside the package."""

from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_VERSION = 1


def config_path() -> Path:
    """Return the per-user config file path."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "mda-cli" / "config.json"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "mda-cli" / "config.json"
    return Path.home() / ".config" / "mda-cli" / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _CONFIG_VERSION, **data}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_last_folder() -> Path | None:
    raw = load_config().get("last_folder")
    if not raw or not isinstance(raw, str):
        return None
    p = Path(raw).expanduser()
    if p.is_dir():
        return p.resolve()
    return None


def set_last_folder(folder: Path) -> None:
    data = load_config()
    data["last_folder"] = str(folder.resolve())
    save_config(data)


def resolve_initial_folder(start: Path | None) -> Path:
    """Pick the folder-picker starting directory."""
    if start is not None:
        p = start.expanduser()
        if p.is_file():
            p = p.parent
        if p.is_dir():
            return p.resolve()
    last = get_last_folder()
    if last is not None:
        return last
    return Path.home().resolve()
