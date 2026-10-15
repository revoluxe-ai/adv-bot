---
cursor:
  subagentId: "bc-3858ca46-2c84-5b6f-9c93-b00b1b3bd445"
---

# ADR certification — drr-cpo-price-semantics

**Latest certified head:** `a6c0faa2f` (consistency repair on PR #474)  
**Prior head:** `5695d21b3`

## Freshness

| Ref | Expected | Actual |
|-----|----------|--------|
| `origin/cursor/drr-cpo-price-semantics-22ef` | `5695d21b3680c1b7f821e452d7b2ff8a0679213c` | match |
| `origin/stage` | `065509c111e96aff88255db479001b9c3da3a0d0` | match |

Merge-base with stage: `065509c` (two decision-only commits on branch).

## Validation

| Check | Result |
|-------|--------|
| Index lists `drr-cpo-price-semantics` Accepted + qualifier | PASS |
| `decision.md` path resolves | PASS |
| Related decision/spec paths (4 ADRs + 2 specs) | PASS |
| `git diff 065509c..HEAD` files | Only `openspec/decisions/drr-cpo-price-semantics/decision.md`, `openspec/decisions/index.md` |
| Product code (`app/`, `tests/`) | unchanged |
| `git diff --check` | clean |
| `openspec validate drr-cpo-price-semantics` (npx @fission-ai/openspec) | N/A — not a registered change artifact |
| `poetry run openspec` | unavailable on VM |

Substitute: manual registry + reference + scope checks above.

## Independent review (Composer 2.5)

**VERDICT: PASS** — criteria A–K PASS. No HIGH semantic contradictions.

MEDIUM (documentation drift, non-blocking for ADR merge):

- `product-pricing-and-cpo-ownership` body still states catalog `PRICE_SEMANTICS_ACCEPTED = NO` without in-file V1 carve-out (index cross-links).
- `product-control-context` spec does not yet norm V1 order-value campaign CPO (future spec sync).

## Acceptance tokens

```text
PRICE_SEMANTICS_ACCEPTED = YES
PRICE_SEMANTICS_QUALIFIER = V1_ORDER_VALUE_BASIS
ORDER_VALUE_SEMANTICS_ACCEPTED = YES
```
