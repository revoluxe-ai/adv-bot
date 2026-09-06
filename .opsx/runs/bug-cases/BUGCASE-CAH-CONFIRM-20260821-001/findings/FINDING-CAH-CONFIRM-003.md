# FINDING-CAH-CONFIRM-003

CASE_ID: BUGCASE-CAH-CONFIRM-20260821-001
SEQUENCE: 3
TITLE: Current-step callback revision
STATUS: GREEN_CONFIRMED
CLAIM_STATUS: CLAIMED
CLAIM_TOKEN: CLAIM-WEX-CLAIM-003-20260821-001-FINDING-CAH-CONFIRM-003
CLAIMED_BY_WORKER_EXECUTION_ID: WEX-CLAIM-003-20260821-001
DUPLICATE_OUTCOME: NEW_FINDING_NO_EXISTING_CASE_MAP_ENTRY
SOURCE: handlers.py around line 209
CLASSIFICATION: IMPLEMENTATION_BUG
FIX: GREEN_CONFIRMED

CLASSIFIER_EXECUTION_ID: WEX-CLASS-003-20260821-001
CLASSIFICATION_BASIS: The S0 renderer emits a hard-coded revision=1 while the
handler validates callbacks against the current FSM/durable generation, so a
later current-step screen can produce a stale callback.
CLASSIFICATION_EVIDENCE: .opsx/runs/bug-cases/BUGCASE-CAH-CONFIRM-20260821-001/team/packets/WEX-CLASS-003-20260821-001.out.md

## RED evidence

RED_TEST_WORKER_EXECUTION_ID: WEX-RED-003-20260821-001
TEST_ID: test_s0_open_current_step_carries_current_revision
TEST_PATH: tests/unit/auto_updater_v3/card_ab_hold/test_epoch_s0_confirm_bridge.py
TEST_CONTENT_SHA256: 591DDB19A3D95D5643E75E2104A7B6E25A9220F6F63E69993E17FB486DF6A296
RED_RESULT: RED_CONFIRMED
OBSERVED_FAILURE: expected revision 7, received revision 1
RED_EVIDENCE: results/RED-WEX-RED-003-20260821-001.md

## Implementation evidence

IMPLEMENTATION_EXECUTION_ID: WEX-EXEC-003-20260821-001
IMPLEMENTATION_EVIDENCE: results/FIX-WEX-EXEC-003-20260821-001.md
GREEN_VERIFICATION: results/GREEN-WEX-GREEN-003-20260821-001.md

## Problem

`CahOpenCurrentStep` is emitted with `revision=1`, so a draft or generation
greater than one can be rejected as stale or open the wrong state.
