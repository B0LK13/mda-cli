import asyncio
from pathlib import Path

from mda_cli.tui import MdaNavigatorApp


async def main() -> None:
    root = Path(__file__).resolve().parent.parent
    skill = root / "fake_skill"
    skill.mkdir(exist_ok=True)
    (skill / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    docs = root / "fake_docs"
    docs.mkdir(exist_ok=True)
    (docs / "one.md").write_text("# One\n", encoding="utf-8")
    app = MdaNavigatorApp(
        start=docs,
        skill_dir=skill,
        model="claude-sonnet-4-20250514",
        max_tokens=100,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")
        await pilot.press("space")
        print("selected", app.selected)
        await pilot.press("q")


asyncio.run(main())
