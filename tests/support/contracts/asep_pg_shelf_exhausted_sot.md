# ASEP PG shelf-exhausted SoT — reviewed ContractCases

```text
CONTRACT_ID: asep.pg.shelf_exhausted_sot.v1
CONTRACT_SHA: c2cd4a7b7f04e23c73a7ae5ecfd54540d5d0e5500c67be7d6528129842a48419
CHANGE_ID: auto-shelf-exhausted-pause-retest
SOURCE: SCENARIO_REFACTOR_AND_TEST_PACKET (opsx-close-external-gap)
```

Semantic expectations below MUST NOT be rewritten from live provider output.

## CASES

### latch_write_read

- intent: WRITE then PURE_READ
- given: `AutoShelfBidControlState` row exists; `shelf_exhausted_pause_active=false`
- when: `AutoShelfBidControlRepository.latch_shelf_exhausted_pause_in_session(...)`
  (production path uses `sm(read_only=False)` then handoff)
- then: `get_state_in_session` → `active=true`, `due_at` + `resolve_cpo_kind/value`
  persisted; no WB pause in this boundary

### clear_write_read

- intent: WRITE then PURE_READ
- given: active our-block with `notify_sent_at` set
- when: `clear_shelf_exhausted_pause_in_session`
- then: `active=false`; `due_at=null`; `notify_sent_at=null`; `epoch_pending=true`;
  resolve/epoch_start retained

### epoch_write_read

- intent: WRITE then PURE_READ
- given: `epoch_pending=true` after clear
- when: `mark_shelf_exhausted_epoch_started_in_session`
- then: `epoch_start` set; `epoch_pending=false`

### keep_block_no_clear

- intent: PURE_READ persistence
- given: active block; interval not due; no plan fit
- when: `get_state_in_session` observe (tick MUST NOT clear)
- then: `shelf_exhausted_pause_active` remains true

### default_retest_interval_settings

- intent: PURE_READ (settings) / optional create WRITE
- given: settings row with default / unset override
- when: read `AutoShelfBidControlSettings.retest_interval_days`
  (or `get_or_create_settings_in_session` default wiring)
- then: effective interval days == 7

## SESSION_MODE

- latch/clear/epoch WRITE: `get_session_maker(read_only=False)` → `*_in_session`
- get_state / settings READ: `get_session_maker(read_only=True)` → `*_in_session`
- settings create WRITE: `get_session_maker(read_only=False)` (no bare `sm()`)

## FORBIDDEN

- AsyncMock session as sole PG proof
- bare `get_session_maker()` without explicit `read_only=`
