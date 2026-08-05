# Architecture Decision Lookup — wb-readonly-job-smoke-reports

## Status

Complete (no new proposed decision)

## Lookup result

Context-first lookup for ownership / layering / write-path / domain invariant
for Stage A ORDERS+sales wire on existing Reports stack:

| Concern | Result |
|---------|--------|
| Scripts Job → existing `wb/api` stack; no invent URL; Job-only API; READ_ONLY_NO_MUTATION; secret-strip L0 | Resolved by accepted `openspec/decisions/scripts-wb-api-ops-stack/decision.md` (Job path exists; this change does not own running Job) |
| Identity `ORDERS_OR_SALES_REPORTS_READ` = statistics-api supplier orders and/or sales; Stage A first page; no funnel/FBS/fullstats substitute | Resolved by accepted `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` |

**Architecture Decision Missing:** нет.

Этот change не вводит нового reusable ownership/layering/write-path/domain
invariant: sales Stage A становится обязательным вызовом уже разрешённого
surface. Placement: orchestration в `scripts/wb_api_readonly_ops`, calls через
existing Reports adapters/managers. Prod Job / archive / ledger — scripts
lane, не apply owed scope.

## Related

- Change: `wb-readonly-job-smoke-reports`
- Capability: `wb-api-read-only-preflight`
- Evolution: `wb-safe-readonly-collect` / `INC-RO-07` (live Job DoD outside
  this change's apply tasks)

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md` + cited paths)
- [x] relevant decisions cited
- [x] new decision **not** proposed (accepted decisions resolve placement)
- [x] implementation layer will match cited decisions (design/apply must verify)
