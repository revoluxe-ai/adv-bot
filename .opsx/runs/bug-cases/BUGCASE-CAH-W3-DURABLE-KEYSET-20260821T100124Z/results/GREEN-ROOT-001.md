TEST_ID: tests/unit/auto_updater_v3/card_ab_hold/test_w3_confirmed_flow.py::test_tp_confirm_all_does_not_shrink_durable_set_for_partial_live_read
BUG_CASE_ID: BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z
FINDING_ID: ROOT-001
COMMAND: poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_w3_confirmed_flow.py::test_tp_confirm_all_does_not_shrink_durable_set_for_partial_live_read -vv
PRODUCTION_HASH_AFTER: f4487e268ca409b108400226f6879635e6a2e111
TEST_CONTENT_SHA256: 5f913bae2700169d32c21491e53f81ae43f053b1ca2193f37dd571b3dba6f843
FROZEN_TEST_CONTENT_SHA256: 9dbd10dd7d6ef9a5523b336bdd1e7219a3605355b68327c4a0e43875fe3ea636
HASH_MATCH: NO
STATUS: GREEN_BLOCKED_PENDING_TEST_DELTA_REVIEW
TARGETED_REGRESSIONS: frozen regression passed (1 passed); adjacent unit suite passed (66 passed)
ADJACENT_COMMAND: poetry run pytest -m unit tests/unit/auto_updater_v3/card_ab_hold/test_w3_confirmed_flow.py tests/unit/auto_updater_v3/card_ab_hold/test_epoch_write_gates.py tests/unit/auto_updater_v3/card_ab_hold/test_confirmation_contracts.py -q
COMPLETENESS_GUARD: _has_complete_factual_position_read rejects a strict subset before confirm_target_places, phase/FSM transition, or durable mutation
COMPLETE_READ_INVALID_POSITION_BEHAVIOR: full authoritative presence permits explicit zero/negative/non-finite exclusion while preserving positive subset writer behavior; covered and passed
DIFF_CHECK: PASS
NON_WEAKEN_DELTA: NOT_PROVIDED; Owner approval is required for the post-RED test-source delta
FAILURE: FROZEN_TEST_HASH_MISMATCH; current authoritative test source differs from RED without approved NON_WEAKEN_DELTA
