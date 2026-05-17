"""Print a move plan from `folder` keys in YAML frontmatter."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FOLDER = re.compile(r"^folder\s*:\s*(.+)\s*$", re.MULTILINE)


def read_folder(text: str) -> str | None:
    m = _FRONTMATTER.match(text)
    if not m:
        return None
    fm = m.group(1)
    hit = _FOLDER.search(fm)
    if not hit:
        return None
    return hit.group(1).strip().strip("'\"")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("vault", type=Path, help="Vault root directory")
    p.add_argument("--recursive", "-r", action="store_true", help="Include subfolders")
    p.add_argument("--dry-run", action="store_true", help="Only print planned moves")
    args = p.parse_args()
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"ERROR: not a directory: {vault}")
        return 2

    pattern = "**/*.md" if args.recursive else "*.md"
    planned = 0
    skipped = 0
    for path in sorted(vault.glob(pattern)):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"ERROR {path}: {e}")
            continue
        folder = read_folder(text)
        if not folder:
            skipped += 1
            continue
        dest = vault / folder.replace("/", "\\") / path.name
        if dest.resolve() == path.resolve():
            skipped += 1
            continue
        planned += 1
        print(f"{path} -> {dest}")
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                print(f"  SKIP exists: {dest}")
                continue
            path.rename(dest)

    print(f"planned={planned} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
