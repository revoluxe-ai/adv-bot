# Normalized RAW_INTAKE

CASE_ID: BUGCASE-CAH-CONFIRM-20260821-001
SOURCE_EXECUTION_ID: WEX-MAT-20260821-001
NORMALIZATION_STATUS: COMPLETE
DUPLICATE_OUTCOME: NEW_CASE_NO_EXISTING_CASE_MAP_ENTRY
REQUESTED_ORDER_PRESERVED: YES

## Findings

### 1. FINDING-CAH-CONFIRM-001

Target: `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_handlers.py`, around line 1075.

Concurrent or stale TP confirmation can raise `EpochWriteError` without a handler-level recovery path, causing a failed callback instead of a user-safe refresh or re-render.

### 2. FINDING-CAH-CONFIRM-002

Target: `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_screens.py`, around line 207.

W3 proposal rendering can pass unpaginated or untruncated exclusions to `edit_text`, potentially exceeding Telegram's 4096-character limit.

### 3. FINDING-CAH-CONFIRM-003

Target: `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/handlers.py`, around line 209.

`CahOpenCurrentStep` is emitted with `revision=1`, so a draft or generation greater than one can be rejected as stale or open the wrong state.

### 4. FINDING-CAH-CONFIRM-004

Target: `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_handlers.py`, around line 822.

Disabling A/B Hold and clearing the epoch are separate operations; a failure between them can leave durable state inconsistent.

### 5. FINDING-CAH-CONFIRM-005

Targets: `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/telegram/confirm_handlers.py`, around line 184, and `app/modules/shop_runner/service_manager/services/auto_updater_v3/card_ab_hold/epoch_write.py`, around line 410.

`NaN` or `Infinity` are not rejected before persistence, potentially causing JSONB serialization failure or invalid durable state.

## Scope correction

Telegram callbacks cannot be forwarded between users. Severity must not be
inflated using a callback-forwarding threat model.
