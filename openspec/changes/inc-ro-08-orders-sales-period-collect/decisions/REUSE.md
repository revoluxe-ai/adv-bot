# Architecture Decision Lookup — inc-ro-08-orders-sales-period-collect

## Status

Complete (no new proposed decision)

## Lookup result

Context-first lookup for ownership / layering / write-path / domain invariant
for INC-RO-08 period collect + cursor/pagination on `ORDERS_OR_SALES_REPORTS_READ`:

| Concern | Result |
|---------|--------|
| Scripts Job → existing `wb/api` stack; no invent URL; Job-only API; READ_ONLY_NO_MUTATION; secret-strip L0; finite run ceiling | Resolved by accepted `openspec/decisions/scripts-wb-api-ops-stack/decision.md` |
| Identity `ORDERS_OR_SALES_REPORTS_READ` = statistics-api GET supplier orders/sales via generated Reports; honest dateFrom/cursor period; no funnel/FBS/fullstats substitute | Resolved by accepted `openspec/decisions/orders-or-sales-reports-read-identity/decision.md` |

**Architecture Decision Missing:** нет.

Этот change не вводит нового reusable ownership/layering/write-path/domain
invariant. Period collect + cursor follow — это режим orchestration поверх
уже разрешённого surface: Stage A first-page остаётся отдельным поведением;
INC-RO-08 явно следует cursor при finite ceiling и честной attestation,
что identity decision уже требует для period semantics (`dateFrom` /
`lastChangeDate`, без classic exact start+end claim).

Placement: orchestration в `scripts/wb_api_readonly_ops`; calls только через
existing Reports adapters/managers; live Job / L0 delivery — `/opsx-scripts`
lane (Supervisor may defer live Job evidence; not an apply-ready blocker).

## Related

- Change: `inc-ro-08-orders-sales-period-collect`
- Capability: `wb-api-read-only-preflight`
- Evolution: `wb-safe-readonly-collect` / `INC-RO-08`

## Review checklist

- [x] existing decisions searched (`openspec/decisions/index.md` + cited paths)
- [x] relevant decisions cited
- [x] new decision **not** proposed (accepted decisions resolve placement)
- [x] implementation layer will match cited decisions (design/apply must verify)
