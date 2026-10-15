---
cursor:
  subagentId: "bc-b1403ae8-ae4a-506d-9e84-1dc2946adc71"
---

# Owner contract review — changeset-apply-authority

PR [#459](https://github.com/revoluxe-ai/adv-bot/pull/459). Reviewed `f66849b7e`; **repairs pushed** `79bf2dbc8`. Base `c956e1673`.

## Verdict

**READY_FOR_OWNER_ACCEPTANCE** after planning-only repairs (trust boundary, receipt, txn, scenarios S21–S29).

At `f66849b7e` the package was **REPAIR_REQUIRED** (client-trusted auth fields, ambiguous evidence txn, receipt ownership gaps).

## Key repairs (79bf2dbc8)

- `ApplyAuthorityService.apply(request, context)` — `ApplyInvocationContext` server-resolved
- `DryRunReceiptV1` issued by dry-run subsystem; `DryRunReceiptStore` in Slice B
- Single PG txn: settings + verification + evidence + receipt CONSUMED
- `ApplyAttemptRecord` vs immutable `ApplyEvidenceV1`
- `pd1` + `cpd1`; idempotency fingerprint includes `pd1`
- ADR: sole gate scoped to ChangeSet apply protocol only

Cross-link: [planning doc](/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-apply-authority-planning.md)
