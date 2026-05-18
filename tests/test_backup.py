from __future__ import annotations

from pathlib import Path

from mda_cli.backup import (
    apply_restore_operations,
    find_manifest_path,
    list_manifest_files,
    load_manifest,
    plan_restore_operations,
    restore_from_manifest,
    summarize_manifest,
    write_batch_checkpoint,
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


def test_restore_apply_dry_run(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MDA_MANIFEST_DIR", str(tmp_path))
    src = tmp_path / "note.md"
    src.write_text("original", encoding="utf-8")
    bak = tmp_path / "note.md.bak"
    bak.write_text("backup", encoding="utf-8")
    src.write_text("changed", encoding="utf-8")
    job = Job(src=src, dst=src)
    result = JobResult(
        job=job,
        ok=True,
        action="wrote",
        changed=True,
        backup_path=bak,
    )
    write_batch_manifest(
        run_id="run_restore_test",
        results=[result],
        skill_id="markdown-document-architect",
        provider="anthropic",
        target=tmp_path,
        in_place=True,
        backup_enabled=True,
        manifest_dir=tmp_path,
    )
    assert main(["restore", "run_restore_test"]) == 0
    out = capsys.readouterr().out
    assert "WOULD RESTORE" in out
    assert src.read_text(encoding="utf-8") == "changed"


def test_restore_apply_copies_backup(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MDA_MANIFEST_DIR", str(tmp_path))
    src = tmp_path / "note.md"
    src.write_text("original", encoding="utf-8")
    bak = tmp_path / "note.md.bak"
    bak.write_text("backup", encoding="utf-8")
    src.write_text("changed", encoding="utf-8")
    job = Job(src=src, dst=src)
    result = JobResult(
        job=job,
        ok=True,
        action="wrote",
        changed=True,
        backup_path=bak,
    )
    write_batch_manifest(
        run_id="run_apply_test",
        results=[result],
        skill_id="markdown-document-architect",
        provider="anthropic",
        target=tmp_path,
        in_place=True,
        backup_enabled=True,
        manifest_dir=tmp_path,
    )
    assert main(["restore", "run_apply_test", "--apply", "--yes"]) == 0
    assert src.read_text(encoding="utf-8") == "backup"
    assert find_manifest_path("run_apply_test", tmp_path) is not None


def test_write_batch_checkpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MDA_CHECKPOINT_DIR", str(tmp_path / "ck"))
    vault = tmp_path / "vault"
    vault.mkdir()
    a = vault / "a.md"
    a.write_text("# A", encoding="utf-8")
    sub = vault / "sub"
    sub.mkdir()
    b = sub / "b.md"
    b.write_text("# B", encoding="utf-8")
    jobs = [Job(src=a, dst=a), Job(src=b, dst=b)]
    root = write_batch_checkpoint(run_id="ck1", jobs=jobs, base=vault)
    assert (root / "a.md").read_text(encoding="utf-8") == "# A"
    assert (root / "sub" / "b.md").read_text(encoding="utf-8") == "# B"


def test_plan_restore_skips_missing_backup(tmp_path: Path) -> None:
    data = {
        "entries": [
            {
                "src": "a.md",
                "dst": "a.md",
                "ok": True,
                "backup_path": str(tmp_path / "missing.bak"),
            }
        ]
    }
    ops = plan_restore_operations(data)
    assert len(ops) == 1
    assert ops[0].skip_reason is not None


def test_restore_from_manifest_applies(tmp_path: Path) -> None:
    src = tmp_path / "note.md"
    src.write_text("changed", encoding="utf-8")
    bak = tmp_path / "note.md.bak"
    bak.write_text("original", encoding="utf-8")
    job = Job(src=src, dst=src)
    result = JobResult(
        job=job,
        ok=True,
        action="wrote",
        changed=True,
        backup_path=bak,
    )
    manifest = write_batch_manifest(
        run_id="undo_manifest",
        results=[result],
        skill_id="markdown-document-architect",
        provider="anthropic",
        target=tmp_path,
        in_place=True,
        backup_enabled=True,
        manifest_dir=tmp_path,
    )
    applied, skipped, msgs, err = restore_from_manifest(manifest, dry_run=False)
    assert err is None
    assert applied == 1
    assert skipped == 0
    assert src.read_text(encoding="utf-8") == "original"
    assert any("RESTORED" in m for m in msgs)


def test_restore_from_manifest_no_backups(tmp_path: Path) -> None:
    manifest = write_batch_manifest(
        run_id="empty_backups",
        results=[],
        skill_id="markdown-document-architect",
        provider=None,
        target=None,
        in_place=False,
        backup_enabled=False,
        manifest_dir=tmp_path,
    )
    applied, skipped, msgs, err = restore_from_manifest(manifest, dry_run=False)
    assert applied == 0
    assert err == "no backup_path entries in manifest"


def test_apply_restore_operations_counts(tmp_path: Path) -> None:
    from mda_cli.backup import RestoreOperation

    bak = tmp_path / "x.bak"
    bak.write_text("old", encoding="utf-8")
    target = tmp_path / "x.md"
    target.write_text("new", encoding="utf-8")
    op = RestoreOperation(
        backup_path=bak,
        target_path=target,
        src=target,
        ok=True,
        skip_reason=None,
    )
    applied, skipped, msgs = apply_restore_operations([op], dry_run=False)
    assert applied == 1
    assert skipped == 0
    assert target.read_text(encoding="utf-8") == "old"
    assert any("RESTORED" in m for m in msgs)
