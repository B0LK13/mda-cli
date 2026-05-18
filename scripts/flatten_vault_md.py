"""Move all .md files under a vault root into the root with unique names (path-encoded)."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path


def destination_path(vault: Path, src: Path) -> Path | None:
    """Return target path in vault root, or None if already at root."""
    rel = src.relative_to(vault)
    if len(rel.parts) == 1:
        return None
    encoded = "__".join(rel.parts)
    if len(encoded) > 200:
        h = hashlib.sha256(str(rel).encode("utf-8")).hexdigest()[:16]
        stem = rel.stem[:80] if rel.suffix.lower() == ".md" else rel.name[:80]
        encoded = f"{stem}__{h}.md"
    return vault / encoded


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("vault", type=Path, help="Vault root (e.g. E:\\ObsidianVault7)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves only",
    )
    args = p.parse_args()
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"ERROR: not a directory: {vault}", file=sys.stderr)
        return 2

    md_files = sorted(vault.rglob("*.md"))
    moved = 0
    skipped_root = 0
    errors = 0
    for src in md_files:
        if not src.is_file():
            continue
        dst = destination_path(vault, src)
        if dst is None:
            skipped_root += 1
            continue
        if args.dry_run:
            print(f"{src} -> {dst}")
            moved += 1
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.resolve() == src.resolve():
                continue
            if dst.exists():
                # Same vault flatten second pass: skip if already there
                if dst.stat().st_size == src.stat().st_size:
                    try:
                        if dst.read_bytes() == src.read_bytes():
                            src.unlink()
                            moved += 1
                            continue
                    except OSError:
                        pass
                print(f"SKIP collision (exists, differ): {dst}", file=sys.stderr)
                errors += 1
                continue
            shutil.move(str(src), str(dst))
            moved += 1
            if moved % 500 == 0:
                print(f"... moved {moved}", file=sys.stderr)
        except OSError as e:
            print(f"ERROR {src}: {e}", file=sys.stderr)
            errors += 1

    summary = (
        f"Done. moved={moved} already_in_root={skipped_root} "
        f"errors={errors} dry_run={args.dry_run}"
    )
    print(summary, file=sys.stderr)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
