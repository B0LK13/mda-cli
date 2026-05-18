# Security

mda-cli runs locally and sends document text to configured LLM providers (Anthropic, OpenRouter). This page covers secrets handling and key rotation — not WDAC or enterprise policy.

## Secrets

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | Default provider API access |
| `OPENROUTER_API_KEY` | Fallback / alternate provider |
| `GITHUB_TOKEN` | Optional: install wheels from private GitHub Releases (see README) |

- Copy [.env.example](../.env.example) to `.env` for local development; **never commit** `.env` or keys.
- CI integration tests use `ANTHROPIC_API_KEY` from repository secrets only on `main` (optional job; failures do not block the pipeline).

## API key rotation

When a key may be exposed or you rotate credentials on a schedule:

1. **Create a new key** in the provider console (Anthropic or OpenRouter).
2. **Update local env**: edit `.env` or your shell profile; restart terminals and any running `mda` / TUI sessions.
3. **Update CI** (if used): GitHub → Settings → Secrets → update `ANTHROPIC_API_KEY`.
4. **Revoke the old key** in the provider console after confirming `mda --check` succeeds with the new key.
5. **Audit machines** that had the old key (shared PCs, backup scripts, password managers).

## Reporting issues

For security-sensitive bugs in this repository, contact the maintainer privately (do not open a public issue with keys or vault contents).

## Related docs

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — install and runtime errors
- [README.md](../README.md) — cost guardrails and env vars
