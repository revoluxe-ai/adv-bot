# Owner gate schemas (BF-004 / BF-V2-003)

```text
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
HOST_MODULE: .cursor/pipeline/bug-team/runtime/owner_decision_host.py
WORKER_VISIBLE_CREATE: FORBIDDEN
```

## Production GO path

```text
.tmp/opsx-bug-cases/<CASE_ID>/gates/OWNER-PRODUCTION-GO-<FINDING_ID>.json
# proof mode:
<PROOF_ROOT>/case/gates/OWNER-PRODUCTION-GO-<FINDING_ID>.json
```

## Host-only registration

Valid receipts are created only via:

```text
runtime.owner_decision_host.register_production_go(..., owner_authority_token=...)
```

Requires explicit Owner decision payload + `OWNER_AUTHORITY_TOKEN` (never written to
worker packets, DISPATCH.jsonl, ROUTE-TRACE, or reports). Receipt stores
`AUTHORITY_TOKEN_SIGNATURE` only.

Lifecycle: `ISSUED` → `RESERVED` (bound to WEX at prepare) → `CONSUMED` (after
accepted executor finalize).

```text
runtime.owner_go.create_production_go  → raises WORKER_OWNER_GO_CREATION_FORBIDDEN
```

## Closure GO

```text
gates/OWNER-FINAL-CLOSURE-<FINDING_ID>.json
runtime.owner_decision_host.register_closure_go(...)
```

Same host-authority pattern; do not weaken.
