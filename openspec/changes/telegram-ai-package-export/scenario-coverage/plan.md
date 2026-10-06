# Scenario Coverage Plan

CHANGE_ID: telegram-ai-package-export
MODE: plan
PLAN_STATUS: ready
PLAN_EVIDENCE_ID: SCPV1-39e72d4f252d8f6f
LIFECYCLE_STATUS: DERIVED

Planning map from Derived Lifecycle and spec scenarios to unit seams.
Execution evidence is recorded by the test run, not by this file.

## Lifecycle coverage

- L1 Button and callback identity
- L2 Ownership gate
- L3 In-process duplicate lock
- L4 Read-only shop_id resolve
- L5 Canonical period and PackageZipAssembler
- L6 Telegram delivery or safe failure

LIFECYCLE_COVERAGE:

- L1 → S01 — covered
- L2 → S02, S03 — covered
- L3 → S10 — covered
- L4 → S04, S05 — covered
- L5 → S06, S07 — covered
- L6 → S07, S08, S09, S11 — covered

## Scenario seams

| ID | Spec scenario | Seam |
|---|---|---|
| S01 | Button packs the cabinet id | `build_shop_main_keyboard` |
| S02 | Foreign user is denied | `export_shop_ai_package` + PermissionError |
| S03 | Owner passes the ownership seam | handler after verify mock |
| S04 | Canonical shop id is passed through | `resolve_canonical_shop_id` and handler args |
| S05 | Broken mapping fails closed | resolve returns None |
| S06 | Exact acceptance window | `v1_shop_menu_export_period` |
| S07 | Zip document is sent | `send_document` BufferedInputFile |
| S08 | Assembler error is redacted | assemble raises RuntimeError |
| S09 | Size rejection is explicit | TelegramBadRequest file is too big |
| S10 | Second click waits outside the assembler | inflight guard |
| S11 | Transport modules do not reference writers | source scan |

SIDE_EFFECT_PROOF: S07 observes `send_document` this run. S02/S05 observe
assembler not called. S11 is forbidden-non-effect on WB/PG/CH writers.

UNRESOLVED_GAPS: none
