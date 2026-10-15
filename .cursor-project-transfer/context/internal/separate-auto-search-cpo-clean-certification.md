---
cursor:
  subagentId: "bc-4d4236e9-5543-5d5f-94d6-e506da7e0973"
---

# SEPARATE_AUTO_SEARCH_CPO_CLEAN_CERTIFICATION_REPORT

Certification only. No live ClickHouse run, no PR, no merge, no rebase, no product edits.

```text
CLEAN_BRANCH:
cursor/separate-auto-search-cpo-clean-a089

CLEAN_HEAD:
f6c18bb76843a73a0ec929d087592d50d6dcedad

ORIGIN_STAGE:
1443649281543bc00411d9940a047037ed6d3ffd

EXPECTED_PATHS_ONLY:
YES

ANCESTOR_784f468:
YES

PRODUCT_SEMANTICS_CHANGED_BY_CLEAN_BRANCH:
NO

LEG_IDENTITY:
PASS

NO_CROSS_LEG_FALLBACK:
PASS

MISSING_NOT_ZERO:
PASS

TEST_DB_ISOLATION:
PASS

DESTRUCTIVE_FAIL_CLOSED:
PASS

UNIT_TESTS:
PASS (18 -m unit + 2 keyword UI by path)

RUFF:
PASS

PYRIGHT:
PASS (bounded, 3 files, 0 errors)

DIFF_CHECK:
PASS

LIVE_CH_RUN:
NOT_AUTHORIZED

EXTERNAL_GAP:
ONE_LIVE_ISOLATED_RUN_REQUIRED

BASELINE_RECONCILIATION:
BLOCKED_BY_STAGE_REVERT

PR_CREATED:
NO

MERGED_TO_STAGE:
NO

PRODUCTION_WRITES:
NONE

FINAL_STATUS:
CERTIFIED_PENDING_LIVE_RUN
```

## Evidence

- `git fetch origin` then `origin/cursor/separate-auto-search-cpo-clean-a089` == `f6c18bb76843a73a0ec929d087592d50d6dcedad`. Not `HEAD_MISMATCH`.
- `784f468becfffcba5118592348adf914dc994d73` is an ancestor. First-parent chain: `784f468` → merge `176d68175` (parents `784f468` + `23c0671f372f0435b13a3573ec8990b4303b3e4a`) → `f6c18bb`.
- Unique post-ancestor commit `f6c18bb` vs `176d68175` changes only:
  - `tests/integration/test_leg_cpo_ch_external_gap_seams.py`
  - `tests/support/leg_cpo_ch_seed.py`
  - `tests/unit/support/test_leg_cpo_ch_seed.py`
- Unauthorized stage fast-forward `144364928` is not an ancestor. New FF paths (`family_status.py`, `package_summary.py`, archive `2026-10-05-ai-package-full-export-contract-repair`) are absent. Overlapping AI-package blobs match `23c0671f`, not the FF.
- `origin/separate-auto-search-cpo` left at `9b97462b16120c6b900b9e57b93bda515b33787c`. Not pushed.
- Leg product files on the clean tree match `784f468` except merge incorporation of stage `23c0671f` shop-wide code in `manager.py` and `pyrightconfig_strict.json`. `leg_cpo.py` is unchanged. Feature delta vs `23c0671f` on `manager.py` is `attach_leg_cpo` only.
- Identity: `get_stats_by_adv_ids_last_days` filters `adv_id IN` and `GROUP BY adv_id`. Snapshot lookup is `stats_by_adv_id.get(auto_adv_id)` / `get(search_adv_id)`.
- No cross-leg fallback: `compute_leg_cpo` uses one stat. Search cluster bids copy `leg_snapshot.search_cpo`. Auto shelf / active-control use `auto_fact_cpo` / `auto_cpo`. Aggregate `fact_pay_for_order` stays separate (integration seam asserts Search `300/3` against aggregate `999`).
- Missing is `None`: `compute_leg_cpo(None)` returns `None`; absent `search_adv_id` yields `search_cpo is None`. UI renders `нет данных`. Unit `tests/unit/test_leg_cpo_economics.py` asserts that.
- Truncate SQL is `TRUNCATE TABLE test_adv_bot_clickhouse.full_adv_wb_stat` on the fixture `GuardedClickHouseClient`. Guard rejects `default_db`, unqualified destructive SQL, and any DB other than `test_adv_bot_clickhouse`. Endpoint allowlist: host `localhost`/`127.0.0.1`, port `8124`, opt-in `ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1`, marker `destructive_local`. Production SQL keeps `default_db.full_adv_wb_stat` and is rewritten only inside the guarded test client.
- `-m integration` and `-m fast` leave `session.items` empty for this module (not executed). `-m destructive_local` collects 10 tests; not run.
- No live isolated receipt in `openspec/changes/separate-auto-search-cpo/`. Seam module says live pytest needs `AUTHORIZE_ONE_LIVE_RUN`.
- PR #451 is OPEN (`cursor/revert-unauthorized-package-archive-a089` → `stage`). `origin/stage` is still `144364928`.

## Checks

Detached worktree at `f6c18bb` (removed after). Poetry 3.11.17 venv.

- `pytest -m unit`: 18 passed (`test_leg_cpo_economics`, `test_leg_cpo_ch_seed`, `test_leg_cpo_ch_stub_contract`, `test_leg_cpo_s10_ui_runtime_seam`).
- `tests/unit/client_bot/test_adv_keywords_leg_cpo_render.py`: 2 passed by path. `-m unit` deselects them (no explicit unit marker; auto-marker is not what `-m unit` matches).
- `ruff check` on the three files: all checks passed.
- `pyright` on the three files: 0 errors.
- `git diff --check 176d68175 f6c18bb`: clean.
