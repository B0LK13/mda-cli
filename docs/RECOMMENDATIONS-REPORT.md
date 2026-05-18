# mda-cli Recommendations Report

**Date:** 2026-05-18  
**Version:** 0.3.1 (branch `chore/close-p0-issues`)  
**Related:** [RECOMMENDATIONS.md](RECOMMENDATIONS.md) · [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) · [GitHub Issues](https://github.com/B0LK13/mda-cli/issues)

---

## Executive summary

Milestone A and most of Milestone B on `chore/close-p0-issues` are implemented locally: CI/release scaffolding, restore apply, batch checkpoints, vault-scan, token warnings, and TUI polish. **v0.3.1** adds **batch pre-flight confirmation** before **P**, **one-level TUI undo** (**U**) from the latest manifest `backup_path` entries, and this report.

Remaining high-value work: merge/tag **0.3.x**, green or documented CI, full TUI skill picker (#27), vault workflow wizard (#32), and distribution docs (#17–#19). Integration tests (#4) stay optional on `main` until billing/credentials are stable.

---

## Completed since last report (v0.3.0 → v0.3.1)

| Area | Deliverable |
|------|-------------|
| **TUI** | Pre-flight modal before batch **P** — file count, output mode, size/token warnings, Continue/Cancel |
| **TUI** | **U** undo last batch via manifest `backup_path` (in-place runs with backups) |
| **TUI** | Batch writes `~/.mda/manifests/<run_id>.json` after each **P** run |
| **CLI** | `mda restore <run_id> --apply --yes` (v0.3.0) |
| **CLI** | `--checkpoint`, `mda vault-scan`, `warn_large_inputs` with `--max-tokens` |
| **Docs** | `docs/SECURITY.md`, `docs/LOCAL-DEV.md`, vault playbook & troubleshooting |
| **Quality** | Ruff + unit pytest in CI workflow (billing may block GitHub runs) |

---

## Open GitHub issues still relevant

| Issue | Priority | Topic | Notes |
|-------|----------|-------|-------|
| [#4](https://github.com/B0LK13/mda-cli/issues/4) | P1 | Integration CI | Optional job on `main`; needs API key + runner budget |
| [#14](https://github.com/B0LK13/mda-cli/issues/14) | P2 | Restore / rollback | **Largely done** — `restore --list` + `--apply`; TUI undo in 0.3.1 |
| [#17](https://github.com/B0LK13/mda-cli/issues/17)–[#21](https://github.com/B0LK13/mda-cli/issues/21) | P1–P2 | Distribution | Private wheel install, release checklist, pinning, PyPI/winget |
| [#22](https://github.com/B0LK13/mda-cli/issues/22)–[#23](https://github.com/B0LK13/mda-cli/issues/23) | P2 | CI quality | Coverage artifact, `ruff format --check` |
| [#25](https://github.com/B0LK13/mda-cli/issues/25)–[#26](https://github.com/B0LK13/mda-cli/issues/26) | P2–P1 | Security | Secret scanning; CI must not echo API keys |
| [#27](https://github.com/B0LK13/mda-cli/issues/27) | P1 | TUI skill picker | **S** cycles skills; full picker still open |
| [#28](https://github.com/B0LK13/mda-cli/issues/28)–[#29](https://github.com/B0LK13/mda-cli/issues/29) | P2 | TUI preview | Scroll/search; richer PDF preview |
| [#30](https://github.com/B0LK13/mda-cli/issues/30) | P2 | TUI undo | **Addressed in 0.3.1** for manifest-backed in-place batches |
| [#31](https://github.com/B0LK13/mda-cli/issues/31) | P1 | Pre-flight confirm | **Addressed in 0.3.1** |
| [#32](https://github.com/B0LK13/mda-cli/issues/32)–[#34](https://github.com/B0LK13/mda-cli/issues/34) | P1–P2 | Vault ops | Guided vault workflow; flatten wrapper; resume checkpoints |
| [#35](https://github.com/B0LK13/mda-cli/issues/35)–[#47](https://github.com/B0LK13/mda-cli/issues/47) | P2 | API cost, docs, providers | Token dashboards, docs site, multi-provider polish |

---

## Follow-up actions

| Action | Priority | Issue ref | Owner |
|--------|----------|-----------|-------|
| Merge `chore/close-p0-issues`, tag **v0.3.1**, publish release wheel | P0 | #8, #16 | Maintainer |
| Resolve or document CI billing; run smoke on Linux + Windows | P0 | #1, #2 | Maintainer |
| Close #30, #31 after verifying TUI preflight + undo in pilot | P1 | #30, #31 | Dev |
| Ship `docs/RELEASE-CHECKLIST.md` and private wheel install docs | P1 | #17, #18 | Dev |
| TUI skill picker (beyond **S** cycle) | P1 | #27 | Dev |
| Vault workflow wizard (flatten → scan → plan → MDA) | P1 | #32 | Dev |
| Enable integration job when `ANTHROPIC_API_KEY` available | P1 | #4 | DevOps |
| Coverage + format in CI | P2 | #22, #23 | Dev |
| Secret scanning in CI | P2 | #25 | DevOps |
| Evaluate PyPI vs private-only distribution | P2 | #20 | Product |

---

## IMPLEMENTATION-PLAN progress (WP snapshot)

| Work package | Status |
|--------------|--------|
| WP-A1 stabilization | ✅ Local |
| WP-B1 restore apply | ✅ |
| WP-B2 checkpoints | ✅ |
| WP-B3 vault-scan | ✅ |
| WP-B4 pre-flight (#31) | ✅ v0.3.1 |
| WP-B5 token warnings | ✅ |
| WP-B6 session undo (#30) | ✅ v0.3.1 (manifest / in-place) |
| WP-C distribution & docs | ⬜ |

See [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) for full sequencing and evidence tables.
