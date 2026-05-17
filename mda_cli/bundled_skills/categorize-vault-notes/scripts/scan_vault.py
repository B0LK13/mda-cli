"""List Markdown files under a vault with basic frontmatter hints."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_KEY = re.compile(r"^([A-Za-z0-9_-]+)\s*:", re.MULTILINE)


def frontmatter_keys(text: str) -> list[str]:
    m = _FRONTMATTER.match(text)
    if not m:
        return []
    return sorted({k.group(1) for k in _KEY.finditer(m.group(1))})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("vault", type=Path, help="Vault root directory")
    p.add_argument("--recursive", "-r", action="store_true", help="Include subfolders")
    p.add_argument("--limit", type=int, default=0, help="Max files to print (0 = all)")
    args = p.parse_args()
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"ERROR: not a directory: {vault}")
        return 2

    pattern = "**/*.md" if args.recursive else "*.md"
    files = sorted(vault.glob(pattern))
    if args.limit:
        files = files[: args.limit]

    for path in files:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"{path}\tERROR\t{e}")
            continue
        keys = frontmatter_keys(text)
        rel = path.relative_to(vault)
        size = path.stat().st_size
        key_s = ",".join(keys) if keys else "-"
        print(f"{rel}\t{size}\t{key_s}")

    print(f"total={len(files)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
