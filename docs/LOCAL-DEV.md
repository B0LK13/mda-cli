# Local development (no GitHub CI)

Use this workflow when GitHub Actions billing is blocked or you want to work entirely on your machine.

## Branch

Active feature work lives on **`chore/close-p0-issues`** (v0.2.10, CI configs, docs, TUI fixes, `plan_moves` dry-run default).

```powershell
cd C:\Users\Admin\Projects\mda-cli
git fetch origin
git checkout chore/close-p0-issues
```

Optional: merge into local `main` for day-to-day use (do not push unless you intend to):

```powershell
git checkout main
git merge chore/close-p0-issues
```

Stay on `chore/close-p0-issues` if you are still landing changes before merging locally.

## Install

Python 3.10+ (this machine uses 3.13):

```powershell
& "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe" -m pip install -e ".[dev,documents]"
```

Or after `scripts\install-global.ps1`, the `mda` on PATH uses whichever Python installed the package.

## Verify

```powershell
mda --check
python -m pytest -q -m "not integration"
```

Integration tests (live API) are optional:

```powershell
$env:ANTHROPIC_API_KEY = "sk-..."
python -m pytest -q -m integration
```

## `mda` and environment

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic provider |
| `OPENROUTER_API_KEY` | OpenRouter provider / fallback |
| `MDA_SKILL` / `mda --skill` | Active skill id |
| `MDA_SKILL_DIR` | Override skill folder |
| `MDA_PROVIDER` | `anthropic` or `openrouter` |
| `MDA_MANIFEST_DIR` | Backup manifest directory (default `~/.mda/manifests`) |

Examples:

```powershell
mda --check
mda path\to\note.md --dry-run
mda path\to\vault --in-place --backup
mda restore --list
mda --tui
```

## GitHub CI

Pushes and PRs normally run `.github/workflows/ci.yml`. While billing is blocked, rely on local `pytest` and `mda --check` above. Re-enable remote CI when billing is fixed, then merge `chore/close-p0-issues` via PR as usual.
