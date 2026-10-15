---
cursor:
  subagentId: "bc-c0aaa0a7-b193-56a4-84ff-98691d94d8c2"
---

# SUBAGENT 3 — product-control-context planning merge readiness

**Authority:** `/agent/repos/adv-bot` @ `27086af1369d9eeb46a680019cad7b3bb3a11ff1` (PR [#458](https://github.com/revoluxe-ai/adv-bot/pull/458) planning-only).  
**Assumption:** `openspec validate … --strict` PASS (parent).

## Verdict flags

| Flag | Value |
|------|-------|
| `SCENARIO_PLAN_VALID` | **true** (substance) |
| `ADR_A_READY` | **true** |
| `ADR_B_READY` | **true** |
| `ADR_C_OWNERSHIP_READY` | **true** |
| `ADR_C_PRICE_SOURCE_RESOLVED` | **false** |
| `ADR_PROMOTION_REQUIRED_BEFORE_MERGE` | **false** |
| `PLANNING_MERGE_READY` | **false** |
| `FINAL_STATUS` | **REPAIR_REQUIRED** (durable scenario evidence + P.3) |

## Owner reverify scenario list (PR #458 body)

Owner repair explicitly required: **S19–S22**, **S07/S09** semantics, **ADR A/C** updates.

| Owner ask | Plan evidence |
|-----------|----------------|
| Shop master gate / override bypass | S19, S20 |
| OVERRIDE without profile | S21 |
| LEGACY tier when enrolled, no profiles | S09 |
| INHERIT_SHOP + shop profile | S07 |
| Domain money 0.01 RUB + legacy adapter | S22 |
| Enrollment matrix / blocked vs legacy | S06, S14, S15, S13 |

All present in `scenario-coverage/plan.md` (22 scenarios, traceability to slices A–E).

## SCENARIO_PLAN_VALID (substance)

- **Count:** `SCENARIOS_TOTAL: 22` matches table S01–S22 with GIVEN/WHEN/THEN.
- **Spec:** 20 `#### Scenario:` blocks in delta spec; plan adds engineering seams (e.g. S05 `main_nmid`, S12 stale price, S18 empty PG defaults) and covers owner-critical paths above.
- **Deferred (acceptable at planning):** spec scenarios for future ChangeSet atomic shop DRR (Slice F task 6.1) and `ProductControlContextV1` export (6.2) — not in 22-scenario matrix; **LOW** gap.
- **Minor mapping gaps:** `Catalog vs control separation`, `Same nmid different shops` — implied by ADR A / domain tasks 1.2–1.4 but no dedicated S-id; **MEDIUM** for lifecycle traceability only.

**P6 durable evidence (separate from matrix substance):** canonical pair requires `plan.receipt.json` + richer plan frontmatter (`GENERATED_FROM`, `LIFECYCLE_COVERAGE` per `SCENARIO_TEST_COVERAGE.md`). Only `plan.md` exists → `SPEC_COVERAGE_EVIDENCE_MISSING` if P6 enforced at merge.

## ADR promotion readiness

Per `openspec/decisions/index.md` + `.cursor/rules/architecture-decisions.mdc`:

- Reusable rules live as **proposed** under `openspec/changes/<change>/decisions/` before **implementation-readiness**.
- **Promotion to** `openspec/decisions/` is **on archive** (`tasks.md` P.4), not planning merge.

| ADR | Status | Planning-ready? |
|-----|--------|-----------------|
| A `product-control-aggregate-ownership` | Proposed | Yes — ownership, gates, WBCard boundary, checklist complete |
| B `campaign-product-binding-ownership` | Proposed | Yes — binding model, multi-nm fail-closed, main_nmid forbidden |
| C `product-pricing-and-cpo-ownership` | Proposed + `EVIDENCE_GAP` | Ownership/math ready; **price SoT explicitly open** |

`ADR_C_PRICE_SOURCE_RESOLVED` **must be false** until Owner accepts canonical field/semantics (table in ADR C §EVIDENCE_GAP). Owner contract §3 and tasks 4.1 align: Slice D blocked, A–C not blocked.

## Tasks ↔ scenarios

Slice mapping in plan traceability matches `tasks.md` slices A–F; governance P.2 checked; **P.3** `/opsx-planning-review` still open.

## Findings

| Severity | Finding |
|----------|---------|
| **CRITICAL** | Missing `openspec/changes/product-control-context/scenario-coverage/plan.receipt.json` — P6 / `DURABLE_PLAN_EVIDENCE` pair incomplete vs peer changes (e.g. `campaign-settings-changeset-contract`). |
| **HIGH** | — |
| **MEDIUM** | `plan.md` lacks `LIFECYCLE_COVERAGE` / `GENERATED_FROM` blocks present on merged changes; weak machine staleness checks. |
| **MEDIUM** | Two spec scenarios without explicit S-id (catalog separation, cross-shop tenancy). |
| **LOW** | `PLAN_EVIDENCE_ID` format differs from hash-style peers; cosmetic unless receipt absent. |
| **LOW** | P.3 planning-review task unchecked (expected before Slice A GO, not necessarily before Owner planning merge if Owner waives). |

## Recommendation

**Owner planning merge (semantics):** GO — matrix matches reverify and owner-contract acceptance #2.  
**Repo planning gate (OPSX P6):** NO-GO until `/opsx-spec-scenario-coverage mode=plan` materializes receipt pair (or equivalent repair).  
**Do not** promote ADRs to `openspec/decisions/` before archive; **do** keep ADR C gap explicit through Slice D.
