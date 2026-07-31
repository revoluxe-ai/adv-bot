# OD-05 broad-enable readiness — card A/B Hold (§25.3)

**Status:** OPEN — owner has **not** accepted OD-05; broad enable for all paid users is blocked.  
**Code gate:** `CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED` (default unset/false)  
**Readiness API:** `evaluate_card_ab_hold_broad_enable_readiness()` in `card_ab_hold/feature_flag.py`  
**Spec:** Broad enablement is gated behind owner manual test, limited beta, and an explicit owner decision

## What OD-05 means

Accepting OD-05 authorizes **broad** epoch-managed A/B Hold for all paid users (when master flag is also ON). Until then:

| Path | Allowed without OD-05? |
|------|-------------------------|
| Master flag OFF | No epoch entry |
| Master flag ON + empty allowlist | No epoch entry (fail-closed) |
| Master flag ON + adv/shop allowlist hit | Limited beta / owner pilot only |
| `CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED=true` | Broad enable authorized in code |

Allowlist and beta **must not** be treated as broad enablement.

## Preconditions before accepting OD-05

1. [ ] Owner manual test checklist PASS — `rollout/owner-manual-test-checklist.md`
2. [ ] Limited opt-in beta run with structured feedback reviewed
3. [ ] Explicit owner sign-off recorded below (who / when / why)
4. [ ] Prod/staging: set `CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED=true` **only after** steps 1–3
5. [ ] Optional: clear allowlists once broad is intentional (or keep as no-op overlay)

## Runtime readiness check

Before flipping the env in any environment, run (or equivalent unit assertion):

```python
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.feature_flag import (
    evaluate_card_ab_hold_broad_enable_readiness,
)

snap = evaluate_card_ab_hold_broad_enable_readiness()
# Without OD-05: snap.broad_enable_allowed is False and blocking_reasons cites OD-05.
```

## Owner sign-off (fill only when accepting OD-05)

| Field | Value |
|-------|-------|
| Decision | OD-05 ACCEPT / REJECT (leave blank while OPEN) |
| Owner | |
| Date (UTC) | |
| Evidence (checklist PASS + beta notes) | |
| Env attestation | `CARD_AB_HOLD_OD05_BROAD_ENABLE_ACCEPTED` set where? |

**While this status is OPEN:** do not set the OD-05 env to true in production.
