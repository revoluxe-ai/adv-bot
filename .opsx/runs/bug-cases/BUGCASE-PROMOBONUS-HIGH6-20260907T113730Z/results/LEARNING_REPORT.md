# LEARNING_REPORT — BUGCASE-PROMOBONUS-HIGH6-20260907T113730Z ROOT-001

```text
LEARNING_STATUS: COMPLETE
LEARNING_VERDICT: LOCAL_CASE_NOTE_ONLY
PROMOTION_DECISION: NONE
FULL_PACKET_REQUIRED: false
DECISION_PATH: family/LEARNING_DECISION.json
WORKER_EXECUTION_ID: WEX/FAMILY_LEARNING_WORKER/ac2d1c4849
```

## Summary

Family learning after fan-in `READY_FOR_FAMILY_CLOSURE`. Root GREEN confirmed that a leftover success-tranche with `remaining>0` and not expired keeps `campaign_usable` / overlay usable when `created_at` is older than `PROMO_LOOKBACK_DAYS` and the common pool is empty. Bounded hunt is CLEAR with no same-invariant siblings.

The defect was local: `load_campaign_ledgers` used the 90d lookback as a leftover-usable filter. Remaining + expiry already define leftover usability; this hop only dropped the local cutoff on leftover/spend load. That is a case note, not a reusable class lesson or a missing policy.

## Why not a promotion candidate

- Hunt CLEAR; no same-invariant siblings to generalize from.
- Overlay remaining+expiry semantics already exist; the 90d AND-stop was a local load-path mistake.
- No static check, project-wide hunt, testing-rule change, global rules, or superclass activation.
- Full `LEARNING_PACKET.json` is not required for `LOCAL_CASE_NOTE_ONLY`; existing stub left unchanged.

## Closure gate

`LEARNING_STAGE_INVOKED=true`, `LEARNING_STATUS=COMPLETE`, packet-free verdict `LOCAL_CASE_NOTE_ONLY` with `PROMOTION_DECISION=NONE`. Canonical decision is `family/LEARNING_DECISION.json`. Ready for `CLOSURE_OPERATOR`.
