# rec_system_bid_math

This folder contains a small synthetic v1 chain for bid ranking and sales-plan ranking.

## Contract

- `bid_model.py` searches for potential impressions.
- `plan_ranker.py` chooses a bid against the sales plan.
- `expected_ranked` can be aggressive.
- `plan_ranked` may choose something other than the maximum impressions bid.
- `confidence` and `uncertainty` are diagnostics of risk, not hard blockers.
- All inputs here are synthetic, with no `app/`, DB, or ClickHouse imports.

## Flow

```text
observed -> bid_model -> expected/main/test
         -> plan_ranker -> bid closer to sales plan
```

Keep this contract stable before moving the logic out of `tests/` into a real project module.
