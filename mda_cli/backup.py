"""Backup manifests, restore apply, and optional batch checkpoints (issue #14, #34)."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mda_cli.core import Job, JobResult

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


def default_checkpoint_dir() -> Path:
    """Directory where optional pre-batch source copies are stored."""
    raw = os.environ.get("MDA_CHECKPOINT_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".mda" / "checkpoints"


def find_manifest_path(run_id: str, manifest_dir: Path | None = None) -> Path | None:
    """Resolve a manifest file by run id (with or without ``.json`` suffix)."""
    rid = run_id.removesuffix(".json")
    root = (manifest_dir or default_manifest_dir()).expanduser()
    direct = root / f"{rid}.json"
    if direct.is_file():
        return direct
    for path in list_manifest_files(root):
        try:
            data = load_manifest(path)
        except (OSError, ValueError):
            continue
        if data.get("run_id") == rid:
            return path
    return None


@dataclass(frozen=True)
class RestoreOperation:
    """One file to restore from a manifest backup_path."""

    backup_path: Path
    target_path: Path
    src: Path | None
    ok: bool
    skip_reason: str | None = None


def plan_restore_operations(data: dict[str, object]) -> list[RestoreOperation]:
    """Build restore operations from manifest entries (only rows with backup_path)."""
    ops: list[RestoreOperation] = []
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return ops
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_backup = entry.get("backup_path")
        if not raw_backup:
            continue
        backup_path = Path(str(raw_backup))
        dst_raw = entry.get("dst") or entry.get("src")
        if not dst_raw:
            ops.append(
                RestoreOperation(
                    backup_path=backup_path,
                    target_path=backup_path,
                    src=None,
                    ok=bool(entry.get("ok")),
                    skip_reason="missing dst/src in manifest entry",
                )
            )
            continue
        target = Path(str(dst_raw))
        src = Path(str(entry["src"])) if entry.get("src") else None
        ok = bool(entry.get("ok"))
        skip: str | None = None
        if not ok:
            skip = "job did not succeed"
        elif not backup_path.is_file():
            skip = f"backup missing: {backup_path}"
        ops.append(
            RestoreOperation(
                backup_path=backup_path,
                target_path=target,
                src=src,
                ok=ok,
                skip_reason=skip,
            )
        )
    return ops


def restore_from_manifest(
    manifest_path: Path,
    *,
    dry_run: bool = False,
) -> tuple[int, int, list[str], str | None]:
    """Restore all ``backup_path`` entries in one manifest.

    Returns ``(applied, skipped, messages, error)`` where ``error`` is set when
    the manifest cannot be used (missing file, no backup entries).
    """
    if not manifest_path.is_file():
        return 0, 0, [], f"manifest not found: {manifest_path}"
    try:
        data = load_manifest(manifest_path)
    except (OSError, ValueError) as e:
        return 0, 0, [], f"invalid manifest: {e}"
    ops = plan_restore_operations(data)
    if not ops:
        return 0, 0, [], "no backup_path entries in manifest"
    applied, skipped, messages = apply_restore_operations(ops, dry_run=dry_run)
    return applied, skipped, messages, None


def apply_restore_operations(
    ops: list[RestoreOperation],
    *,
    dry_run: bool = True,
) -> tuple[int, int, list[str]]:
    """Copy backup_path → target_path. Returns (applied, skipped, messages)."""
    applied = 0
    skipped = 0
    messages: list[str] = []
    for op in ops:
        if op.skip_reason:
            skipped += 1
            messages.append(f"SKIP {op.target_path}: {op.skip_reason}")
            continue
        if dry_run:
            messages.append(f"WOULD RESTORE {op.backup_path} -> {op.target_path}")
            applied += 1
            continue
        try:
            op.target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(op.backup_path, op.target_path)
        except OSError as e:
            skipped += 1
            messages.append(f"FAILED {op.target_path}: {e}")
            continue
        applied += 1
        messages.append(f"RESTORED {op.target_path} <- {op.backup_path}")
    return applied, skipped, messages


def write_batch_checkpoint(
    *,
    run_id: str,
    jobs: list[Job],
    base: Path | None = None,
    checkpoint_dir: Path | None = None,
) -> Path:
    """Copy source files to ``~/.mda/checkpoints/<run_id>/`` before a batch run."""
    root = (checkpoint_dir or default_checkpoint_dir()).expanduser() / run_id
    root.mkdir(parents=True, exist_ok=True)
    base_resolved = base.resolve() if base is not None else None
    for job in jobs:
        src = job.src.resolve()
        if base_resolved is not None:
            try:
                rel = src.relative_to(base_resolved)
            except ValueError:
                rel = Path(src.name)
        else:
            rel = Path(src.name)
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return root
