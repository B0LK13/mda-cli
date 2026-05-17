"""One-off: ensure MdaNavigatorApp CSS parses (Textual)."""
from __future__ import annotations

import asyncio
from pathlib import Path

from mda_cli.tui import MdaNavigatorApp


async def _check() -> None:
    app = MdaNavigatorApp(start=Path.cwd(), skill_dir=None, model="x", max_tokens=1)
    async with app.run_test():
        pass


def main() -> None:
    asyncio.run(_check())
    print("CSS ok")


if __name__ == "__main__":
    main()
