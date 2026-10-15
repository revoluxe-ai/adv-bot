---
cursor:
  subagentId: "bc-b6d7ca2b-966e-5d2d-94fc-2b92a12223d0"
---

# Owner contract review — product-control-context (PR #458)

PLANNING_HEAD: `22cb2e5841e76650c4694f9c2865e71e2e06f1c3`  
ORIGIN_STAGE_CURRENT: `c956e167393ab5258af5833336207cd5a339830d`

## Gates

| Gate | Result |
|------|--------|
| `npx @fission-ai/openspec@1.6.0 validate product-control-context --type change --strict` | **FAIL** — spec lacks `## ADDED Requirements` delta headers |
| `git diff --check origin/stage...HEAD` | **FAIL** — trailing whitespace in `scenario-coverage/plan.md` |
| merge-tree vs `origin/stage` | **CLEAN** (no conflicts reported) |

## Enrollment resolution (recommended contract patch)

**PRODUCT_DEFAULT_STATE:** `INHERIT_SHOP` — product row default / `NOT_ENROLLED` means *no SKU-level override*, not *opt out of shop rollout*.

**SHOP_GATE_PRECEDENCE:** Master shop gate — `shop NOT_ENROLLED` or `shop BLOCKED` ⇒ entire shop `LEGACY_NOT_ENROLLED`; **product `ENROLLED` cannot bypass**.

See coordinator RETURN for full matrix.

## Rounding

**ROUNDING_DECISION:** **B** — integer max is legacy `AdvSetting.max_price_for_order` storage compatibility. Domain should expose canonical money; `LegacyCampaignCpoAdapter` performs int conversion.

## ADR promotion

- A: yes (with enrollment patch in owner-contract)
- B: yes
- C: ownership yes; source selection remains EVIDENCE_GAP

FINAL_STATUS: **REPAIR_REQUIRED** before `READY_FOR_OWNER_PLANNING_MERGE_GO`.
