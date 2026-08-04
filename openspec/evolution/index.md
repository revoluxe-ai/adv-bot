# North Star Registry

Durable index for long-term capability directions managed by
`/opsx-evolution`.

North Star cards provide planning context. They do not replace OpenSpec specs,
architecture decisions, tasks, verification, or Owner GO.

Human display is always `Title (STAR_ID)`.

## Cards

| Title | STAR_ID | Status | Card | Active increment |
|-------|---------|--------|------|------------------|
| Безопасный постоянный сбор WB API-данных | `wb-safe-readonly-collect` | ACTIVE | [wb-safe-readonly-collect.md](wb-safe-readonly-collect.md) | `INC-RO-01` best-effort collect + L0 archive |

## Lookup rules

- Search this index before creating a card.
- Resolve exact card paths before any fallback search.
- Similarity never authorizes an automatic merge.
- `DOTO/WORKLOG.md` is raw notes, not this registry's source of truth.
