# mda-cli

**Roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md) · **Gap analysis:** [docs/GAP-ANALYSIS.md](docs/GAP-ANALYSIS.md) ([tracked issues](https://github.com/B0LK13/mda-cli/issues))

CLI for **Markdown Document Architect (MDA)** and related bundled skills: loads `SKILL.md` and companion standards (bundled by default), calls Anthropic or OpenRouter, and writes restructured output (strips the outer fence when present).

**Supported inputs:** `.md`, `.pdf`, `.docx`, `.doc` (listing only; convert to docx), `.txt` — case-insensitive. Override with `MDA_EXTENSIONS` (comma-separated, e.g. `MDA_EXTENSIONS=.md,.txt`).

**Optional extras:** `pip install 'mda-cli[pdf]'` and/or `'mda-cli[docx]'` (or `'mda-cli[documents]'` for both) for PDF and Word extraction.

You do **not** need a separate Claude/Cursor skill install for normal use. Optional override: set `MDA_SKILL_DIR` or pass `--skill-dir` to use an external skill folder.

## Global install

`mda` must be installed separately in each shell environment. Windows PowerShell uses `mda.exe` from Python’s `Scripts` folder; **zsh** (WSL, macOS, Linux) uses `~/.local/bin/mda` from `pip install -e`.

### Windows (PowerShell / CMD)

From the repo root, run once (adds Python `Scripts` to your **user** PATH if needed):

```powershell
pwsh -File scripts\install-global.ps1
```

Then open a **new** terminal and run `mda` (TUI) or `mda --check`.

**Troubleshooting (Windows):** If `pip install` fails with `[WinError 32]` on `mda.exe`, another process (often a Cursor terminal) is still running `mda`. Close those terminals or quit the TUI, then rerun `scripts\install-global.ps1` (it stops `mda` / `mda-cli` / `mda-tui` and retries). You can always run `python -m mda_cli` with the same Python used by the installer.

### macOS / Linux / WSL (zsh)

From the repo root in **zsh** (not PowerShell):

```bash
chmod +x scripts/install-global.sh scripts/mda
./scripts/install-global.sh
source ~/.zshrc
mda --version
```

WSL path to this repo: `/mnt/c/Users/Admin/Projects/mda-cli`

The script installs with **pipx** when available (typical on Homebrew / PEP 668 Python), otherwise `pip install --user -e`. It appends a marked `# mda-cli` block to `~/.zshrc` only if `~/.local/bin` is not already on PATH. A fallback `scripts/mda` wrapper is copied only if no working `mda` command exists yet.

### Git Bash (optional)

Git Bash does not use `mda.exe` from Windows PATH by default. Use the same shell installer from a **bash** session, then add `~/.local/bin` to PATH in `~/.bashrc` if you do not use zsh:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Or run without installing: `python -m mda_cli` from the repo after `pip install -e .`.

Synonyms everywhere: `mda-cli`, `mda-tui`.

## Getting started (interactive)

1. **Install** (once) — or use [Global install](#global-install) above:

   ```powershell
   cd C:\Users\Admin\Projects\mda-cli
   python -m pip install -e .
   ```

2. **Set your API key**:

   ```powershell
   set ANTHROPIC_API_KEY=your-key-here
   ```

3. **Run** with no arguments — the interactive UI opens:

   ```powershell
   mda
   ```

4. **Pick a folder** (vault or project root):
   - Use **↑/↓** or **j/k** to move
   - **Enter** opens a folder
   - **Backspace** goes up
   - **H** jumps to your home folder
   - **U** = **Use this folder** when you are in the right place
   - **I** toggles the live document preview pane (highlight a supported file to see original content)
   - **Q** quits

5. **Select files** (`.md`, `.pdf`, `.docx`, `.txt`, …) and run:
   - **Space** toggles selection on supported files (Kind column shows extension)
   - **A** selects supported files recursively under the current folder
   - **P** runs MDA on everything selected
   - **O** cycles output mode (sibling file, in-place, or output folder)

Your last chosen folder is remembered for next time (saved under `%APPDATA%\mda-cli\config.json` on Windows).

## Install check

```powershell
python -m mda_cli --check
```

## Batch mode (power users)

Process paths from the command line without the UI:

```powershell
mda path\to\file.md
mda path\to\vault -r --max-files 10 -q
mda path\to\vault --dry-run
mda path\to\file.md --in-place --backup
```

Optional environment variables: `MDA_SKILL` (skill id), `MDA_SKILL_DIR` (explicit skill folder), `MDA_EXTENSIONS`, `MDA_MODEL`, `MDA_MAX_TOKENS`, `MDA_API_TIMEOUT`.

**Output naming:** sibling `*.restructured.md` for the default MDA skill (including PDF/DOCX sources). The `categorize-vault-notes` skill writes `*.restructured.txt` for non-Markdown sources.

### Safe overwrite workflow

- `--in-place` overwrites the source file.
- `--backup` is available only with `--in-place` in batch mode and writes a sibling backup before replacing the file.
- Generated outputs are written atomically. If the process fails during write, the original destination file is left in place.
- `--json-lines` now includes `action`, `changed`, `bytes_in`, `bytes_out`, and `backup_path` fields.

### Skill selection

| Mechanism | Example |
|-----------|---------|
| Default | `markdown-document-architect` (MDA restructure) |
| `--skill` | `mda --skill categorize-vault-notes E:\ObsidianVault7 --max-files 5` |
| `MDA_SKILL` | `set MDA_SKILL=categorize-vault-notes` |
| `--skill-dir` / `MDA_SKILL_DIR` | Explicit folder with `SKILL.md` (ignores skill id path) |

Bundled skills: `markdown-document-architect`, `categorize-vault-notes`. Resolution order for a given id: `--skill-dir` → `MDA_SKILL_DIR` → `~/.claude/skills/<id>` → `~/.cursor/skills/<id>` → packaged `mda_cli/bundled_skills/<id>`. Run `mda --check` to see bundled ids, active skill, path, and source (`bundled`, `claude`, `cursor`, `env`, or `explicit`).

### Categorize vault notes

Assign YAML frontmatter and optional folder hints for Obsidian vaults (flat or nested):

```powershell
mda --skill categorize-vault-notes E:\ObsidianVault7\note.md
mda script --list --skill categorize-vault-notes
mda script scan_vault --skill categorize-vault-notes -- E:\ObsidianVault7 --limit 20
mda script plan_moves --skill categorize-vault-notes -- E:\ObsidianVault7 --dry-run
```

Pair with `scripts\flatten_vault_md.py` when moving nested notes to the vault root before batch categorization.

### LLM providers

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Primary provider (default when set) |
| `OPENROUTER_API_KEY` | OpenRouter provider or Anthropic fallback |
| `MDA_PROVIDER` | `anthropic` or `openrouter` for this shell |
| `MDA_USE_OPENROUTER` | Set to `1` to prefer OpenRouter |
| `MDA_OPENROUTER_MODEL` | OpenRouter model id (default `anthropic/claude-sonnet-4`) |
| `MDA_OPENROUTER_FALLBACK` | `1` (default) retry via OpenRouter when Anthropic returns 402/403/429/529/5xx |

CLI override: `mda --provider openrouter path\to\file.md`

### Troubleshooting: `No module named mda_cli`

Homebrew/Linuxbrew `python3` on PATH is often **not** the interpreter that installed `mda-cli` (e.g. Python 3.14 without the package). Reinstall so `~/.local/bin/mda` runs the pinned venv:

```bash
cd /mnt/c/Users/Admin/Projects/mda-cli
./scripts/install-global.sh
source ~/.zshrc
mda --check
```

The installer uses **pipx** when available, writes `~/.config/mda-cli/python`, and installs a wrapper that runs `that-python -m mda_cli` (not bare `python3` from PATH).

## Tests

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Vault flatten helper

```powershell
python scripts\flatten_vault_md.py E:\ObsidianVault7 --dry-run
```
