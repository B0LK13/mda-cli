# Troubleshooting

## Windows: `pip install` fails with WinError 32 on `mda.exe`

Another process still has `mda` open (often a Cursor terminal or the TUI).

1. Quit the TUI and close terminals running `mda`.
2. Re-run `pwsh -File scripts\install-global.ps1` (stops `mda` / `mda-cli` / `mda-tui` before pip).
3. Or run `python -m mda_cli` with the same Python used for install.

## `No module named mda_cli`

The `mda` on PATH may point at a different Python than the one that installed the package.

- **Windows:** Re-run `scripts\install-global.ps1`; confirm `mda --check`.
- **WSL/macOS/Linux:** Run `./scripts/install-global.sh` and ensure `~/.local/bin` is on PATH.

## API key / provider errors

| Symptom | What to try |
|---------|-------------|
| Missing API key | Set `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` (see `.env.example`) |
| 402 / credits | Add credits or set `MDA_PROVIDER=openrouter` |
| 429 / rate limit | Lower `--max-files`; retry; enable `MDA_OPENROUTER_FALLBACK=1` |
| Timeout | Increase `MDA_API_TIMEOUT` (seconds) |

TUI: the status line under the log shows the **last API error** without blocking the UI.

## TUI

| Issue | Fix |
|-------|-----|
| Preview empty for PDF/DOCX | `pip install 'mda-cli[pdf]'` and/or `'mda-cli[docx]'` |
| `.doc` files | Convert to `.docx` first |
| Batch seems stuck | Watch log for `Batch N/M`; check API status line for errors |
| `NoActiveWorker` on jump/filter | Upgrade to latest `mda-cli` (0.2.5+ fix) |

## CLI batch

- `--dry-run` is not supported with `--tui`; use batch mode on files/directories.
- `--max-files` requires a directory target, not single-file mode.
- `--backup` only applies with `--in-place`.

## CI / dev

```powershell
python -m pip install -e ".[dev]"
ruff check .
pytest -q -m "not integration"
pytest -q -m integration   # needs ANTHROPIC_API_KEY
```
