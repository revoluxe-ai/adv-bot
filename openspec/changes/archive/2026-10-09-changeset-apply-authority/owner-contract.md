# Owner Contract — changeset-apply-authority

## Что получили (PG-only V1 — Slices A–C)

Единый **transport-independent** контракт применения `ChangeSetV1`: вызывающий код
передаёт **`ApplyRequestV1`** и **`ApplyInvocationContext`** (server-resolved principal,
shop authz). Запрос привязан к server-issued `DryRunReceiptV1` (`pd1` + `sd1_`).
**WB Sky Apply Authority** повторно валидирует, проверяет права, сравнивает `st1`,
выполняет запись через **`pg.campaign_settings_policy_v1`**, перечитывает PG state,
выдаёт **неизменяемое** `ApplyEvidenceV1`. Dry-run `OK` **не** разрешает запись.

## Зачем

Единый idempotency, evidence, stale-state protection и запрет обхода transport → writer
для in-scope policy apply.

## Неизменное

- Dry-run main spec и `ChangeSetV1` semantics без изменений.
- `campaign_settings_history` и decision experiment memory — отдельные authorities;
  Apply не владеет историей и не реализует cross-links в V1.
- Legacy writers (Excel, Telegram, shop-runner) **не** мигрированы; гонки признаются
  через `STALE_STATE`, без claim глобальной эксклюзивности.

## Вне scope этого change (отдельные будущие changes)

- WB HTTP mutation / `UNKNOWN_EXTERNAL_STATE` implementation.
- REST / MCP / Telegram Apply entrypoints.
- Production migration, deploy, legacy rewiring.

См. `openspec/evolution/changeset-apply-authority-future-boundaries.md`.

## Критерии приёмки V1 (выполнено)

- Валидный binding + свежий `st1` → `VERIFIED` + evidence + `post_state_tokens`.
- Stale / drift / mismatch / unauthorized → fail closed.
- Idempotency replay у авторизованного principal без второй PG записи.
- `UNKNOWN_INTERNAL_COMMIT` + `RECEIPT_BLOCKED_RECONCILIATION` без слепого retry.
- PG settings + evidence — одна транзакция; success только после COMMIT.

## Решения Owner

- **Option A (принято):** archive этого change на PG-only V1; D/E/F — отдельные changes.
- V1: PG-only, три bounded ops, одна транзакция.
- Transport parity (REST/MCP → один `ApplyAuthorityService`) — **будущий** change, не V1.
