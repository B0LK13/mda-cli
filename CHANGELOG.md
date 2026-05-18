# Changelog

## [0.2.10]

- GitHub Actions: ruff + unit pytest on push/PR; optional integration job on `main`.
- CI smoke: `install-global.sh` / `install-global.ps1` then `mda --check` on Linux and Windows.
- Tag-driven release workflow uploads wheel/sdist to GitHub Releases.
- `.env.example` for API keys and `MDA_*` variables.
- `install-global.ps1`: dynamic Python 3.10+ discovery (`py`, `python3`, `MDA_PYTHON`); stop `mda` processes before pip.
- `plan_moves`: dry-run by default; `--apply` to move files.
- Docs: `docs/VAULT-PLAYBOOK.md`, `docs/TROUBLESHOOTING.md`, README cost guardrails.
- TUI: batch progress (`Batch N/M`) and inline last API error status line.
- Dependabot for pip and GitHub Actions.

## [0.2.9]

- TUI: live read-only preview of the highlighted supported file (`.md`, `.txt`, `.pdf`, `.docx`, `.doc` listing).
- Async extraction with 150ms debounce, path+mtime cache, truncation at 10k chars, metadata line (path, ext, size).
- Clear preview on `..`/directories; friendly errors for missing PDF/DOCX extras and legacy `.doc`.
- Toggle preview pane with **I** (`i`); **P** still runs MDA.

## [0.2.8]

- TUI and batch CLI accept `.md`, `.pdf`, `.docx`, `.doc`, and `.txt` (case-insensitive).
- Optional pip extras: `mda-cli[pdf]` (pypdf), `mda-cli[docx]` (python-docx), `mda-cli[documents]` (both).
- `MDA_EXTENSIONS` env overrides the default extension list (comma-separated).
- Text extraction for PDF/DOCX; legacy `.doc` shows a clear convert-to-docx error.
- Folder picker counts all supported types; TUI Kind column shows extension.
- Output: `*.restructured.md` by default; `categorize-vault-notes` uses `*.restructured.txt` for non-Markdown sources.

## [0.2.7]

- Bundle multiple skills under `mda_cli/bundled_skills/` (`markdown-document-architect`, `categorize-vault-notes`).
- Select skill via `--skill`, `MDA_SKILL`, or `MDA_SKILL_DIR` (unchanged override).
- `mda script` subcommand runs helpers from the active skill's `scripts/` directory; `mda --check` lists bundled skills.

## [0.2.5]

- Fix TUI `NoActiveWorker` crash on jump-to-path (`ctrl+j`) and name filter (`f`) by running `push_screen_wait` inside `@work` workers (Textual 8.x).

## [0.2.6]

- Add atomic output writes for batch and TUI processing paths.
- Add optional `--backup` for `--in-place` batch runs.
- Extend JSON-lines/job result reporting with `action`, `changed`, byte counts, and backup-path metadata.

## [0.2.4]

- Bundle Markdown Document Architect skill (`SKILL.md`, `MDA-STANDARD.md`) inside the package so `mda` / TUI work without Claude or Cursor skill installs.
- Skill resolution fallback order ends with packaged `mda_cli/bundled_skill`; `mda --check` reports skill source (`bundled`, `claude`, `cursor`, `env`, `explicit`).

## [0.2.3]

- Fix global `mda` launcher: pin install Python in `~/.config/mda-cli/python`, pipx-aware wrapper (avoids Linuxbrew `python3.14` without `mda_cli`).
- OpenRouter provider: `MDA_PROVIDER`, `MDA_USE_OPENROUTER`, `MDA_OPENROUTER_FALLBACK`, `--provider`, `--check` provider lines.

## [0.2.2]

- TUI-first: `mda` / `mda-cli` with no arguments opens the interactive UI.
- Folder picker before file browser; remembers last folder in user config.
- `mda-cli` console script alias.

## [0.2.1]

- UTF-16 / BOM skill and source reads, prompt cache, retries, TUI improvements, `--check`, `--max-files`, `--json-lines`, vault flatten script.
