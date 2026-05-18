"""Argument parsing and entry point for the `mda` CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from mda_cli import __version__
from mda_cli.backup import (
    apply_restore_operations,
    find_manifest_path,
    list_manifest_files,
    load_manifest,
    new_run_id,
    plan_restore_operations,
    summarize_manifest,
    write_batch_checkpoint,
    write_batch_manifest,
)
from mda_cli.core import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SKILL_ID,
    JobResult,
    collect_jobs,
    find_skill_dir,
    job_result_record,
    list_bundled_skills,
    list_skill_scripts,
    load_system_prompt,
    print_json_line,
    resolve_skill_dir,
    resolve_skill_id,
    resolve_skill_script,
    warn_large_inputs,
)
from mda_cli.providers import (
    build_restructure_client,
    ensure_api_credentials,
    friendly_api_message,
    process_job_with_provider,
    provider_check_lines,
    resolve_provider_name,
)


def run_restore_list() -> int:
    """List backup manifests written by prior batch runs."""
    paths = list_manifest_files()
    if not paths:
        print("No backup manifests found (batch runs write to ~/.mda/manifests/).")
        return 0
    for path in paths:
        try:
            data = load_manifest(path)
            print(f"{path.name}\t{summarize_manifest(data)}")
        except (OSError, ValueError) as e:
            print(f"{path.name}\tERROR: {e}", file=sys.stderr)
    print(
        "\nRestore: mda restore <run_id> [--apply] [--yes]  (dry-run without --apply)",
        file=sys.stderr,
    )
    return 0


def run_restore_apply(
    run_id: str,
    *,
    apply: bool,
    yes: bool,
) -> int:
    """Restore files from manifest backup_path entries for one run."""
    path = find_manifest_path(run_id)
    if path is None:
        print(f"ERROR: no manifest for run id {run_id!r}", file=sys.stderr)
        return 2
    try:
        data = load_manifest(path)
    except (OSError, ValueError) as e:
        print(f"ERROR: {path}: {e}", file=sys.stderr)
        return 2
    ops = plan_restore_operations(data)
    if not ops:
        print(f"No backup_path entries in manifest {path.name}.")
        return 0
    dry_run = not apply
    if apply and not yes:
        restorable = sum(1 for o in ops if not o.skip_reason)
        print(
            f"About to restore {restorable} file(s) from run {data.get('run_id', run_id)}.",
            file=sys.stderr,
        )
        print("Re-run with --yes to confirm.", file=sys.stderr)
        dry_run = True
    applied, skipped, messages = apply_restore_operations(ops, dry_run=dry_run)
    for line in messages:
        print(line)
    label = "would restore" if dry_run else "restored"
    print(f"\n{label}: {applied}; skipped: {skipped}", file=sys.stderr)
    if apply and not yes:
        return 2
    return 0 if skipped == 0 or applied > 0 else 1


def run_vault_scan(script_args: list[str]) -> int:
    """Alias for ``mda script scan_vault`` with categorize-vault-notes skill."""
    return run_skill_script(
        "scan_vault",
        script_args,
        skill_dir_arg=None,
        skill_id="categorize-vault-notes",
        list_only=False,
    )


def run_check(
    skill_dir_arg: Path | None,
    *,
    cli_provider: str | None = None,
    skill_id: str | None = None,
) -> int:
    """Verify Python import and skill resolution (doctor / --check)."""
    print(f"Python executable: {sys.executable}")
    try:
        import mda_cli as pkg
    except ImportError as e:
        print(f"ERROR: cannot import mda_cli: {e}", file=sys.stderr)
        return 1
    print(f"mda_cli package: {pkg.__file__}")
    print(f"mda-cli version: {__version__}")

    bundled = list_bundled_skills()
    print(f"Bundled skills: {', '.join(bundled) if bundled else '(none)'}")
    active_id = resolve_skill_id(cli_skill=skill_id)
    print(f"Active skill id: {active_id}")

    res, err = find_skill_dir(skill_dir_arg, skill_id=skill_id)
    if err or res is None:
        print(err or "ERROR: skill dir not found", file=sys.stderr)
        return 1
    print(f"Skill directory: {res.path}")
    print(f"Skill source: {res.source}")
    scripts = list_skill_scripts(res.path)
    if scripts:
        print(f"Skill scripts: {', '.join(scripts)}")
    for line in provider_check_lines(cli_provider=cli_provider):
        print(line)
    print("Check OK.")
    return 0


def run_skill_script(
    script_name: str | None,
    script_args: list[str],
    *,
    skill_dir_arg: Path | None,
    skill_id: str | None,
    list_only: bool,
) -> int:
    """Run ``scripts/<name>.py`` from the resolved skill directory."""
    res, err = find_skill_dir(skill_dir_arg, skill_id=skill_id)
    if err or res is None:
        print(err or "ERROR: skill dir not found", file=sys.stderr)
        return 1

    available = list_skill_scripts(res.path)
    if list_only or script_name is None:
        if not available:
            print(f"No scripts in {res.path / 'scripts'}")
            return 0
        for name in available:
            print(name)
        return 0

    script_path = resolve_skill_script(res.path, script_name)
    if script_path is None:
        print(
            f"ERROR: script {script_name!r} not found under {res.path / 'scripts'}",
            file=sys.stderr,
        )
        if available:
            print(f"Available: {', '.join(available)}", file=sys.stderr)
        return 1

    import runpy

    argv = [str(script_path), *script_args]
    print(f"Running: {sys.executable} {' '.join(argv)}", file=sys.stderr)
    sys.argv = argv
    try:
        runpy.run_path(str(script_path), run_name="__main__")
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mda",
        description=(
            "Restructure documents (Markdown, PDF, DOCX, TXT, …) using bundled skills "
            "(SKILL.md + standards) via the Anthropic or OpenRouter API."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verify this environment: Python path, mda_cli import, and skill directory "
            "(same resolution as a normal run). Exits 0 on success."
        ),
    )
    p.add_argument(
        "target",
        nargs="?",
        type=Path,
        default=None,
        help=(
            "Supported file or directory (.md, .pdf, .docx, .doc, .txt) for batch mode. "
            "Omit to open the interactive UI, or pass with --tui as the folder-picker start path."
        ),
    )
    p.add_argument(
        "--tui",
        "-T",
        action="store_true",
        help=(
            "Open the interactive terminal UI (folder picker, then file browser). "
            "This is the default when no target path is given."
        ),
    )
    p.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="Write outputs under this directory (mirrors layout for directory targets).",
    )
    p.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subdirectories when target is a directory.",
    )
    p.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite each source file with the restructured output.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List source -> destination mappings and exit.",
    )
    p.add_argument(
        "--skill",
        default=None,
        metavar="ID",
        help=(
            f"Bundled or installed skill id (default: {DEFAULT_SKILL_ID}). "
            "Examples: markdown-document-architect, categorize-vault-notes. "
            "Overridden by MDA_SKILL env when --skill is omitted."
        ),
    )
    p.add_argument(
        "--skill-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing SKILL.md (and optional MDA-STANDARD.md). "
            "Overrides --skill / MDA_SKILL. Otherwise: MDA_SKILL_DIR env, "
            "~/.claude/skills/<id>, ~/.cursor/skills/<id>, then bundled skill."
        ),
    )
    p.add_argument(
        "--provider",
        choices=("anthropic", "openrouter"),
        default=None,
        help=(
            "LLM provider for this run (overrides MDA_PROVIDER / MDA_USE_OPENROUTER). "
            "Default: anthropic when ANTHROPIC_API_KEY is set, else openrouter."
        ),
    )
    p.add_argument(
        "--model",
        default=None,
        help=(
            f"Model id (Anthropic: default {DEFAULT_MODEL} or MDA_MODEL; "
            "OpenRouter: MDA_OPENROUTER_MODEL)."
        ),
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.environ.get("MDA_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        help=f"Max output tokens (default: {DEFAULT_MAX_TOKENS} or MDA_MAX_TOKENS env).",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Abort if more than this many supported files would be processed (batch mode).",
    )
    p.add_argument(
        "--max-retries",
        type=int,
        default=int(os.environ.get("MDA_MAX_RETRIES", "3")),
        help="Max attempts per file for transient API errors (default: 3 or MDA_MAX_RETRIES).",
    )
    p.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable retries (single attempt per file).",
    )
    p.add_argument(
        "--json-lines",
        action="store_true",
        help=(
            "After each job, print one JSON object to stdout "
            "(src, dst, ok, action, changed, bytes, provider, backup path, error)."
        ),
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="When used with --in-place in batch mode, keep a sibling .bak copy before overwrite.",
    )
    p.add_argument(
        "--checkpoint",
        action="store_true",
        help=(
            "Before batch processing, copy each source file to "
            "~/.mda/checkpoints/<run_id>/ (override with MDA_CHECKPOINT_DIR)."
        ),
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="No progress dots on stderr during streaming.",
    )
    return p


def _parse_script_argv(argv: list[str]) -> argparse.Namespace:
    """Parse arguments after the leading ``script`` token."""
    skill: str | None = None
    skill_dir: Path | None = None
    list_only = False
    tokens: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--list":
            list_only = True
            i += 1
            continue
        if tok == "--skill" and i + 1 < len(argv):
            skill = argv[i + 1]
            i += 2
            continue
        if tok == "--skill-dir" and i + 1 < len(argv):
            skill_dir = Path(argv[i + 1])
            i += 2
            continue
        tokens.append(tok)
        i += 1

    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    script_name = tokens[0] if tokens else None
    script_args = tokens[1:] if len(tokens) > 1 else []
    if script_args and script_args[0] == "--":
        script_args = script_args[1:]

    return argparse.Namespace(
        script_name=script_name,
        script_args=script_args,
        skill=skill,
        skill_dir=skill_dir,
        list=list_only,
    )


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else list(argv)

    if raw_argv and raw_argv[0] == "restore":
        rest = raw_argv[1:]
        if rest == ["--list"] or rest == ["-l"]:
            return run_restore_list()
        apply = "--apply" in rest
        yes = "--yes" in rest
        positional = [t for t in rest if t not in ("--apply", "--yes")]
        if len(positional) != 1:
            print(
                "Usage: mda restore --list\n"
                "       mda restore <run_id>              # dry-run restore plan\n"
                "       mda restore <run_id> --apply --yes  # copy from backup_path",
                file=sys.stderr,
            )
            return 2
        return run_restore_apply(positional[0], apply=apply, yes=yes)

    if raw_argv and raw_argv[0] in ("vault-scan", "vault_scan"):
        args = _parse_script_argv(raw_argv[1:])
        script_args = list(args.script_args)
        if script_args and script_args[0] == "--":
            script_args = script_args[1:]
        return run_vault_scan(script_args)

    if raw_argv and raw_argv[0] == "script":
        args = _parse_script_argv(raw_argv[1:])
        script_args = list(args.script_args)
        if script_args and script_args[0] == "--":
            script_args = script_args[1:]
        return run_skill_script(
            args.script_name,
            script_args,
            skill_dir_arg=args.skill_dir,
            skill_id=args.skill,
            list_only=args.list,
        )

    parser = build_parser()
    args = parser.parse_args(raw_argv)

    if args.check:
        return run_check(
            args.skill_dir,
            cli_provider=args.provider,
            skill_id=args.skill,
        )

    if args.in_place and args.out_dir is not None:
        parser.error("--in-place and --out-dir are mutually exclusive")
    if args.backup and not args.in_place:
        parser.error("--backup requires --in-place")

    max_attempts = 1 if args.no_retry else max(1, args.max_retries)

    use_tui = args.tui or args.target is None
    if use_tui:
        if args.dry_run:
            parser.error("--dry-run is not supported with the interactive UI")
        if args.recursive and args.target is None:
            parser.error("-r/--recursive applies to batch mode; pass a directory target")
        if args.in_place and args.target is None:
            parser.error("--in-place applies to batch mode; pass a file or directory target")
        if args.out_dir is not None and args.target is None:
            parser.error("-o/--out-dir applies to batch mode; pass a directory target")
        if args.max_files is not None and args.target is None:
            parser.error("--max-files applies to batch mode; pass a directory target")
        if args.json_lines and args.target is None:
            parser.error("--json-lines applies to batch mode; pass a directory target")
        if args.backup:
            parser.error("--backup is only supported in batch mode with --in-place")
        from mda_cli.tui import run_tui

        model = args.model or os.environ.get("MDA_MODEL", DEFAULT_MODEL)
        return run_tui(
            start=args.target,
            skill_dir=args.skill_dir,
            skill_id=args.skill,
            model=model,
            max_tokens=args.max_tokens,
            max_attempts=max_attempts,
            provider=args.provider,
        )

    skill_res = resolve_skill_dir(args.skill_dir, skill_id=args.skill)
    skill_dir = skill_res.path
    if not args.json_lines:
        src_note = (
            " (bundled with mda-cli)"
            if skill_res.source == "bundled"
            else f" ({skill_res.source})"
        )
        print(
            f"Using skill: {skill_res.skill_id} ({skill_dir}){src_note}",
            file=sys.stderr,
        )

    skill_id = resolve_skill_id(cli_skill=args.skill)
    jobs = collect_jobs(
        args.target,
        recursive=args.recursive,
        out_dir=args.out_dir,
        in_place=args.in_place,
        max_files=args.max_files,
        skill_id=skill_id,
    )
    if not jobs:
        print("No supported files found.", file=sys.stderr)
        return 0

    if args.dry_run:
        for j in jobs:
            print(f"{j.src}  ->  {j.dst}")
        return 0

    provider = resolve_provider_name(cli_provider=args.provider)
    ensure_api_credentials(provider)

    warn_large_inputs(jobs, max_tokens=args.max_tokens)

    run_id = new_run_id()
    if args.checkpoint:
        checkpoint_root = write_batch_checkpoint(
            run_id=run_id,
            jobs=jobs,
            base=args.target if args.target.is_dir() else args.target.parent,
        )
        if not args.json_lines:
            print(f"Checkpoint: {checkpoint_root}", file=sys.stderr)

    system = load_system_prompt(skill_dir)
    client, ctx = build_restructure_client(
        cli_provider=args.provider,
        model=args.model,
        max_tokens=args.max_tokens,
    )
    if not args.json_lines:
        print(f"Provider: {ctx.provider} (model: {ctx.model})", file=sys.stderr)

    failures = 0
    results: list[JobResult] = []
    for job in jobs:
        try:
            result = process_job_with_provider(
                job,
                client,
                ctx,
                max_tokens=args.max_tokens,
                system=system,
                progress=not args.quiet,
                max_attempts=max_attempts,
                backup_in_place=args.backup,
            )
            results.append(result)
            if args.json_lines:
                print_json_line(job_result_record(result, provider=ctx.provider))
            if not result.ok:
                failures += 1
        except Exception as e:
            failures += 1
            msg = friendly_api_message(e)
            print(f"   FAILED: {job.src}: {msg}", file=sys.stderr)
            failed = JobResult(job=job, ok=False, action="failed", error=msg)
            results.append(failed)
            if args.json_lines:
                print_json_line(
                    job_result_record(failed, provider=ctx.provider),
                )

    manifest_path = write_batch_manifest(
        run_id=run_id,
        results=results,
        skill_id=skill_id,
        provider=ctx.provider,
        target=args.target,
        in_place=args.in_place,
        backup_enabled=args.backup,
    )
    if not args.json_lines:
        print(f"Backup manifest: {manifest_path}", file=sys.stderr)

    if not args.json_lines:
        print(f"Done. {len(jobs) - failures}/{len(jobs)} succeeded.", file=sys.stderr)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
