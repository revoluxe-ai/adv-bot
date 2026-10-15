---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# separate-auto-search-cpo — bounded reconciliation verification

**Repo:** `/agent/repos/adv-bot`  
**Branch:** `separate-auto-search-cpo`  
**Verified at:** 2026-10-05 (Cloud Agent)

## Git reconciliation

| Check | Result |
|-------|--------|
| `HEAD` | `176d681751d1632738d9030415443aa71cc74c8f` (matches expected) |
| `origin/stage` after fetch | `23c0671f372f0435b13a3573ec8990b4303b3e4a` (unchanged; no STAGE_MOVED) |
| `git push -u origin separate-auto-search-cpo` | Success `784f468be..176d68175` |
| `git diff --check origin/stage...HEAD` | Clean (no output) |
| `git diff --check` | Clean (no output) |

## Semantics (unchanged; tests exercised routing/UI seams only)

Aggregate CPO remains aggregate; Auto/Search explicit; consumers use matching leg; no cross-leg fallback; UI separate labels; production-write owners not modified in this verification hop.

## Tests (Poetry / pytest)

Environment bootstrapped per `.cursor/environment.json` (Python 3.11 + `poetry install`).

**Changed tests vs merge-base** `b79534379971e94e0200b50ebc6787ea96455452`: 82 paths under `tests/` (mix of unit + integration).

### Targeted leg-CPO + adjacent unit consumers

```bash
poetry run pytest -m unit <25 paths> -q --tb=line
# 345 passed, 9 deselected, exit 0

poetry run pytest tests/unit/client_bot/test_adv_keywords_leg_cpo_render.py \
  tests/unit/app/modules/shop_runner/bidder/test_v3_safety_cap.py -q --tb=line
# 9 passed (deselected under -m unit due to marker profile), exit 0

poetry run pytest -m unit tests/unit/shop_runner/ -q --tb=line
# 88 passed, exit 0
```

**Destructive gate (unit, no live DB/Docker):** `tests/unit/support/test_destructive_lifecycle.py` — 26 passed (included in first batch).

**Not run (full changed list):** stage-merge-heavy suites (`tests/unit/ai_package_v1/*`, `tests/unit/test_campaign_settings_*`, `tests/unit/test_clickhouse_migration_*`, integration PG/CH) — out of bounded leg-CPO verification slice unless listed above.

### Integration CH seam

`tests/integration/test_leg_cpo_ch_external_gap_seams.py` — **not executed** (see ClickHouse / authority below).

## Pyright

```bash
poetry run pyright-strict
# exit 1 — 7 errors in:
#   tests/unit/ai_package_v1/test_campaign_settings_contract.py (5)
#   tests/unit/ai_package_v1/test_package_zip_assembler.py (2)
```

Failures are in **stage-merge ai_package_v1 test files**, not `leg_cpo.py` / leg-CPO feature paths. No mechanical fix applied (verification-only hop).

## OpenSpec

- `poetry run openspec` — not installed.
- `poetry run check-openspec validate separate-auto-search-cpo --strict` — runs config contract only; **exit 0**, stdout: `OpenSpec config contract check passed.` (twice).
- `npx openspec validate separate-auto-search-cpo --strict` — **exit 1**, `could not determine executable to run` (no CLI in `package.json`).

## Scenario coverage (`mode=audit`)

**Command surface:** `.cursor/commands/opsx-spec-scenario-coverage.md` (no standalone repo runner; audit performed read-only against `scenario-coverage/plan.md` + executed pytest).

**Plan:** `openspec/changes/separate-auto-search-cpo/scenario-coverage/plan.md` — 10 scenarios (LEG-CPO-001 … 010).  
**Prior audit artifacts:** none (`audit.receipt.json` / `audit.report.md` absent).

| Scenario | Seam/unit evidence (this run) | Gap |
|----------|------------------------------|-----|
| LEG-CPO-001 … 010 (scenario_seam / contract) | Covered by targeted unit runs above | — |
| LEG-CPO-001 `BOUNDARY_INTEGRATION_READ` (live CH) | **NOT_EXECUTED** | Requires disposable CH + destructive opt-in + close-external-gap live auth |

**Audit verdict (bounded):** **FAIL** — CH boundary row not proven on current snapshot; durable `audit.receipt.json` not materialized. Certify not attempted (requires provider receipts).

## ClickHouse provider

- **Env (repo contract):** `CLICK_HOUSE_HOST`, `CLICKHOUSE_PORT` (allowlist HTTP **8124**), `test_adv_bot_clickhouse`, `ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1`, compose opt-in `ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1`.
- **Live close-external-gap auth:** `AUTHORIZE_ONE_LIVE_RUN` with `INDEPENDENT_REAUDIT: VERDICT: READY_FOR_ONE_AUTHORIZED_RUN` (not present; not bypassed).
- **Execution:** `docker` **not installed** on VM → cannot start `leg-cpo-ch-proof-*` container.

```text
RECONCILED_FEATURE_HEAD: 176d681751d1632738d9030415443aa71cc74c8f
PUSHED_FEATURE: yes (origin/separate-auto-search-cpo 784f468be..176d68175)

TESTS: targeted unit 442 passed (345+9+88), 0 failed, exit 0; destructive_lifecycle unit included; integration test_leg_cpo_ch_external_gap_seams NOT_RUN
PYRIGHT: exit 1, 7 errors (ai_package_v1 stage-merge tests only)
OPENSPEC: check-openspec exit 0 (config contract); openspec CLI / npx validate unavailable
SCENARIO_COVERAGE: audit FAIL — LEG-CPO-001 CH boundary NOT_EXECUTED; no audit.receipt.json on change
GIT_DIFF_CHECK: clean (both ranges)

CLICKHOUSE_PROVIDER_ENV: ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1, ALLOW_DESTRUCTIVE_TEST_SUBPROCESS=1, CLICKHOUSE_PORT=8124, CLICK_HOUSE_HOST=localhost; live also AUTHORIZE_ONE_LIVE_RUN+INDEPENDENT_REAUDIT
CLICKHOUSE_PROVIDER_EXECUTION: NOT_RUN — docker missing; AUTHORITY_GATE for live seam
FAIL

BLOCKER: pyright-strict (7 errors, unrelated ai_package_v1 tests); scenario audit CH boundary + TEST_INFRA_BLOCKER (no docker); openspec validate --strict CLI not available (config contract only PASS)
```
