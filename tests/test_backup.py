from __future__ import annotations

import json
from pathlib import Path

from mda_cli.backup import (
    list_manifest_files,
    load_manifest,
    summarize_manifest,
    write_batch_manifest,
)
from mda_cli.cli import main
from mda_cli.core import Job, JobResult


def test_write_and_list_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MDA_MANIFEST_DIR", str(tmp_path))
    job = Job(src=Path("a.md"), dst=Path("a.md"))
    result = JobResult(
        job=job,
        ok=True,
        action="wrote",
        changed=True,
        backup_path=Path("a.md.bak"),
    )
    path = write_batch_manifest(
        run_id="20260101T120000Z",
        results=[result],
        skill_id="markdown-document-architect",
        provider="anthropic",
        target=Path("vault"),
        in_place=True,
        backup_enabled=True,
        manifest_dir=tmp_path,
    )
    assert path.is_file()
    data = load_manifest(path)
    assert data["run_id"] == "20260101T120000Z"
    assert data["job_count"] == 1
    entries = data["entries"]
    assert isinstance(entries, list)
    assert entries[0]["backup_path"] == "a.md.bak"
    listed = list_manifest_files(tmp_path)
    assert listed == [path]
    summary = summarize_manifest(data)
    assert "backups=1" in summary


def test_restore_list_empty(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MDA_MANIFEST_DIR", str(tmp_path / "empty"))
    assert main(["restore", "--list"]) == 0
    out = capsys.readouterr().out
    assert "No backup manifests" in out


def test_restore_list_shows_manifest(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MDA_MANIFEST_DIR", str(tmp_path))
    write_batch_manifest(
        run_id="20260102T000000Z",
        results=[],
        skill_id="categorize-vault-notes",
        provider=None,
        target=None,
        in_place=False,
        backup_enabled=False,
        manifest_dir=tmp_path,
    )
    assert main(["restore", "--list"]) == 0
    out = capsys.readouterr().out
    assert "20260102T000000Z" in out
