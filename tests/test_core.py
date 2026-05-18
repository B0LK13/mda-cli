from __future__ import annotations

from pathlib import Path

import pytest

from mda_cli.core import (
    DEFAULT_SKILL_ID,
    Job,
    bundled_skill_dir,
    clear_system_prompt_cache,
    collect_jobs,
    find_skill_dir,
    job_result_record,
    jobs_from_document_files,
    jobs_from_markdown_files,
    list_bundled_skills,
    list_skill_scripts,
    load_system_prompt,
    process_job,
    read_markdown_text,
    resolve_skill_id,
    resolve_skill_script,
    strip_outer_fence,
    write_output_text,
)
from mda_cli.document_io import DocumentReadError


def test_find_skill_dir_explicit_ok(skill_dir: Path) -> None:
    res, err = find_skill_dir(skill_dir)
    assert err is None
    assert res is not None
    assert res.path == skill_dir.resolve()
    assert res.source == "explicit"


def test_find_skill_dir_explicit_missing(tmp_path: Path) -> None:
    res, err = find_skill_dir(tmp_path / "nope")
    assert res is None
    assert err is not None and "SKILL.md" in err


def test_list_bundled_skills_includes_mda_and_categorize() -> None:
    ids = list_bundled_skills()
    assert DEFAULT_SKILL_ID in ids
    assert "categorize-vault-notes" in ids


def test_bundled_skill_dir_has_required_files() -> None:
    bundled = bundled_skill_dir(DEFAULT_SKILL_ID)
    assert (bundled / "SKILL.md").is_file()
    assert (bundled / "MDA-STANDARD.md").is_file()


def test_bundled_categorize_skill_has_scripts() -> None:
    bundled = bundled_skill_dir("categorize-vault-notes")
    assert (bundled / "SKILL.md").is_file()
    assert (bundled / "references" / "CATEGORIES.md").is_file()
    scripts = list_skill_scripts(bundled)
    assert "scan_vault.py" in scripts
    assert resolve_skill_script(bundled, "scan_vault") is not None


def test_find_skill_dir_uses_bundled_when_external_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("mda_cli.core.Path.home", lambda: fake_home)
    monkeypatch.delenv("MDA_SKILL_DIR", raising=False)
    monkeypatch.delenv("MDA_SKILL", raising=False)

    res, err = find_skill_dir(None)
    assert err is None
    assert res is not None
    assert res.source == "bundled"
    assert res.skill_id == DEFAULT_SKILL_ID
    assert res.path == bundled_skill_dir(DEFAULT_SKILL_ID).resolve()


def test_find_skill_dir_categorize_bundled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr("mda_cli.core.Path.home", lambda: fake_home)
    monkeypatch.delenv("MDA_SKILL_DIR", raising=False)

    res, err = find_skill_dir(None, skill_id="categorize-vault-notes")
    assert err is None
    assert res is not None
    assert res.skill_id == "categorize-vault-notes"
    assert res.source == "bundled"
    assert (res.path / "SKILL.md").is_file()


def test_resolve_skill_id_prefers_cli_then_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MDA_SKILL", "categorize-vault-notes")
    assert resolve_skill_id(cli_skill="markdown-document-architect") == (
        "markdown-document-architect"
    )
    assert resolve_skill_id(cli_skill=None) == "categorize-vault-notes"


def test_load_system_prompt_from_bundled_skill() -> None:
    bundled = bundled_skill_dir(DEFAULT_SKILL_ID)
    clear_system_prompt_cache()
    out = load_system_prompt(bundled)
    assert "Markdown Document Architect" in out
    assert "MDA-STANDARD.md" in out or "governing standard" in out.lower()


def test_load_system_prompt_from_categorize_bundled() -> None:
    bundled = bundled_skill_dir("categorize-vault-notes")
    clear_system_prompt_cache()
    out = load_system_prompt(bundled)
    assert "Categorize Vault Notes" in out
    assert "CATEGORIES" in out or "taxonomy" in out.lower()


def test_strip_outer_fence_four_ticks() -> None:
    raw = "````markdown\n# 1. Hi\n\nBody\n````\n"
    out = strip_outer_fence(raw)
    assert out.strip() == "# 1. Hi\n\nBody"


def test_strip_outer_fence_passthrough() -> None:
    raw = "# Title\n\nok\n"
    assert strip_outer_fence(raw).strip() == raw.strip()


def test_jobs_from_markdown_sibling(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    a.write_text("# A", encoding="utf-8")
    jobs = jobs_from_markdown_files([a], out_dir=None, in_place=False)
    assert len(jobs) == 1
    assert jobs[0].dst == a.with_name("a.restructured.md")


def test_jobs_from_markdown_in_place(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    a.write_text("# A", encoding="utf-8")
    jobs = jobs_from_markdown_files([a], out_dir=None, in_place=True)
    assert jobs[0].dst == a.resolve()


def test_jobs_from_markdown_out_dir_collision(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    a1 = d1 / "same.md"
    a2 = d2 / "same.md"
    a1.write_text("# 1", encoding="utf-8")
    a2.write_text("# 2", encoding="utf-8")
    jobs = jobs_from_markdown_files([a1, a2], out_dir=out, in_place=False)
    dsts = {j.dst for j in jobs}
    assert len(dsts) == 2
    assert out / "same.md" in dsts
    assert out / "same_2.md" in dsts


def test_jobs_from_document_accepts_txt(tmp_path: Path) -> None:
    t = tmp_path / "x.txt"
    t.write_text("x", encoding="utf-8")
    jobs = jobs_from_document_files([t], out_dir=None, in_place=False)
    assert jobs[0].dst == t.with_name("x.restructured.md")


def test_jobs_from_document_rejects_unknown_extension(tmp_path: Path) -> None:
    t = tmp_path / "x.xyz"
    t.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        jobs_from_document_files([t], out_dir=None, in_place=False)


def test_jobs_from_markdown_alias(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    a.write_text("# A", encoding="utf-8")
    assert jobs_from_markdown_files([a], out_dir=None, in_place=False) == jobs_from_document_files(
        [a], out_dir=None, in_place=False
    )


def test_collect_jobs_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B", encoding="utf-8")
    (tmp_path / "c.txt").write_text("C", encoding="utf-8")
    jobs = collect_jobs(tmp_path, recursive=False, out_dir=None, in_place=False)
    assert len(jobs) == 3


def test_collect_jobs_skips_restructured(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "a.restructured.md").write_text("# AR", encoding="utf-8")
    jobs = collect_jobs(tmp_path, recursive=False, out_dir=None, in_place=False)
    assert len(jobs) == 1


def test_collect_jobs_max_files_guard(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B", encoding="utf-8")
    jobs = collect_jobs(
        tmp_path, recursive=False, out_dir=None, in_place=False, max_files=10
    )
    assert len(jobs) == 2
    with pytest.raises(SystemExit, match="max-files"):
        collect_jobs(
            tmp_path, recursive=False, out_dir=None, in_place=False, max_files=1
        )


def test_load_system_prompt_cache_reads_once(
    skill_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pathlib import Path as PathCls

    calls = {"n": 0}
    real_read = PathCls.read_bytes

    def counting_read(self: PathCls) -> bytes:
        if self.name in ("SKILL.md", "MDA-STANDARD.md"):
            calls["n"] += 1
        return real_read(self)

    monkeypatch.setattr(PathCls, "read_bytes", counting_read)
    clear_system_prompt_cache()
    load_system_prompt(skill_dir)
    load_system_prompt(skill_dir)
    assert calls["n"] == 2


def test_load_system_prompt_utf16_le_skill(skill_dir: Path) -> None:
    """Notepad-style UTF-16 LE + BOM must not crash prompt load."""
    body = "---\nname: markdown-document-architect\n---\n# Skill\n"
    (skill_dir / "SKILL.md").write_bytes(b"\xff\xfe" + body.encode("utf-16-le"))
    (skill_dir / "MDA-STANDARD.md").write_bytes(b"\xff\xfe" + "# Std\n".encode("utf-16-le"))
    clear_system_prompt_cache()
    out = load_system_prompt(skill_dir)
    assert "# Skill" in out
    assert "# Std" in out


def test_read_markdown_text_utf8_bom(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_bytes(b"\xef\xbb\xbf# Hello\n")
    assert read_markdown_text(p).startswith("# Hello")


def test_write_output_text_creates_backup(tmp_path: Path) -> None:
    dst = tmp_path / "doc.md"
    dst.write_text("old\n", encoding="utf-8")

    changed, backup_path, bytes_out = write_output_text(dst, "new\n", create_backup=True)

    assert changed is True
    assert bytes_out == len(b"new\n")
    assert backup_path is not None
    assert backup_path.read_text(encoding="utf-8") == "old\n"
    assert dst.read_text(encoding="utf-8") == "new\n"


def test_write_output_text_unchanged_skips_rewrite(tmp_path: Path) -> None:
    dst = tmp_path / "doc.md"
    dst.write_text("same\n", encoding="utf-8")

    changed, backup_path, bytes_out = write_output_text(dst, "same\n", create_backup=True)

    assert changed is False
    assert backup_path is None
    assert bytes_out == len(b"same\n")


def test_process_job_returns_metadata_and_backup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src = tmp_path / "doc.md"
    src.write_text("# Title\n", encoding="utf-8")
    job = Job(src=src, dst=src)

    monkeypatch.setattr("mda_cli.core.restructure", lambda *args, **kwargs: "# Changed\n")

    result = process_job(
        job,
        object(),
        model="claude-test",
        max_tokens=32,
        system="sys",
        progress=False,
        backup_in_place=True,
    )

    record = job_result_record(result, provider="anthropic")

    assert result.ok is True
    assert result.action == "wrote"
    assert result.changed is True
    assert result.backup_path is not None
    assert result.backup_path.read_text(encoding="utf-8") == "# Title\n"
    assert src.read_text(encoding="utf-8") == "# Changed\n"
    assert record["provider"] == "anthropic"
    assert record["backup_path"] == str(result.backup_path)


def test_process_job_document_read_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"%PDF")
    job = Job(src=src, dst=src.with_name("doc.restructured.md"))

    def fail_read(path: Path) -> str:
        raise DocumentReadError("PDF support requires the pdf extra")

    monkeypatch.setattr("mda_cli.core.read_document_text", fail_read)

    result = process_job(
        job,
        object(),
        model="claude-test",
        max_tokens=32,
        system="sys",
        progress=False,
    )

    assert result.ok is False
    assert result.action == "failed"
    assert "pdf extra" in (result.error or "")


def test_process_job_unchanged_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    src = tmp_path / "doc.md"
    src.write_text("# Title\n", encoding="utf-8")
    job = Job(src=src, dst=src)

    monkeypatch.setattr("mda_cli.core.restructure", lambda *args, **kwargs: "# Title\n")

    result = process_job(
        job,
        object(),
        model="claude-test",
        max_tokens=32,
        system="sys",
        progress=False,
        backup_in_place=True,
    )

    assert result.ok is True
    assert result.action == "unchanged"
    assert result.changed is False
    assert result.backup_path is None
