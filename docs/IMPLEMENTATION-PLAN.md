# mda-cli Implementation Plan

**As of:** 2026-05-18  
**Repository:** [B0LK13/mda-cli](https://github.com/B0LK13/mda-cli) (private)  
**Strategic context:** [ROADMAP.md](ROADMAP.md) · [GAP-ANALYSIS.md](GAP-ANALYSIS.md) · [RECOMMENDATIONS.md](RECOMMENDATIONS.md) · [LOCAL-DEV.md](LOCAL-DEV.md)  
**Draft stabilization PR:** [#16](https://github.com/B0LK13/mda-cli/pull/16) (`chore/close-p0-issues`, not merged; CI blocked)

This document is the **actionable engineering plan**. It does not replace [ROADMAP.md](ROADMAP.md).

---

## 1. Current state snapshot

### Versions and branches

| Location | Version | Notes |
|----------|---------|--------|
| **GitHub `origin/main`** | **0.2.9** | Last tagged release baseline; no `.github/workflows`, no `.env.example` |
| **Local `main`** | **0.2.10** + Unreleased | 5 commits ahead of `origin/main` (merged stabilization work) |
| **Local `chore/close-p0-issues`** | Same as local `main` | 2 commits ahead of `origin/chore/close-p0-issues` (backup manifests, TUI **S** skill cycle, `LOCAL-DEV.md`) |
| **Target next release** | **0.3.0** (Milestone A) | After merge + verification; see §3 |

### Shipped capabilities (evidence-based)

| Capability | `origin/main` (0.2.9) | Local branch (0.2.10+) | Notes |
|------------|----------------------|-------------------------|--------|
| TUI folder picker (**U**), file select, **P** batch, **Ctrl+J**, **I** preview | Yes | Yes | `mda_cli/tui.py` |
| Live preview (md/txt/pdf/docx; 10k cap; debounce) | Yes | Yes | `mda_cli/preview.py`; PDF is text extract only |
| Multi-format I/O + `[documents]` extra | Yes | Yes | `mda_cli/document_io.py` |
| Bundled skills + `mda script` | Yes | Yes | MDA + `categorize-vault-notes` |
| OpenRouter + Anthropic fallback | Yes | Yes | `mda_cli/providers.py` |
| Global install (Win PS1 / Unix sh) | Partial | **Improved** | Dynamic Python + stop `mda` on Win (local only) |
| Atomic writes, `--backup`, `--json-lines` | Yes | Yes | `mda_cli/core.py` |
| **GitHub Actions CI** (ruff + pytest) | **No** | **Yes** (branch only) | `.github/workflows/ci.yml` |
| **CI smoke install** (Linux + Windows) | **No** | **Yes** (branch only) | Jobs in `ci.yml`; never green on GitHub (billing) |
| **Tag release workflow** (wheel/sdist) | **No** | **Yes** (branch only) | `.github/workflows/release.yml` |
| **Dependabot** | **No** | **Yes** (branch only) | `.github/dependabot.yml` |
| `.env.example` | **No** | **Yes** | Root |
| `docs/VAULT-PLAYBOOK.md`, `TROUBLESHOOTING.md` | **No** | **Yes** | Phase 1 docs |
| `docs/RECOMMENDATIONS.md` + issues #17–#47 | **No** | **Yes** | Tracking backlog |
| TUI batch progress (`Batch N/M`) | **No** | **Yes** | `_set_batch_progress` in `tui.py` |
| TUI inline API error line | **No** | **Yes** | `#api-status` in `tui.py` |
| `plan_moves` dry-run default + `--apply` | **No** | **Yes** | `bundled_skills/.../plan_moves.py` + tests |
| Backup **manifests** + `mda restore --list` | **No** | **Partial** | `mda_cli/backup.py`; **apply not implemented** |
| TUI skill cycle (**S**) | **No** | **Yes** (local) | Cycles bundled skills; not full picker (#27) |
| Unit tests | ~87 collected | **91 passed** (1 integration deselected) | +`test_backup.py`, `test_plan_moves.py` |
| Integration tests (live API) | Local only | Local only | `@pytest.mark.integration`; optional CI job on `main` push |

### Open GitHub issues (47 total)

| Priority (from title labels) | Count | Examples |
|------------------------------|------:|----------|
| **P0** | 4 | #1 CI, #3 `.env.example`, #5 PS1 Python, #24 `SECURITY.md` |
| **P1** | 22 | #2 smoke install, #8 releases, #6/#9 TUI, #10–#12 docs, #17–#19 distribution, #27 skill picker, #32 vault TUI, … |
| **P2** | 20 | #13–#15 (partially addressed locally), #14 restore, #28–#30 TUI polish, #39–#40 cost, #43 docs site, … |
| **Other** | 1 | Issues use area tags (`[CI]`, `[Vault]`) without P-level in title — treat as P2 unless body says otherwise |

### Done locally / not on `main` / not on GitHub

| Item | On `origin/main` | On GitHub `main` | In PR #16 branch | Local only (unpushed to `origin/chore`) |
|------|------------------|------------------|------------------|----------------------------------------|
| v0.2.10 stabilization (CI, installer, docs, TUI, `plan_moves`) | No | No | Yes (3 commits on remote branch) | Merged into local `main` |
| Backup manifests + `restore --list` | No | No | No | **Yes** (`68d7e98`, `fcc3f26`) |
| TUI **S** skill cycle | No | No | No | **Yes** |
| `docs/LOCAL-DEV.md` | No | No | No | **Yes** |
| Green CI on PR | — | — | **No** (all jobs failed ~3s; billing) | — |

**Interpretation:** Phase 1 stabilization is **implemented locally** but **not released** on GitHub `main`. Treat PR #16 + 2 local commits as the release candidate for v0.2.10, then bump to **v0.3.0** after merge, green CI (or documented local-only attestation), and issue closure.

---

## 2. Gap vs targets

### vs ROADMAP Phase 1 (Stabilize, v0.3.x)

| ROADMAP deliverable | Gap after local branch |
|---------------------|-------------------------|
| CI on push/PR | **Code done**; **not verified on GitHub** (billing) |
| GitHub Release wheels | **Workflow done**; **no tag run yet** |
| Installer resilience | **Done locally** (#5, #7) |
| `.env.example` + secrets docs | **Example done**; **#24 `SECURITY.md` still open** |
| TUI batch progress + API errors | **Done locally** (#6, #9) |
| Vault playbook + troubleshooting | **Done locally** (#10, #11) |
| Cost guardrails in README | **Done locally** (#12) |
| Dependabot | **Done locally** (#15) |
| Release checklist as repo file | **Open** → [#18](https://github.com/B0LK13/mda-cli/issues/18) |
| Private PAT wheel install doc | **Partial** → [#17](https://github.com/B0LK13/mda-cli/issues/17) |

### vs ROADMAP Phase 2 (Scale vault, v0.4.x)

| ROADMAP deliverable | Gap |
|---------------------|-----|
| Documented flatten → scan → plan → batch | Playbook exists; **TUI not integrated** (#32) |
| `plan_moves` dry-run default | **Done locally** (#13) |
| Resume checkpoints | **Missing** (#34) |
| Backup manifest + **restore apply** | **Manifest + list only** (#14) |
| Token budget warnings in json-lines | **Missing** (#40) |
| CSV export from json-lines | **Missing** (#35) |

### vs RECOMMENDATIONS top items

| ID | Status |
|----|--------|
| DIST-R1–R3 | Open (#17–#19); release mechanics local |
| CI-R1–R2 | Open (#22–#23); core CI local |
| SEC-R1 | Open (#24) — only major P0 left after merge |
| TUI-R1 | **Partial** — **S** cycles bundled skills; full picker #27 |
| TUI-R5 | Open (#31) — pre-flight confirm before large **P** |
| VAULT-R1–R4 | Open (#32–#35); playbook done |
| API-R1–R2 | Open (#39–#40) |
| PLAT-R1 | Open (#45) — macOS CI |

---

## 3. Implementation plan — three milestones

### Milestone A — Ship baseline (**v0.3.0**, ~1–2 weeks)

**Goal:** Everything in local stabilization is on `main`, attested (CI or local checklist), and tagged. Close original P0/P1 issues #1–#13, #15, and #2.

#### Merge / push strategy

| Scenario | Steps |
|----------|--------|
| **A1 — CI billing fixed** | Push local `chore/close-p0-issues` → update PR #16 → green CI → merge to `main` → tag `v0.3.0` → verify `release.yml` assets |
| **A2 — CI still blocked** | Follow [LOCAL-DEV.md](LOCAL-DEV.md): local `ruff check .`, `pytest -q -m "not integration"`, `mda --check`, Win/Linux install smoke → merge to `main` with release notes stating **local attestation** → tag `v0.3.0` → manual wheel build if needed: `python -m build` |
| **A3 — Minimal GitHub** | Push branch only; merge without CI; document attestation in `CHANGELOG.md` and [#18](https://github.com/B0LK13/mda-cli/issues/18) checklist |

**Version bump:** `pyproject.toml`, `mda_cli/__init__.py`, `CHANGELOG.md` → **0.3.0** (consolidates 0.2.10 work + local commits; one release narrative).

#### Work items (owners, files, acceptance)

| Issue | Owner | Files / areas | Acceptance criteria |
|-------|-------|---------------|---------------------|
| **#1** CI | Dev | `.github/workflows/ci.yml` | Ruff + unit pytest pass on PR/`main` **or** documented local substitute in release notes |
| **#2** Smoke install | Dev | `ci.yml`, `scripts/install-global.*` | Linux + Windows jobs run `mda --check` after install script |
| **#3** `.env.example` | Dev | `.env.example`, README | Template lists `ANTHROPIC_*`, `OPENROUTER_*`, `MDA_*`; not committed with secrets |
| **#5** PS1 Python | Dev | `scripts/install-global.ps1` | No hard-coded `Python313` path; honors `MDA_PYTHON` |
| **#6** TUI progress | Dev | `mda_cli/tui.py` | Multi-file **P** shows `Batch N/M` in log + selection label |
| **#7** Stop mda before pip | Dev | `install-global.ps1` | Script stops `mda`/`mda-cli`/`mda-tui` before upgrade |
| **#8** Release workflow | Dev | `.github/workflows/release.yml` | Tag `v0.3.0` produces wheel + sdist on GitHub Release |
| **#9** TUI API error | Dev | `mda_cli/tui.py` | Last API failure visible in `#api-status` without blocking TUI |
| **#10** Vault playbook | Dev | `docs/VAULT-PLAYBOOK.md` | flatten → scan → plan_moves → batch documented with dry-run |
| **#11** Troubleshooting | Dev | `docs/TROUBLESHOOTING.md` | WinError 32, imports, TUI crashes covered |
| **#12** Cost guardrails | Dev | README, playbook | `--max-files`, `--max-tokens`, env caps documented |
| **#13** plan_moves default | Dev | `plan_moves.py`, tests | Default dry-run; moves only with `--apply` |
| **#15** Dependabot | Dev | `.github/dependabot.yml` | Weekly pip + Actions PRs enabled |
| **#4** Integration CI | Dev | `ci.yml` | Optional: `continue-on-error` job on `main` when secret set (can defer post-0.3.0) |
| **#24** SECURITY.md | Dev | `docs/SECURITY.md` | Rotation runbook; closes last P0 doc gap |

**PR #16 closure:** Merge commit message includes `Closes #1`, `#2`, … `#13`, `#15` as in PR body. Reconcile **#14**: keep open or add comment “manifest/list shipped in 0.3.0; apply tracked for Milestone B”.

---

### Milestone B — Vault & safety (**v0.3.x**, ~3–4 weeks)

**Goal:** Safe bulk vault operations with rollback, TUI workflows, and RECOMMENDATIONS vault/TUI priorities.

| Theme | Issues / IDs | Key files | Acceptance criteria |
|-------|----------------|-----------|---------------------|
| **Restore apply** | #14, TUI-R4 | `mda_cli/backup.py`, `cli.py` | `mda restore <run_id>` restores from manifest `backup_path`; dry-run flag; tests in `test_backup.py` |
| **Checkpoint / resume** | #34, VAULT-R3 | `mda_cli/core.py`, `cli.py`, optional `~/.mda/checkpoints/` | Interrupted batch can resume; manifest or checkpoint records pending jobs |
| **TUI categorize wizard** | #32, VAULT-R1 | `mda_cli/tui.py`, script wrappers | Guided flow: pick vault → scan → plan_moves (dry-run) → optional batch |
| **plan_moves in TUI** | #13 (done), #32 | TUI + `plan_moves.py` | User sees plan output; **Apply** requires explicit confirm (#31) |
| **Skill picker** | #27, TUI-R1 | `tui.py`, `core.py` | Beyond **S** cycle: list bundled + `MDA_SKILL_DIR` with validation (#36) |
| **Pre-flight confirm** | #31, TUI-R5 | `tui.py` | Dialog when file count or estimated tokens exceed thresholds |
| **Session undo** | #30, TUI-R4 | `tui.py`, `backup.py` | Undo last in-place write from latest backup sibling |
| **Vault automation** | VAULT-R2 | `scripts/flatten_vault_md.py`, CLI | Documented `mda script` or thin wrapper command |
| **Categorize in TUI** | (skill) | TUI + bundled skill | Run categorize pipeline without leaving TUI |

**Release cadence:** v0.3.1 (restore apply), v0.3.2 (checkpoints + TUI wizard), v0.3.3 (undo + confirm).

---

### Milestone C — Distribution & polish (**v0.4.x**)

**Goal:** Broader distribution, docs site, cost visibility, platform coverage.

| Area | Issues | Deliverables |
|------|--------|--------------|
| **Distribution** | #17–#21, DIST-R4/R5 | PAT install doc, `RELEASE-CHECKLIST.md`, pinning doc, PyPI decision, winget draft |
| **Docs site** | #42–#44, DOCS-R2/R3 | `docs/README.md` index, MkDocs or Pages, optional video |
| **API / cost** | #39–#41, API-R1–R3 | Dry-run cost estimate CLI/TUI; json-lines budget warnings; provider matrix doc |
| **TUI polish** | #28–#29 | Preview scroll/search; better PDF preview |
| **Platform** | #45–#47, PLAT-R1–R3 | macOS CI smoke; portable config dir; Git Bash PATH doc |
| **CI quality** | #22–#23, #25–#26 | Coverage artifact, ruff format check, secret scanning |
| **Skills** | #37–#38 | `mda skills list`; third-party manifest design |
| **Analytics** | #35 | CSV export from json-lines |

Map remaining RECOMMENDATIONS (#17–#47) to these releases; no new issues required unless scope splits.

---

## 4. Work packages

| WP-ID | Issues / scope | Effort | Dependencies | Definition of done |
|-------|----------------|--------|--------------|-------------------|
| **WP-A1** | Merge & tag v0.3.0 (#1–#13, #15, #2, #8) | M | CI billing **or** local attestation | `main` at 0.3.0; GitHub Release assets; issues closed |
| **WP-A2** | #24 SECURITY.md | S | — | `docs/SECURITY.md` merged; linked from README |
| **WP-A3** | #18 RELEASE-CHECKLIST, #17 PAT install | S | WP-A1 | Checklist file + README install from Release URL |
| **WP-A4** | #4 optional integration CI | S | WP-A1, org secret | Job runs on `main` when key present |
| **WP-B1** | #14 restore apply | L | Manifests (done) | `mda restore RUN_ID` restores files; tests pass |
| **WP-B2** | #34 checkpoints | L | WP-B1 | Resume flag documented; integration test with fake jobs |
| **WP-B3** | #32 TUI vault wizard | L | #13, playbook | End-to-end TUI path for categorize pipeline |
| **WP-B4** | #27 skill picker + #36 validation | M | — | Pick external/bundled skill; invalid dirs rejected |
| **WP-B5** | #31 pre-flight confirm | S | WP-B3 | Large **P** runs require confirm |
| **WP-B6** | #30 session undo | M | WP-B1 | One-level undo for last in-place write in TUI |
| **WP-C1** | #20–#21 PyPI / winget | L | WP-A1 | Decision record + one distribution channel live |
| **WP-C2** | #43 docs site | L | WP-A3 | Published docs with ROADMAP/GAP/PLAN links |
| **WP-C3** | #39–#40 cost estimator + warnings | M | — | CLI dry-run estimate; json-lines warnings |
| **WP-C4** | #45 macOS CI | M | WP-A1 | `install-global.sh` + `mda --check` on macOS runner |
| **WP-C5** | #28–#29 preview UX | M | — | Scroll/search; improved PDF preview path |

**Counts:** **3 milestones**, **15 work packages** (WP-A1–A4, B1–B6, C1–C5).

---

## 5. Missing features (user-facing)

| Feature | Status | Target |
|---------|--------|--------|
| **Restore from backup** | **Partial** — `mda restore --list` + manifests; manual copy from `backup_path` | Milestone B (#14) |
| **Skill picker in TUI** | **Partial** — **S** cycles bundled skills only | Milestone B (#27) |
| **PDF preview rendering** | Text extract + 10k cap; no page layout | Milestone C (#29) |
| **Preview scroll / in-preview search** | Not implemented | Milestone C (#28) |
| **Batch undo / rollback** | Sibling `--backup` files only; no TUI undo | Milestone B (#30, #14) |
| **In-TUI categorize workflow** | CLI/`mda script` only | Milestone B (#32) |
| **Resume interrupted batch** | Not implemented | Milestone B (#34) |
| **Dry-run cost estimate before batch** | Flags exist; no estimate | Milestone C (#39) |
| **Token budget warnings in output** | Not implemented | Milestone C (#40) |
| **plan_moves safe default** | **Done locally** — dry-run + `--apply` | Ship in A |
| **CI-gated releases** | **Blocked** on GitHub billing | Milestone A |
| **PyPI / winget install** | Not available | Milestone C |
| **Legacy `.doc` processing** | Listing only; convert message | No plan (by design) |
| **Full skill picker + external dirs** | Env/CLI only | Milestone B (#36, #37) |
| **CSV batch summary** | Not implemented | Milestone C (#35) |

---

## 6. Risk & blockers

| Risk | Impact | Mitigation |
|------|--------|------------|
| **GitHub Actions billing** | PR #16 CI failed immediately (all jobs); cannot prove green pipeline on GitHub | Local attestation per [LOCAL-DEV.md](LOCAL-DEV.md); fix billing or use self-hosted runner; merge with documented manual checklist |
| **API costs at vault scale** | Large **P** runs on `ObsidianVault7` can exhaust tokens | `--max-files`, `--max-tokens`, dry-run first; Milestone C cost estimate (#39); OpenRouter fallback |
| **Legacy `.doc` format** | Users expect Word support; only `.docx` extract works | Clear errors in `document_io.py`; playbook says convert to docx/PDF |
| **Private repo distribution** | No PyPI/winget until decided | GitHub Release wheels + PAT install (#17) |
| **Move plans / wikilinks** | `plan_moves --apply` can break links | Dry-run default (done); playbook; restore in B |
| **Textual API churn** | TUI regressions | Pin `textual>=0.47`; keep `test_tui.py` |

---

## 7. Immediate next 5 tasks

1. **Verify local release candidate** (on `chore/close-p0-issues`):

   ```powershell
   cd C:\Users\Admin\Projects\mda-cli
   ruff check .
   python -m pytest -q -m "not integration"
   mda --check
   ```

2. **Push branch so PR #16 includes backup/TUI commits** (when ready; user may defer push):

   ```powershell
   git push -u origin chore/close-p0-issues
   ```

3. **Resolve GitHub Actions billing** (org/repo Settings → Billing) **or** record local attestation in PR #16 and proceed with merge per scenario A2.

4. **Add `docs/SECURITY.md`** for #24 (short rotation runbook) — can land before or with v0.3.0 merge.

5. **After merge to `main`:** bump to **0.3.0**, tag, and verify release workflow:

   ```powershell
   # After version bump in pyproject.toml + __init__.py + CHANGELOG
   git tag -a v0.3.0 -m "Phase 1 stabilization"
   git push origin main --tags
   ```

---

## Appendix A — Issue → milestone cross-reference

| Milestone | Issues |
|-----------|--------|
| **A — v0.3.0** | #1, #2, #3, #5, #6, #7, #8, #9, #10, #11, #12, #13, #15, #24 (recommended before tag) |
| **A — partial close / comment** | #14 (list/manifest only) |
| **A — defer** | #4 (optional integration CI) |
| **B — v0.3.x** | #14 (apply), #27, #30, #31, #32, #34, #36; REC: VAULT-R1–R3, TUI-R1/R4/R5 |
| **C — v0.4.x** | #17–#23, #25–#29, #33, #35, #37–#47; REC: DIST-R4/R5, DOCS-R2/R3, API-R1–R3, PLAT-R1–R3, CI-R1/R2, SEC-R2 |

### Issues addressed by local code (close on merge)

#1, #2, #3, #5, #6, #7, #8, #9, #10, #11, #12, #13, #15 — implemented on branch per PR #16 + local commits; still **open** on GitHub until merge.

---

*Maintained with ROADMAP; update after each release or milestone review.*
