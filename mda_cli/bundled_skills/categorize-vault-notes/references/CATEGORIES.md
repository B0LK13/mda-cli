# Default vault taxonomy

Use these defaults unless the user provides a different map.

## Areas (`area`)

| Value | Use for |
|-------|---------|
| `inbox` | Unprocessed captures, quick notes |
| `projects` | Active outcomes with a deadline |
| `areas` | Ongoing responsibilities |
| `resources` | Reference material, how-tos |
| `archive` | Completed or inactive |

## Types (`type`)

| Value | Use for |
|-------|---------|
| `note` | General note |
| `meeting` | Meeting notes, agendas |
| `task` | Action items, checklists |
| `reference` | Stable reference |
| `daily` | Daily / journal |
| `template` | Templates |
| `meta` | Vault meta, MOCs |

## Tags (`tags`)

- Lowercase, hyphenated, no spaces.
- Prefer 1–5 tags per note; include topic and system tags (e.g. `work`, `personal`) when clear.
- Do not duplicate tags already implied by `area` and `type` unless useful for search.

## Status (`status`)

| Value | Meaning |
|-------|---------|
| `inbox` | Needs triage |
| `active` | Current |
| `archive` | Done / inactive |

## Suggested folders (`folder`)

Relative to vault root, POSIX paths:

| Pattern | When |
|---------|------|
| `00-Inbox` | `status: inbox` |
| `10-Projects/<slug>` | `area: projects` |
| `20-Areas/<slug>` | `area: areas` |
| `30-Resources/<slug>` | `area: resources` |
| `90-Archive/<year>` | `status: archive` |

`<slug>` = short kebab-case from title (max 40 chars).
