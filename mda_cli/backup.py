"""Backup manifest tracking for batch runs (issue #14 groundwork).

Each batch run with ``--backup`` and/or in-place writes can append a JSON manifest
under ``~/.mda/manifests/`` (override with ``MDA_MANIFEST_DIR``). Full
``mda restore`` apply is not implemented yet; use ``mda restore --list`` to inspect.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mda_cli.core import JobResult

MANIFEST_VERSION = 1


def default_manifest_dir() -> Path:
    """Directory where batch manifests are stored."""
    raw = os.environ.get("MDA_MANIFEST_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".mda" / "manifests"


def new_run_id() -> str:
    """UTC timestamp id for a batch run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def manifest_entry_from_result(result: JobResult) -> dict[str, object]:
    """Serialize one job result for the manifest."""
    return {
        "src": str(result.job.src),
        "dst": str(result.job.dst),
        "ok": result.ok,
        "action": result.action,
        "changed": result.changed,
        "backup_path": str(result.backup_path) if result.backup_path else None,
        "error": result.error,
    }


def write_batch_manifest(
    *,
    run_id: str,
    results: list[JobResult],
    skill_id: str,
    provider: str | None,
    target: Path | None,
    in_place: bool,
    backup_enabled: bool,
    manifest_dir: Path | None = None,
) -> Path:
    """Write a JSON manifest for a completed batch run; return its path."""
    root = (manifest_dir or default_manifest_dir()).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{run_id}.json"
    payload: dict[str, object] = {
        "version": MANIFEST_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "skill_id": skill_id,
        "provider": provider,
        "target": str(target) if target is not None else None,
        "in_place": in_place,
        "backup_enabled": backup_enabled,
        "job_count": len(results),
        "entries": [manifest_entry_from_result(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def list_manifest_files(manifest_dir: Path | None = None) -> list[Path]:
    """Return manifest JSON paths newest first."""
    root = (manifest_dir or default_manifest_dir()).expanduser()
    if not root.is_dir():
        return []
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p for p in files if p.is_file()]


def load_manifest(path: Path) -> dict[str, object]:
    """Load one manifest file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid manifest (expected object): {path}")
    return data


def summarize_manifest(data: dict[str, object]) -> str:
    """One-line summary for ``restore --list``."""
    run_id = data.get("run_id", "?")
    created = data.get("created_at", "?")
    jobs = data.get("job_count", "?")
    skill = data.get("skill_id", "?")
    backups = sum(
        1
        for e in data.get("entries", [])
        if isinstance(e, dict) and e.get("backup_path")
    )
    return f"{run_id}  {created}  skill={skill}  jobs={jobs}  backups={backups}"
