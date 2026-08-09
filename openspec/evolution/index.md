# North Star Registry

Durable index for long-term capability directions managed by
`/opsx-evolution`.

North Star cards provide planning context. They do not replace OpenSpec specs,
architecture decisions, tasks, verification, or Owner GO.

Human display is always `Title (STAR_ID)`.

## Cards

| Title | STAR_ID | Status | Card | Active increment | Depends on |
|-------|---------|--------|------|------------------|------------|
| Доступная автокампания: пауза при пустых ключах + тариф 1000₽ | `affordable-auto-pause-on-empty` | ACTIVE | [affordable-auto-pause-on-empty.md](affordable-auto-pause-on-empty.md) | `INC-PAUSE-02` | none |
| V3-only: обесточить и выпилить updater v2 | `v3-only-retire-v2` | ACTIVE | [v3-only-retire-v2.md](v3-only-retire-v2.md) | `INC-V2-MIGRATE-01` | none |

## Lookup rules

- Search this index before creating a card.
- Resolve exact card paths before any fallback search.
- Similarity never authorizes an automatic merge.
- `DOTO/WORKLOG.md` is raw notes, not this registry's source of truth.
- Keep **Depends on** in sync with each card's `DEPENDS_ON` (unidirectional DAG; no cycles).
