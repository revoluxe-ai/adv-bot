# Proposal: Adv-bot historical state extractor

## Why

Forensic analysis of paid automation cases (e.g. ДИЛЕРА Aug 2026) requires a reusable
**INTERNAL** adv-bot history pack: plan/fact control inputs, keyword delivery history,
bid decisions, current PG settings snapshot, and production revision context — without
re-collecting ER-020 external WB/store outcomes.

## What Changes

- Add reusable STRICT READ_ONLY script **Adv-bot historical state extractor**
  (`scripts/adv_bot_historical_state_extractor.py`) with generic CLI selectors.
- Emit primary artifact `ADV_BOT_INTERNAL_HISTORY_<case>_<period>.zip` + SHA256 sidecar.
- Reuse read/query/ZIP patterns from `scripts/a1_baseline_v0_collect.py` and
  `scripts/ch_a1_evidence.py`; remove A1 hardcoding.
- **No** WB API collect, **no** mutations, **no** REGISTRY update in this worktree
  (parallel scripts worktree owns lifecycle integration).

## Capabilities

### New Capabilities

- `adv-bot-internal-history-extractor` — READ_ONLY export of plan_fact_stats,
  clusters_adv_stats (intraday + daily), bid_decision_log, PG CURRENT_SNAPSHOT,
  prod revision timeline.

### Modified Capabilities

- (none)

## Impact

- New script under `scripts/`; unit tests under `tests/unit/scripts/`.
- OpenSpec change artifacts only; shared scripts infra files untouched until integration phase.
