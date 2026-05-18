# mda-cli Recommendations

**Baseline:** v0.2.9 (main); stabilization draft in [PR #16](https://github.com/B0LK13/mda-cli/pull/16) (`chore/close-p0-issues`, targets v0.2.10)  
**Related:** [ROADMAP.md](ROADMAP.md) · [GAP-ANALYSIS.md](GAP-ANALYSIS.md) · [GitHub Issues](https://github.com/B0LK13/mda-cli/issues)

This document groups follow-on work by **topic**. Each recommendation has priority **P0/P1/P2** and effort **S/M/L**. Items already tracked as issues [#1–#15](https://github.com/B0LK13/mda-cli/issues) are listed for context only—do not open duplicate issues; link **Related to #N** instead.

---

## Distribution & releases

GitHub Releases and install hardening are in flight via PR #16. Next steps focus on how users pin versions, install from private assets, and eventually reach PyPI/winget.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **DIST-R1** | P1 | S | Document `pip install` from private GitHub Release wheel URL (PAT, extras `[documents]`) in README and release notes (ROADMAP A10). | [#17](https://github.com/B0LK13/mda-cli/issues/17) |
| **DIST-R2** | P1 | S | Add `docs/RELEASE-CHECKLIST.md` copied from ROADMAP §6 template (ROADMAP A24). | [#18](https://github.com/B0LK13/mda-cli/issues/18) |
| **DIST-R3** | P1 | S | Document version pinning and rollback: `pip install mda-cli==x.y.z`, reinstall scripts (ROADMAP §5e). | [#19](https://github.com/B0LK13/mda-cli/issues/19) |
| **DIST-R4** | P2 | M | Evaluate PyPI publish vs private-only distribution (ROADMAP A11, Q1/Q2). | [#20](https://github.com/B0LK13/mda-cli/issues/20) |
| **DIST-R5** | P2 | L | Draft winget manifest or defer with decision record (ROADMAP A12, Phase 3). | [#21](https://github.com/B0LK13/mda-cli/issues/21) |
| — | P1 | M | Tag-driven wheel/sdist on `v*` tags. | **Related to #8** (PR #16) |
| — | P0 | M | Parameterize Windows Python discovery. | **Related to #5** (PR #16) |
| — | P1 | S | Stop `mda` processes before Windows pip. | **Related to #7** (PR #16) |

---

## CI & quality

Core CI lands in PR #16. Remaining gaps: install smoke on runners, optional integration, and coverage visibility.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **CI-R1** | P2 | M | Publish pytest coverage summary (and optional `coverage.xml` artifact) on PR CI. | [#22](https://github.com/B0LK13/mda-cli/issues/22) |
| **CI-R2** | P2 | S | Add `ruff format --check` or format job alongside lint (if not already enforced). | [#23](https://github.com/B0LK13/mda-cli/issues/23) |
| — | P0 | M | GitHub Actions: ruff + pytest on push/PR. | **Related to #1** (PR #16) |
| — | P1 | M | CI smoke: `mda --check` after install on Windows and Linux. | **Related to #2** (PR #16) |
| — | P1 | M | Optional CI job for Anthropic integration tests. | **Related to #4** (deferred) |
| — | P2 | S | Dependabot for pip and GitHub Actions. | **Related to #15** (PR #16) |

---

## Security & secrets

`.env.example` and env-only keys are addressed in PR #16. Focus on rotation process and automated leak prevention.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **SEC-R1** | P0 | S | Add `docs/SECURITY.md`: key rotation steps, never commit `.env`, revoke leaked keys (ROADMAP A03). | [#24](https://github.com/B0LK13/mda-cli/issues/24) |
| **SEC-R2** | P2 | M | CI secret scanning (e.g. gitleaks/trufflehog) on push/PR; fail on high-confidence findings. | [#25](https://github.com/B0LK13/mda-cli/issues/25) |
| **SEC-R3** | P1 | S | Document that CI/workflows must not echo `ANTHROPIC_*` / `OPENROUTER_*`; use GitHub secrets only. | [#26](https://github.com/B0LK13/mda-cli/issues/26) |
| — | P0 | S | Ship `.env.example` for API keys and `MDA_*`. | **Related to #3** (PR #16) |

---

## TUI & UX

PR #16 adds batch `N/M` progress and inline API errors. Larger UX items remain: skill selection, preview depth, undo, and restore/checkpoints.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **TUI-R1** | P1 | L | TUI skill picker: choose bundled or `MDA_SKILL_DIR` skill without CLI env juggling. | [#27](https://github.com/B0LK13/mda-cli/issues/27) |
| **TUI-R2** | P2 | M | Preview: scrollable buffer and in-preview search for long notes (ROADMAP A15). | [#28](https://github.com/B0LK13/mda-cli/issues/28) |
| **TUI-R3** | P2 | M | Preview: improve PDF rendering (page-aware or thumbnail) beyond plain-text extract cap. | [#29](https://github.com/B0LK13/mda-cli/issues/29) |
| **TUI-R4** | P2 | L | Session-level undo for last in-place write using backup sibling (ROADMAP A16). | [#30](https://github.com/B0LK13/mda-cli/issues/30) |
| **TUI-R5** | P1 | S | Pre-flight confirmation before **P** when file count or estimated tokens exceed thresholds. | [#31](https://github.com/B0LK13/mda-cli/issues/31) |
| — | P1 | M | Batch progress indicator for multi-file **P**. | **Related to #6** (PR #16) |
| — | P1 | S | Show last API error inline (non-blocking). | **Related to #9** (PR #16) |
| — | P2 | L | Backup manifest and `mda restore` for moves and in-place. | **Related to #14** (deferred) |

---

## Vault operations

Playbook and safer `plan_moves` defaults ship in PR #16. Scale work: TUI pipelines, checkpoints, and batch analytics.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **VAULT-R1** | P1 | L | TUI vault workflow: guided flatten → scan → plan_moves (dry-run) → batch categorize/MDA. | [#32](https://github.com/B0LK13/mda-cli/issues/32) |
| **VAULT-R2** | P2 | M | Promote `scripts/flatten_vault_md.py` to documented `mda script` entry or subcommand wrapper. | [#33](https://github.com/B0LK13/mda-cli/issues/33) |
| **VAULT-R3** | P1 | L | Resume checkpoints for interrupted batch runs (`--checkpoint-dir`, resume flag). | [#34](https://github.com/B0LK13/mda-cli/issues/34) |
| **VAULT-R4** | P2 | M | Export batch summary CSV from `--json-lines` (ROADMAP A32). | [#35](https://github.com/B0LK13/mda-cli/issues/35) |
| — | P1 | M | `docs/VAULT-PLAYBOOK.md` pipeline. | **Related to #10** (PR #16) |
| — | P2 | M | `plan_moves` dry-run by default; `--apply` to move. | **Related to #13** (PR #16) |

---

## Skills & extensibility

Bundled MDA and categorize skills are stable; external skills need validation, discovery, and a long-term registry story.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **SKILL-R1** | P1 | M | Validate external skill directories (`--skill-dir` / `MDA_SKILL_DIR`): required files, clear errors. | [#36](https://github.com/B0LK13/mda-cli/issues/36) |
| **SKILL-R2** | P2 | S | `mda skills list` (bundled + discovered external paths, versions). | [#37](https://github.com/B0LK13/mda-cli/issues/37) |
| **SKILL-R3** | P2 | L | Design optional third-party skill manifest format (local index; marketplace out of scope). | [#38](https://github.com/B0LK13/mda-cli/issues/38) |

---

## API & cost

Cost flags exist; users need estimates before spend and structured warnings during batch.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **API-R1** | P1 | M | Dry-run cost estimate: approximate tokens × list price before batch (CLI + TUI). | [#39](https://github.com/B0LK13/mda-cli/issues/39) |
| **API-R2** | P1 | M | Emit budget warnings in `--json-lines` when approaching `--max-tokens` (ROADMAP Phase 2). | [#40](https://github.com/B0LK13/mda-cli/issues/40) |
| **API-R3** | P2 | S | Document provider routing matrix (Anthropic primary, OpenRouter fallback, env flags). | [#41](https://github.com/B0LK13/mda-cli/issues/41) |
| — | P1 | S | Document cost guardrails (`--max-files`, `--max-tokens`). | **Related to #12** (PR #16) |

---

## Documentation

Troubleshooting and vault playbook land in PR #16. Broader docs site and onboarding media remain.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **DOCS-R1** | P2 | S | Add `docs/README.md` index linking ROADMAP, GAP, playbooks, RECOMMENDATIONS. | [#42](https://github.com/B0LK13/mda-cli/issues/42) |
| **DOCS-R2** | P2 | L | MkDocs or GitHub Pages site (ROADMAP A23, Q5). | [#43](https://github.com/B0LK13/mda-cli/issues/43) |
| **DOCS-R3** | P2 | L | Record short video quickstart: install → TUI → dry-run vault pilot. | [#44](https://github.com/B0LK13/mda-cli/issues/44) |
| — | P1 | M | `docs/TROUBLESHOOTING.md`. | **Related to #11** (PR #16) |

---

## Platform

Windows and WSL are primary; macOS CI and portable config paths reduce friction on other machines.

| ID | Priority | Effort | Recommendation | Tracking |
|----|----------|--------|----------------|----------|
| **PLAT-R1** | P1 | M | macOS GitHub Actions job: `install-global.sh` + `mda --check` (ROADMAP A07). | [#45](https://github.com/B0LK13/mda-cli/issues/45) |
| **PLAT-R2** | P1 | M | Portable config directory (`XDG_CONFIG_HOME` / `%APPDATA%/mda-cli`) for skills overrides and checkpoints. | [#46](https://github.com/B0LK13/mda-cli/issues/46) |
| **PLAT-R3** | P2 | S | Document Git Bash on Windows: PATH to `~/.local/bin` or `python -m mda_cli`. | [#47](https://github.com/B0LK13/mda-cli/issues/47) |

---

## Deferred / PR #16 follow-ups

Work intentionally left open after [PR #16](https://github.com/B0LK13/mda-cli/pull/16). **Do not duplicate** these issues—track progress there.

| Item | Issue | Notes |
|------|-------|-------|
| CI install smoke (Win + Linux) | [#2](https://github.com/B0LK13/mda-cli/issues/2) | In PR #16 (`smoke-install-*` CI jobs) |
| Optional Anthropic integration CI | [#4](https://github.com/B0LK13/mda-cli/issues/4) | Nightly or `workflow_dispatch`; ROADMAP Q6 |
| Backup manifest + `mda restore` | [#14](https://github.com/B0LK13/mda-cli/issues/14) | Phase 2; pairs with TUI-R4 |
| Post-merge: tag `v0.2.10` and verify release workflow | — | Operational; see PR #16 test plan |
| Close #1–#3, #5–#13, #15, #2 when PR #16 merges | — | Use `Closes #N` in merge commit |

---

## Summary counts

| Metric | Count |
|--------|------:|
| Topics | 10 |
| New recommendations (issues to file) | 31 |
| Already tracked (#1–#15 / PR #16) | 15 |
| Deferred explicit (#4, #14) | 2 |

*Last updated: 2026-05-18*
