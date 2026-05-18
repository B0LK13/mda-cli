# mda-cli Gap Analysis

**Baseline:** v0.2.9 (2026-05-18)  
**Planned state:** [ROADMAP.md](ROADMAP.md)  
**Repository:** [B0LK13/mda-cli](https://github.com/B0LK13/mda-cli) (private)

---

## Executive summary

| Area | Planned (ROADMAP) | Current (v0.2.9) | Gap |
|------|-------------------|------------------|-----|
| **Phase 0 baseline** | TUI, multi-format, bundled skills, OpenRouter, global install, tests | Shipped per CHANGELOG 0.2.3–0.2.9 | None for baseline scope |
| **CI / quality** | Ruff + pytest on push/PR; optional integration; install smoke (A01, A02, A28, A29) | 87 unit tests locally; no `.github/workflows` | **No automated CI** |
| **Distribution** | Tag-driven GitHub Releases (wheel/sdist); private PAT install docs (A08–A10) | Editable/git install only | **No release pipeline or artifacts** |
| **Install hardening** | Dynamic Python; stop `mda` before pip on Windows (A05, A06) | PS1 hard-codes Python313 path; no process stop in script | **Fragile Win installer** |
| **Secrets / docs** | `.env.example`; cost guardrails; troubleshooting (A04, A22, A31) | `.gitignore` allows `.env.example` but file missing; README partial | **Missing env template & doc depth** |
| **TUI UX (Phase 1)** | Batch progress bar; inline API errors; preview scroll (A13–A15) | Log-only batch feedback; errors in log pane | **Limited batch UX** |
| **Vault workflows (Phase 2)** | Playbook, dry-run defaults, TUI pipelines, undo, checkpoints (A16–A20, A32) | CLI `mda script` only; `plan_moves` applies unless `--dry-run` | **Not vault-scale safe yet** |
| **Enterprise (Phase 3)** | winget, SBOM, opt-in telemetry (A12, Phase 3) | Not started | Deferred |

**Priority focus:** Close Phase 1 P0/P1 gaps (CI, releases, install, docs, TUI feedback) before Phase 2 bulk vault automation.

---

## Phase 0 — Now (v0.2.9 baseline)

### Planned

Ship-ready local tool: TUI folder picker, live preview, multi-format batch, bundled MDA + categorize skills, OpenRouter fallback, global Win/WSL install, atomic writes, `--backup`, `--json-lines`, pytest.

### Current (implemented)

| Capability | Evidence |
|------------|----------|
| TUI folder picker, file select, **P** batch, **Ctrl+J**, **I** preview | `mda_cli/tui.py`, CHANGELOG 0.2.9 |
| Preview debounce/cache/10k cap; PDF/DOCX/txt/md | `mda_cli/preview.py`, `tests/test_preview.py` |
| Multi-format + `[pdf]`/`[docx]`/`[documents]` extras | `mda_cli/document_io.py`, `pyproject.toml` |
| Bundled skills + `mda script` | `mda_cli/bundled_skills/`, CHANGELOG 0.2.7 |
| OpenRouter + Anthropic fallback | `mda_cli/providers.py`, README |
| Global install scripts | `scripts/install-global.ps1`, `install-global.sh` |
| Atomic writes, `--backup`, enriched `--json-lines` | `mda_cli/core.py`, CHANGELOG 0.2.6 |
| Unit tests (87 collected); integration gated | `tests/`, `@pytest.mark.integration` |

### Gap

| ID | Gap | Priority |
|----|-----|----------|
| — | Phase 0 deliverables match roadmap baseline | — |
| A03 | User action: rotate keys if ever exposed (process, not code) | P0 (ops) |
| — | `install-global.ps1` still documents risk: hard-coded Python path (ROADMAP §Phase 0 risks) | P0 → A05 |

---

## Phase 1 — Stabilize (v0.3.x)

### Planned

CI, GitHub Releases, installer resilience, `.env.example`, TUI batch progress + API error UX, expanded `docs/`, release checklist.

### Current

| Item | Status |
|------|--------|
| GitHub Actions (ruff + pytest) | **Missing** — no `.github/` workflows |
| Integration job with secret | **Missing** — marker exists, no CI job |
| `.env.example` | **Missing** — `.gitignore` has `!.env.example` only |
| `install-global.ps1` Python discovery | **Partial** — falls back to `python` if hard path missing; default still hard-coded |
| Stop `mda` before pip (Windows) | **Missing in script** — README describes behavior not in `install-global.ps1` |
| GitHub Release wheel/sdist | **Missing** |
| TUI batch progress bar | **Missing** — sequential log lines only (`_run_batch_sync`) |
| TUI inline API error | **Missing** — failures logged via `log_msg` |
| Preview scroll/search | **Not implemented** (P2 A15) |
| `docs/VAULT-PLAYBOOK.md` | **Missing** — only `docs/ROADMAP.md` |
| `docs/` troubleshooting matrix | **Partial** — README troubleshooting only |
| Release checklist file | **In ROADMAP §6 only** — not a repo file |
| README → ROADMAP link | **Done** |
| Cost guardrails doc (`--max-files`, `--max-tokens`) | **Partial** — flags exist; no dedicated guardrails section |
| Dependabot/Renovate | **Missing** |

### Gap table (action IDs)

| ID | P | Planned action | Current | Gap |
|----|---|----------------|---------|-----|
| A01 | P0 | GitHub Actions: ruff + pytest | None | **Full** |
| A02 | P0 | Optional integration job | Local skip only | **Full** |
| A04 | P0 | `.env.example` | Absent | **Full** |
| A05 | P0 | Parameterize PS1 Python | Hard-coded path line 6 | **Partial** |
| A06 | P1 | Stop mda before pip (Win) | README only | **Full** (doc ahead of code) |
| A07 | P1 | WSL pipx smoke on fresh Ubuntu | Manual/script works; no CI | **Partial** |
| A08 | P1 | Release workflow on `v*` tag | None | **Full** |
| A09 | P1 | Release notes: `[documents]` extra | N/A until A08 | **Blocked** |
| A10 | P1 | Document private PAT wheel install | ROADMAP §5c only | **Partial** |
| A11 | P2 | PyPI vs private index | Not decided (Q1/Q2) | Open |
| A13 | P1 | TUI batch progress | Log messages only | **Full** |
| A14 | P1 | TUI inline API error | Log only | **Full** |
| A15 | P2 | Preview scroll/search | Not started | **Full** |
| A19 | P1 | `docs/VAULT-PLAYBOOK.md` | Missing | **Full** |
| A21 | P1 | README roadmap + cost flags | Roadmap linked; cost section thin | **Partial** |
| A22 | P2 | `docs/` troubleshooting | README snippets | **Partial** |
| A23 | P2 | MkDocs / GitHub Pages | Not started | **Full** |
| A24 | P1 | Release checklist in repo | ROADMAP template only | **Partial** |
| A28 | P1 | CI Win smoke `mda --check` | None | **Full** |
| A29 | P1 | CI Linux smoke `install-global.sh` | None | **Full** |
| A30 | P2 | Dependabot | None | **Full** |
| A31 | P1 | Document cost guardrails | Env vars listed | **Partial** |

---

## Phase 2 — Scale vault workflows (v0.4.x)

### Planned

Documented flatten → scan → plan → batch pipeline; resume checkpoints; categorize apply with dry-run default; backup manifest + restore; token budget warnings in JSON-lines.

### Current

| Item | Status |
|------|--------|
| `flatten_vault_md.py` | Present under `scripts/` |
| `scan_vault`, `plan_moves` via `mda script` | Bundled skill scripts |
| TUI categorize pipeline | **Not integrated** — CLI/script only |
| `plan_moves` dry-run default | **Opposite** — moves apply unless `--dry-run` |
| Resume checkpoints | **Missing** |
| Backup manifest + restore command | **Sibling `--backup` only**; no manifest/restore CLI |
| `--max-tokens` warnings / spend hints in JSON-lines | **Missing** |
| CSV export from JSON-lines (A32) | **Missing** |

### Gap table (action IDs)

| ID | P | Planned action | Current | Gap |
|----|---|----------------|---------|-----|
| A17 | P1 | User vault pilot (dry-run, max-files) | Manual | User task |
| A18 | P1 | flatten dry-run before categorize | Script exists | User task |
| A20 | P1 | `plan_moves` dry-run default emphasized | Opt-in `--dry-run` | **Behavior + docs** |
| A16 | P2 | TUI undo in-place write | Not started | **Full** |
| — | P1 | TUI vault/categorize workflow | Not started | **Full** |
| — | P1 | Resume checkpoints | Not started | **Full** |
| — | P1 | Restore from backup manifest | Not started | **Full** |
| A32 | P2 | Batch summary CSV | Not started | **Full** |

---

## Phase 3 — Enterprise / optional (v0.5+)

| ID | Item | Status |
|----|------|--------|
| A12 | winget manifest | Not started |
| — | SBOM + dependency audit in CI | Not started |
| — | Opt-in telemetry | Not started |

No implementation expected at v0.2.9; defer until Phase 1 distribution is stable.

---

## Priority gaps (consolidated)

### P0 — Blockers for trustworthy releases

1. **A01** — No CI (regression risk on every change)
2. **A04** — No `.env.example` (onboarding/security clarity)
3. **A05** — Hard-coded Python in `install-global.ps1`

### P1 — Phase 1 stabilization

4. **A02, A28, A29** — CI integration + install smoke runners  
5. **A06** — Align Windows installer with README (stop processes)  
6. **A08–A10, A24** — Release automation and checklist  
7. **A13, A14** — TUI batch progress and API error surfacing  
8. **A19, A20, A31** — Vault playbook, safe `plan_moves` defaults, cost docs  
9. **A22** — Central troubleshooting doc  

### P2 — Phase 2+

10. **A15, A16, A23, A30, A32** — Preview UX, undo, docs site, dependabot, CSV export  
11. **A11, A12** — PyPI/winget strategy (decision-dependent)  
12. Vault-scale: checkpoints, restore CLI, TUI categorize integration  

---

## Recommended GitHub issues

Issues created from this analysis (see [GitHub Issues](https://github.com/B0LK13/mda-cli/issues) for live numbers):

| # | Title | Priority |
|---|-------|----------|
| [#1](https://github.com/B0LK13/mda-cli/issues/1) | [P0] Add GitHub Actions CI (ruff + pytest on push/PR) | P0 |
| [#3](https://github.com/B0LK13/mda-cli/issues/3) | [P0] Add `.env.example` for API keys and MDA_* variables | P0 |
| [#5](https://github.com/B0LK13/mda-cli/issues/5) | [P0] Parameterize Python discovery in `install-global.ps1` | P0 |
| [#7](https://github.com/B0LK13/mda-cli/issues/7) | [P1] Stop running `mda` processes before Windows pip install | P1 |
| [#8](https://github.com/B0LK13/mda-cli/issues/8) | [P1] GitHub Release workflow: build wheel/sdist on version tags | P1 |
| [#2](https://github.com/B0LK13/mda-cli/issues/2) | [P1] CI smoke: `mda --check` after install on Windows and Linux | P1 |
| [#4](https://github.com/B0LK13/mda-cli/issues/4) | [P1] Optional CI job for Anthropic integration tests | P1 |
| [#6](https://github.com/B0LK13/mda-cli/issues/6) | [P1] TUI: batch progress indicator for multi-file **P** runs | P1 |
| [#9](https://github.com/B0LK13/mda-cli/issues/9) | [P1] TUI: show last API error inline (non-blocking) | P1 |
| [#10](https://github.com/B0LK13/mda-cli/issues/10) | [P1] Add `docs/VAULT-PLAYBOOK.md` (flatten → scan → plan → batch) | P1 |
| [#11](https://github.com/B0LK13/mda-cli/issues/11) | [P1] Add `docs/TROUBLESHOOTING.md` (WinError 32, imports, TUI) | P1 |
| [#12](https://github.com/B0LK13/mda-cli/issues/12) | [P1] Document cost guardrails (`--max-files`, `--max-tokens`) | P1 |
| [#13](https://github.com/B0LK13/mda-cli/issues/13) | [P2] `plan_moves`: dry-run by default; require `--apply` to move files | P2 |
| [#14](https://github.com/B0LK13/mda-cli/issues/14) | [P2] Backup manifest and `mda restore` for in-place and moves | P2 |
| [#15](https://github.com/B0LK13/mda-cli/issues/15) | [P2] Enable Dependabot for Python dependencies | P2 |

See [all open issues](https://github.com/B0LK13/mda-cli/issues).

---

## References

- [ROADMAP.md](ROADMAP.md) — phases, action IDs A01–A32, deployment plans  
- [README.md](../README.md) — user-facing install and usage  
- [CHANGELOG.md](../CHANGELOG.md) — shipped features by version  
