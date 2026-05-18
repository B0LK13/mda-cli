# mda-cli Strategic Roadmap

**Repository:** [B0LK13/mda-cli](https://github.com/B0LK13/mda-cli) (private)  
**Current baseline:** v0.2.9  
**Primary vault:** `E:\ObsidianVault7`  
**Last updated:** 2026-05-18

---

## 1. Executive summary

**mda-cli** is a local-first CLI and TUI for Markdown Document Architect (MDA) and bundled vault skills. v0.2.9 delivers multi-format input, live preview, OpenRouter fallback, and global `mda` on Windows and WSL. Near-term focus is **stabilization** (CI, distribution, install hardening), then **vault-scale workflows** (batch progress, categorize pipelines, cost controls).

---

## 2. Strategic themes (pillars)

| Pillar | Focus | Success signal |
|--------|--------|----------------|
| **UX / TUI** | Folder picker, preview, batch feedback, undo | Users complete vault pilots without CLI flags |
| **Skills & vault ops** | MDA + categorize-vault-notes, flatten → scan → plan → apply | Repeatable vault hygiene on `ObsidianVault7` |
| **Reliability & distribution** | pip/PyPI or GitHub Releases, Win/WSL installers, pinned versions | One-command install on fresh machine |
| **Security & compliance** | Env-only keys, no secrets in repo, dependency audit in CI | Keys rotated; no secrets in logs or releases |
| **Observability** | `--json-lines`, structured logs, CI test matrix | Failures diagnosable from job output alone |

---

## 3. Roadmap by phase

### Phase 0 — Now (v0.2.9 baseline)

**Goals:** Ship-ready local tool for single-user vault work.

**Done (baseline):**

- TUI-first: folder picker (**U**), file select, **P** process, **Ctrl+J** jump, **I** preview toggle
- Live read-only preview (debounced, cached, 10k char cap) for `.md`, `.txt`, `.pdf`, `.docx`
- Multi-format batch + optional `[pdf]` / `[docx]` / `[documents]` extras
- Bundled skills: `markdown-document-architect`, `categorize-vault-notes` + `mda script`
- OpenRouter provider + Anthropic fallback (`MDA_OPENROUTER_FALLBACK`)
- Global install: `scripts/install-global.ps1`, `scripts/install-global.sh` (pipx-aware WSL)
- Atomic writes, `--backup` with `--in-place`, `--json-lines` enrichment
- Unit tests (pytest); integration tests gated on `ANTHROPIC_API_KEY`

**Success metrics:** `mda --check` passes on Win + WSL; pilot `--max-files 5` on vault without data loss.

**Risks:** Hard-coded Python path in `install-global.ps1`; no CI → regressions on upgrade.

---

### Phase 1 — Stabilize (v0.3.x, 4–8 weeks)

**Goals:** Trustworthy releases, automated tests, clearer docs, installer resilience.

| Area | Deliverables |
|------|----------------|
| CI | GitHub Actions: lint (ruff), unit tests, optional integration job with secrets |
| Distribution | GitHub Release wheels + sdist; tag-driven CHANGELOG |
| Install | Detect Python dynamically; stop `mda` before pip on Windows; pipx default doc |
| Secrets | `.env.example`, docs: never commit keys; rotate leaked keys |
| TUI | Batch progress bar; clearer API error surfaces; preview scroll/search (P1) |
| Docs | `docs/` index, troubleshooting matrix, Obsidian vault playbook |

**Success metrics:** Green CI on `main`; install from release artifact on clean Win11 + WSL; 0 secret scans in repo.

**Risks:** Private repo limits community QA; integration test cost; Textual API churn.

---

### Phase 2 — Scale vault workflows (v0.4.x, 8–16 weeks)

**Goals:** Safe bulk operations on large vaults with categorization and move planning.

| Area | Deliverables |
|------|----------------|
| Pipelines | Documented flatten → `scan_vault` → `plan_moves` → MDA/categorize batch |
| Batch UX | Resume checkpoints, per-file skip reasons, aggregate cost estimate |
| Categorize | Apply mode for `plan_moves` (with dry-run default); conflict reporting |
| Undo | Backup manifest + restore command for `--in-place` / moves |
| Cost | `--max-tokens` budget warnings; provider spend hints in `--json-lines` |

**Success metrics:** Process 100+ notes on `ObsidianVault7` with dry-run sign-off; rollback tested.

**Risks:** LLM cost at scale; move plans breaking wikilinks; long-running TUI sessions.

---

### Phase 3 — Enterprise / optional (v0.5+)

**Goals:** Optional packaging, compliance artifacts, and distribution beyond git + pip.

| Area | Deliverables |
|------|----------------|
| Packaging | winget manifest (community or private); signed Windows installer (optional) |
| Compliance | SBOM, dependency audit in CI, documented data residency (API calls leave machine) |
| Telemetry | Opt-in anonymous usage (off by default) |

**Success metrics:** Release artifacts install from winget or signed installer on a clean machine; SBOM published per release; API data-flow documented for compliance review.

**Risks:** Private distribution friction; signed installer cost; dependency audit noise without triage process.

---

## 4. Detailed action items

| ID | P | Owner | Action | Dependencies | ETA |
|----|---|-------|--------|--------------|-----|
| A01 | P0 | Dev | Add GitHub Actions workflow: ruff + pytest on push/PR | — | W1 |
| A02 | P0 | Dev | Gate integration tests behind `ANTHROPIC_API_KEY` secret (optional job) | A01 | W2 |
| A03 | P0 | User | Rotate any API keys ever pasted in chat; set env only | — | Now |
| A04 | P0 | Dev | Add `.env.example` listing `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `MDA_*` | — | W1 |
| A05 | P0 | Dev | Parameterize `install-global.ps1` Python discovery (remove hard-coded path) | — | W2 |
| A06 | P1 | Dev | Pre-install: stop `mda`/`mda-cli` processes on Windows (document in script) | A05 | W2 |
| A07 | P1 | Dev | WSL: verify pipx path + `~/.config/mda-cli/python` on fresh Ubuntu | — | W2 |
| A08 | P1 | Dev | GitHub Release workflow: build wheel/sdist on tag `v*` | A01 | W3 |
| A09 | P1 | Dev | Attach `[documents]` extra install instructions to release notes | A08 | W3 |
| A10 | P1 | Dev | Document `pip install` from GitHub release URL (private repo PAT) | A08 | W3 |
| A11 | P2 | Dev | Evaluate PyPI publish vs private index only | Legal/repo | W6 |
| A12 | P2 | Dev | Draft winget manifest (or defer until public) | A08, A11 | W8+ |
| A13 | P1 | Dev | TUI: batch progress indicator during **P** multi-file run | — | W4 |
| A14 | P1 | Dev | TUI: show last API error inline (non-blocking) | — | W4 |
| A15 | P2 | Dev | TUI: preview scroll / search-in-preview | — | W6 |
| A16 | P2 | Dev | TUI: undo last in-place write (session-level) | backup manifest | W8 |
| A17 | P1 | User | Vault pilot: `mda --dry-run` + `--max-files 5` on `E:\ObsidianVault7` | A03 | W1 |
| A18 | P1 | User | Run `flatten_vault_md.py --dry-run` before bulk categorize | A17 | W2 |
| A19 | P1 | Dev | Document vault pipeline in `docs/VAULT-PLAYBOOK.md` | A17 | W3 |
| A20 | P1 | Dev | `mda script plan_moves` examples with `--dry-run` default emphasized | A19 | W3 |
| A21 | P1 | Dev | Expand README: link to this ROADMAP + cost control flags | — | W1 |
| A22 | P2 | Dev | Add `docs/` troubleshooting: WinError 32, NoActiveWorker, module not found | — | W3 |
| A23 | P2 | Dev | Optional MkDocs or GitHub Pages for docs site | A19 | W8 |
| A24 | P1 | Dev | Release checklist template in repo (see §6) | A08 | W3 |
| A28 | P1 | Dev | CI: Windows runner smoke `mda --check` after install script | A01, A05 | W4 |
| A29 | P1 | Dev | CI: Linux runner smoke `install-global.sh` + `mda --check` | A01 | W4 |
| A30 | P2 | Dev | Add dependabot/Renovate for Python deps | A01 | W5 |
| A31 | P1 | Dev | `--max-files` + `--max-tokens` documented cost guardrails | — | W2 |
| A32 | P2 | Dev | Export batch summary CSV from `--json-lines` | — | W6 |

---

## 5. Deployment plans

### 5a. Developer install (editable)

**Prerequisites:** Python 3.10+, git, API keys in shell env (not files).

**Windows (PowerShell):**

1. `cd C:\Users\Admin\Projects\mda-cli`
2. `python -m pip install -e ".[dev,document]"`
3. `set ANTHROPIC_API_KEY=...` (session) or User env var
4. `python -m pytest -q`
5. `python -m mda_cli --check`

**WSL (zsh):**

1. `cd /mnt/c/Users/Admin/Projects/mda-cli`
2. `python3 -m pip install -e ".[dev]"`
3. `export ANTHROPIC_API_KEY='...'`
4. `python3 -m pytest -q && mda --check` (or `python3 -m mda_cli`)

**Verification:** `mda --version` → `0.2.9`; bundled skills listed.

**Rollback:** `pip uninstall mda-cli`; delete editable checkout if needed.

**Troubleshooting:** Wrong Python on PATH → use full path to 3.10+; WSL use `install-global.sh` pinned interpreter.

---

### 5b. End-user global install

**Prerequisites:** Same as 5a; close running TUI before reinstall on Windows.

**Windows:**

1. `pwsh -File C:\Users\Admin\Projects\mda-cli\scripts\install-global.ps1`
2. New terminal: `mda --check`
3. Optional: `pip install 'mda-cli[documents]'` if processing PDF/DOCX

**WSL:**

1. `cd /mnt/c/Users/Admin/Projects/mda-cli && ./scripts/install-global.sh`
2. `source ~/.zshrc && mda --check`

**Verification:** `where mda` (Win) / `which mda` (WSL); `mda --check` shows provider + bundled skills.

**Rollback:** `pip uninstall mda-cli`; remove user PATH entry for Scripts/`~/.local/bin` if desired.

**Troubleshooting:** `[WinError 32]` → quit `mda` in all terminals; `No module named mda_cli` → rerun `install-global.sh`.

---

### 5c. GitHub release pipeline

**Prerequisites:** A01 CI green; tag naming `v0.3.0`; `CHANGELOG.md` updated; GITHUB_TOKEN for workflow.

**Steps:**

1. Bump `version` in `pyproject.toml` + `mda_cli/__init__.py`
2. Merge to `main`; create annotated tag `git tag -a v0.3.0 -m "..."`
3. Push tag → workflow builds wheel + sdist, uploads to GitHub Release
4. Release notes: copy CHANGELOG section; note extras: `pip install mda-cli[documents]`
5. Private install: `pip install https://github.com/B0LK13/mda-cli/releases/download/v0.3.0/mda_cli-0.3.0-py3-none-any.whl` (with PAT)

**Verification:** Fresh venv `pip install` wheel; `mda --version` matches tag.

**Rollback:** Yank release asset; pin users to previous wheel URL or `pip install mda-cli==0.2.9` from prior release.

**Troubleshooting:** Missing `bundled_skills` in wheel → verify `hatch` force-include in `pyproject.toml`.

---

### 5d. Production use on Obsidian vault

**Prerequisites:** Keys in env; vault backed up (git or Obsidian sync); pilot scope agreed.

**Steps:**

1. `set MDA_SKILL=markdown-document-architect` (or `categorize-vault-notes`)
2. Dry-run: `mda E:\ObsidianVault7\note.md --dry-run`
3. Small batch: `mda E:\ObsidianVault7 -r --max-files 5 -q`
4. Review outputs (`*.restructured.md` or `*.restructured.txt`)
5. In-place only with backup: `mda path --in-place --backup`
6. OpenRouter fallback: set `OPENROUTER_API_KEY`; keep `MDA_OPENROUTER_FALLBACK=1`
7. Categorize pipeline: `mda script scan_vault -- ...` then `plan_moves --dry-run`

**Verification:** `--json-lines` shows `changed`, `bytes_in/out`; spot-check random notes in Obsidian.

**Rollback:** Restore from `--backup` siblings; git `checkout` for tracked vault; reinstall CLI (§5e).

**Troubleshooting:** 429/402 → fallback or lower `--max-files`; timeout → raise `MDA_API_TIMEOUT`.

---

### 5e. Rollback / recovery

**Prerequisites:** Know last good version (e.g. `0.2.9`).

**Steps:**

1. `pip install mda-cli==0.2.9` or reinstall from known wheel
2. Win: rerun `install-global.ps1`; WSL: `./scripts/install-global.sh`
3. `mda --check`
4. Vault: restore from backup/git if batch run went wrong

**Verification:** Version pin matches; sample file dry-run unchanged behavior.

**Rollback of rollback:** Forward-upgrade to latest release after root-cause fix.

**Troubleshooting:** Editable install overrides pin → `pip uninstall` then install specific version.

---

## 6. Release checklist template

Copy for each `v0.x.y` release:

```markdown
## Release v0.x.y

- [ ] CHANGELOG.md section for v0.x.y
- [ ] Version bump: pyproject.toml + mda_cli/__init__.py
- [ ] `python -m pytest -q` local
- [ ] `ruff check` clean
- [ ] PR merged to main
- [ ] Tag `v0.x.y` pushed
- [ ] CI green on tag
- [ ] GitHub Release assets (wheel, sdist) uploaded
- [ ] Release notes: extras `[documents]`, breaking changes
- [ ] Win: `install-global.ps1` smoke `mda --check`
- [ ] WSL: `install-global.sh` smoke `mda --check`
- [ ] User notified: reinstall / `pip install --upgrade` steps
- [ ] API keys: no commits; rotate if any leak suspected
```

---

## 7. Open questions / decisions

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| Q1 | Public repo vs stay private? | Private + PAT install / Public + PyPI | Stay private until winget/PyPI strategy clear |
| Q2 | PyPI package name | `mda-cli` vs `mda` | `mda-cli` on PyPI; console script stays `mda` |
| Q3 | Default skill for vault batch | MDA vs categorize | Pilot categorize on 5 files; MDA for prose cleanup |
| Q4 | In-place default | Off vs on with `--backup` | Off by default; explicit `--in-place --backup` |
| Q5 | Documentation site | README only vs MkDocs | README + `docs/` until v0.4; then MkDocs optional |
| Q6 | Integration test budget | Skip CI integration / nightly only | Nightly optional job with org secret |

---

## References

- Install scripts: `scripts/install-global.ps1`, `scripts/install-global.sh`
- Vault helper: `scripts/flatten_vault_md.py`
- Changelog: `CHANGELOG.md`
