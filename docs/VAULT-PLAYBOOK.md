# Obsidian vault playbook (mda-cli)

Step-by-step workflow for large vaults (e.g. `E:\ObsidianVault7`). **Always dry-run before apply.**

## 1. Flatten (optional)

If notes live in nested folders, move `.md` files to the vault root first:

```powershell
python scripts\flatten_vault_md.py E:\ObsidianVault7 --dry-run
python scripts\flatten_vault_md.py E:\ObsidianVault7
```

## 2. Scan frontmatter

Inventory YAML coverage and gaps:

```powershell
mda script scan_vault --skill categorize-vault-notes -- E:\ObsidianVault7 --limit 50
```

## 3. Plan moves (dry-run by default)

Preview folder moves from `folder:` frontmatter keys:

```powershell
mda script plan_moves --skill categorize-vault-notes -- E:\ObsidianVault7
```

Apply only after review:

```powershell
mda script plan_moves --skill categorize-vault-notes -- E:\ObsidianVault7 --apply
```

## 4. Categorize / MDA batch

Start small; increase limits after sign-off:

```powershell
mda --skill categorize-vault-notes E:\ObsidianVault7 -r --max-files 5 -q
mda E:\ObsidianVault7 -r --max-files 5 --dry-run
```

Use the TUI for interactive selection: `mda` → **U** (use folder) → select files → **P**.

## 5. Verify

- Spot-check outputs and frontmatter in Obsidian.
- Re-run `scan_vault` to confirm `folder` / `area` / `tags` coverage.
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for install and API issues.

## Cost guardrails

See README **Cost guardrails** and use `--max-files` / `--max-tokens` on every pilot run.
