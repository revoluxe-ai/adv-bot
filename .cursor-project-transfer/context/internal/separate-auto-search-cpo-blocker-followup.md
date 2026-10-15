---
cursor:
  subagentId: "bc-32bdaafb-bc6f-532c-901a-2eb4845c2b03"
---

# separate-auto-search-cpo blocker follow-up

**Repo:** `/agent/repos/adv-bot`  
**Branch (main worktree):** `separate-auto-search-cpo`  
**HEAD:** `176d681751d1632738d9030415443aa71cc74c8f` (verified)

## A. Pyright classification

### Main worktree (`poetry run pyright-strict`, cwd `/agent/repos/adv-bot`)

Exit code **1**, **7 errors**:

| File | Line | Message |
|------|------|---------|
| `tests/unit/ai_package_v1/test_campaign_settings_contract.py` | 88 | Type of parameter "assembler_factory" is unknown (reportUnknownParameterType) |
| `tests/unit/ai_package_v1/test_campaign_settings_contract.py` | 88 | Type annotation is missing for parameter "assembler_factory" (reportMissingParameterType) |
| `tests/unit/ai_package_v1/test_campaign_settings_contract.py` | 116 | Type of "detailed_payload" is unknown (reportUnknownVariableType) |
| `tests/unit/ai_package_v1/test_campaign_settings_contract.py` | 116 | Type of "assemble" is unknown (reportUnknownMemberType) |
| `tests/unit/ai_package_v1/test_campaign_settings_contract.py` | 117 | Argument type is unknown — corresponds to parameter "payload" in function "build_campaign_settings_snapshot_card" (reportUnknownArgumentType) |
| `tests/unit/ai_package_v1/test_package_zip_assembler.py` | 26 | "_NoOpReader" is private and used outside of the module in which it is declared (reportPrivateUsage) |
| `tests/unit/ai_package_v1/test_package_zip_assembler.py` | 27 | "_scope_for_shop" is private and used outside of the module in which it is declared (reportPrivateUsage) |

### `origin/stage` worktree comparison

- `git worktree add /tmp/adv-bot-stage origin/stage` → detached HEAD **`1443649281543bc00411d9940a047037ed6d3ffd`** (current `origin/stage` after fetch; user-cited `23c0671f…` is not current `origin/stage` tip).
- Stage pyright: `cd /tmp/adv-bot-stage && poetry run -C /agent/repos/adv-bot pyright --project /tmp/adv-bot-stage/pyrightconfig_strict.json` → exit **1**, **19 errors**.
- The **same 7 lines** (files/lines/messages above) appear in the stage report; stage additionally has 12 errors under `app/modules/ai_package_v1/export/package_summary.py`, `package_validator.py`, and other `tests/unit/ai_package_v1/*` files not present on the reconcile branch run (reconcile branch reports only 7 total).
- Worktree removed: `git worktree remove --force /tmp/adv-bot-stage`.

**Classification:** **STAGE_BASELINE_RED** — the seven reconcile-branch diagnostics are a subset of stage strict pyright; not introduced solely by reconcile.

## B. Isolated ClickHouse / destructive_local integration

### Infra

- `docker` client absent initially; installed `docker.io` (29.1.3). `dockerd` started manually (`sudo dockerd`); unprivileged `docker` required `sudo` for API.
- Ports **8124** and **5433** free before start (`netstat`).
- Owned containers:
  - `leg-cpo-ch-proof-176d681` — `clickhouse/clickhouse-server:latest`, `8124:8123`, env `CLICKHOUSE_DB=test_adv_bot_clickhouse`, `CLICKHOUSE_USER=CLICK_HOUSE_USER`, `CLICKHOUSE_PASSWORD=password`.
  - `leg-cpo-pg-proof-176d681` — `postgres:15-alpine`, `5433:5432`, test credentials matching root `conftest.py`.
- Ownership proof: `sudo docker ps --filter name=leg-cpo-ch-proof-176d681`; `curl http://127.0.0.1:8124/ping` → `Ok.`
- Schema: pytest `clickhouse_client` fixture + `apply_clickhouse_session_ddl` (no manual DDL beyond container DB/user).
- Reuse mode: `TEST_INFRA_REUSE=1` so lifecycle probes loopback endpoints without compose up/down.

### Test command (final run)

```bash
ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1 \
ALLOW_DESTRUCTIVE_TEST_DB=1 \
TEST_INFRA_REUSE=1 \
CLICKHOUSE_PORT=8124 \
CLICK_HOUSE_HOST=127.0.0.1 \
CLICK_HOUSE_USER=CLICK_HOUSE_USER \
CLICK_HOUSE_PASSWORD=password \
poetry run pytest -m "destructive_local" \
  tests/integration/test_leg_cpo_ch_external_gap_seams.py -q --tb=line
```

**Result:** exit **1** — **2 passed**, **8 failed** (assertions / constructor mismatch / asyncio loop), **0** collection/infra blockers. Log: `/tmp/leg-cpo-pytest-full.log`.

**Execution:** **FAIL** (tests ran against owned CH; not `TEST_INFRA_BLOCKER`).

### Teardown

- `sudo docker rm -f leg-cpo-ch-proof-176d681 leg-cpo-pg-proof-176d681`

## C. OpenSpec strict CLI

| Attempt | Outcome |
|---------|---------|
| `poetry run check-openspec` | Exit **0** — config contract only (not change validate). |
| `poetry run openspec validate separate-auto-search-cpo --strict` | **OPENSPEC_CLI_MISSING** — `Command not found: openspec` (no Poetry script in `pyproject.toml` beyond `check-openspec`). |
| Documented one-shot install try: `npx --yes -p openspec-extensions openspec validate separate-auto-search-cpo --strict` | Exit **0**, stdout: `Change 'separate-auto-search-cpo' is valid` |

Repo skills/commands reference bare `openspec validate "<name>" --type change --strict`; environment bootstrap only asserts `poetry run check-openspec --help`.

## Authority

- **AUTHORITY_GATE:** **NO** — runner opt-in `ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1` (+ `ALLOW_DESTRUCTIVE_TEST_DB=1` for PG-dependent cases). No `AUTHORIZE_ONE_LIVE_RUN` used.
