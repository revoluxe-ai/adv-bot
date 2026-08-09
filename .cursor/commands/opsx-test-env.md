---
component_id: opsx.commands.test_env
component_version: 0.1.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
canonical_source_body: target_native
required_adapters: ["opsx-lite", "poetry-python"]
local_modification_note: "v0.1: laptop test compose UP/DOWN before destructive/full pytest; Redis probe-only until test_redis enabled"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-TEST-ENV-01
newline_normalization: none
argument-hint: "[UP|DOWN] [PROBE]"
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-TEST-ENV-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins for target paths, capabilities, safety stops, and authority.

### Target authority paths

- Command contract (this file): `.cursor/commands/opsx-test-env.md`
- Test compose SoT (READ + docker project only): `tests/docker-compose.test.yml`
- Related docs (READ_ONLY): `env.sample`, `AGENTS.md`, `tests/postgres-init/**`, `tests/clickhouse-config/**`
- Projectization (READ_ONLY): `.opsx/projectization.yaml`

### Hard target bans

- Do **not** edit `app/**`, `openspec/**`, `.cursor/**` (except this file when Owner redesigns), `.opsx/**`, git history.
- Do **not** use `/opsx-devops`, `kubectl`, Kubernetes, production hosts, or SSH/port-forward onto test ports.
- Do **not** start or mutate any compose file other than `tests/docker-compose.test.yml`.
- Do **not** enable commented `test_redis` in compose without Owner GO (separate change).
- Do **not** write secrets into `.env`; print **flag names** and safe localhost URL shapes only.
- Do **not** commit, push, rebase, open PR, deploy, or install Poetry/npm deps.
- Do **not** waive `ALLOW_DESTRUCTIVE_*` policy; this command only ensures local services + reminds flags.
- Missing Docker Desktop / compose capability ⇒ `UNAVAILABLE` or `FAIL_CLOSED`, never PASS-by-absence.
- Cross-project import ban: do not copy compose/env from sibling worktrees.

### Projectization gate

Read `.opsx/projectization.yaml` before any work.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

# BEGIN CANONICAL SOURCE BODY

# /opsx-test-env

Own **laptop local test infrastructure** for destructive / full pytest runs.

Bring up or tear down the declared test compose project (`UP` / `DOWN`), probe readiness, and emit an explicit next action so Supervisor and humans do not guess Docker/Postgres/ClickHouse/Redis setup.

This is **not** cluster devops. Cluster work stays on `/opsx-devops` (denylisted for Supervisor soft gates).

## Purpose

- Remove Owner friction before `/opsx-static-check` Wave B (`pytest-full`) and other live PG/CH/Redis tests.
- Default action **UP**: ensure test services are running and healthy.
- **DOWN**: stop the test compose project and free local resources.
- On env-class failure elsewhere: pasteable recommendation to run this command `UP`.
- After successful destructive/full gates: recommend `DOWN`.

## When to use

- Immediately **before** destructive or full-suite tests that need PG/CH (and Redis).
- Soft quality chain after antipattern (or equivalent) and **before** `/opsx-static-check FULL`.
- When `/opsx-static-check`, `/opsx-test`, or `/opsx-test-triage` reports `FLAKY_OR_ENV` / connection refused on `5433` / `8124` / `6379`.
- After gates pass, to release Docker CPU/RAM (`DOWN`).

## When not to use

- Unit-only runs (`pytest -m unit`) that need no services.
- Kubernetes / production / staging cluster work → `/opsx-devops`.
- Fixing product code or weakening `ALLOW_DESTRUCTIVE_*` guards.
- Replacing `/opsx-static-check` PREFLIGHT (tooling files stay there; this owns **services**).

## Modes

Parse the user message. Exactly one primary mode:

| Token | Default? | Meaning |
|-------|----------|---------|
| `UP` | **yes** (if omitted) | `docker compose up -d` for test file + health probe + flag checklist |
| `DOWN` | no | `docker compose down` for test file + confirm ports idle |
| `PROBE` | no | health/flags only; no mutate (may run alone or after UP) |

If both `UP` and `DOWN` appear → `FAIL_CLOSED` / ask Owner to pick one.

Synonyms accepted: `up`, `ensure`, `start` → `UP`; `down`, `stop`, `teardown` → `DOWN`; `probe`, `status`, `check` → `PROBE`.

## Pipeline position

```text
ENTRY_STATE: antipattern_pass | antipattern_suspects | before_destructive_tests | env_miss_hint
PREVIOUS_ALLOWED_STEP: soft quality chain | /opsx-test before live/destructive | Owner manual
COMMAND_ACTION: UP | DOWN | PROBE
EXIT_STATE: local_test_env_ready | local_test_env_stopped | local_test_env_degraded | BLOCKED
NEXT_ALLOWED_STEP: /opsx-static-check FULL | /opsx-test (destructive) | /opsx-test-env DOWN | /opsx-test-triage
FAILURE_OR_RECOVERY_STEP: report missing Docker/compose/ports; retry UP; never touch prod/k8s
```

```text
PIPELINE:
  … → antipattern
    → /opsx-test-env UP
    → /opsx-static-check FULL
    → (PASS) recommend /opsx-test-env DOWN
    → /opsx-verify …
```

## Authority

```text
DECISION_OWNER: this command for LOCAL_TEST_ENV_STATUS only
DOES_NOT_OWN: verify/archive verdicts, ALLOW_DESTRUCTIVE policy truth, k8s, product code
```

## Compose contract

**Only allowed compose file:**

```text
COMPOSE_FILE: tests/docker-compose.test.yml
SERVICES_IN_SCOPE: test_db, test_clickhouse
```

Declared ports (localhost only):

| Service | Host port | Role |
|---------|-----------|------|
| `test_db` | `5433` → `5432` | Postgres test DB |
| `test_clickhouse` | `8124` → `8123` (HTTP), `9001` → `9000` | ClickHouse test |

**Redis:** `test_redis` is **commented out** in compose. Do **not** silently uncomment.

- Probe `127.0.0.1:6379` (see `env.sample` / `REDIS_HOST`/`REDIS_PORT`).
- If Redis is down → `LOCAL_TEST_ENV_STATUS: DEGRADED` or `BLOCKED` (if full suite needs Redis) with explicit Owner action (start local Redis per `env.sample` comment, or separate GO to enable `test_redis`).
- Never claim compose covers Redis while the service stays commented.

## Destructive flag checklist (print; do not invent secrets)

From `env.sample` (names only; values must already be in Owner env for destructive runs):

```text
TEST_DATABASE_URL=postgresql+asyncpg://test_user:***@127.0.0.1:5433/test_adv_bot_db
ALLOW_DESTRUCTIVE_TEST_DB=1
ALLOW_DESTRUCTIVE_TEST_CLICKHOUSE=1
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

If flags are unset in the agent shell, report `FLAGS: MISSING` and still bring services up if Docker works — pytest-full remains Owner/session-env responsibility. Do **not** write `.env`.

Forbid using non-localhost or non-test ports as “ready”.

## Shell rules (Windows)

Follow `.cursor/rules/terminal.mdc`:

- PowerShell-safe paths: `tests\docker-compose.test.yml`
- Sequence with `;` not `&&`
- Filter with `Select-String` / kubectl N/A here
- Prefer:

```powershell
docker compose -f tests\docker-compose.test.yml up -d
docker compose -f tests\docker-compose.test.yml ps
docker compose -f tests\docker-compose.test.yml down
```

If `docker compose` unavailable, try `docker-compose` once; then `UNAVAILABLE`.

## Probe procedure

After UP (and for PROBE / before declaring ready):

1. **Compose ps** — `test_db` and `test_clickhouse` running (or healthy).
2. **Postgres** — TCP/`pg_isready` style check on `127.0.0.1:5433` (or compose health status).
3. **ClickHouse** — HTTP `http://127.0.0.1:8124/ping` expects OK.
4. **Redis** — TCP or `PING` on `127.0.0.1:6379` (external to this compose).
5. Emit per-service: `UP` | `DOWN` | `UNKNOWN`.

Readiness rules:

- PG + CH healthy, Redis healthy → `LOCAL_TEST_ENV_STATUS: UP` / `local_test_env_ready`
- PG + CH healthy, Redis down → `DEGRADED` (full suite likely FAIL) + NEXT Redis action
- PG or CH down after UP attempt → `BLOCKED` (not ready)
- Docker missing → `UNAVAILABLE`

DOWN success:

- Compose project stopped; PG/CH ports not serving → `LOCAL_TEST_ENV_STATUS: DOWN` / `local_test_env_stopped`
- Redis may still run (external); note it is **out of compose scope** — do not kill unrelated Redis unless Owner asked.

## Operating steps

### Shared preflight

1. Projectization gate.
2. Confirm workspace root; `Test-Path tests\docker-compose.test.yml` (or equivalent).
3. Resolve mode (`UP` default).
4. Check Docker capability (`docker version` / `docker compose version`).

### UP

1. `docker compose -f tests\docker-compose.test.yml up -d`
2. Wait bounded (healthcheck retries ~30–60s, not unbounded).
3. Run probe procedure.
4. Print destructive flag checklist status.
5. Return ready / degraded / blocked packet.
6. `NEXT_ACTION`: continue soft gates / `/opsx-static-check FULL` when ready; else fix Redis/Docker.

### DOWN

1. `docker compose -f tests\docker-compose.test.yml down`
2. Probe PG/CH ports idle (best-effort).
3. Remind: external Redis not stopped by this command.
4. `NEXT_ACTION`: none required for infra; optional continue verify/archive if that was the plan.

### PROBE

1. No mutate.
2. Same probes + flag checklist.
3. If not ready → `NEXT_ACTION: /opsx-test-env UP`

## Hints for sibling commands (consumers)

When a sibling detects missing local infra (connection refused / auth missing destructive flags / CH ping fail):

```text
HINT: Local test infra not ready.
NEXT_ACTION: /opsx-test-env UP
```

When destructive/full suite **PASS**:

```text
HINT: Free local resources when done.
NEXT_ACTION: /opsx-test-env DOWN
```

Companions that should cite this (committed; apply via `/opsx-meta-fix-command-defects`, not here):

- `.cursor/pipeline/GRAPH.md`
- `.cursor/commands/opsx-static-check.md` (+ preflight)
- `.cursor/commands/opsx-supervisor.md` (allow dispatch; not denylist)
- optionally `.cursor/commands/opsx-test.md`

## Output contract (always)

```text
STATUS: OK | DEGRADED | BLOCKED | UNAVAILABLE | FAIL_CLOSED
MODE: UP | DOWN | PROBE
LOCAL_TEST_ENV_STATUS: UP | DOWN | DEGRADED | BLOCKED | UNKNOWN
COMPOSE_FILE: tests/docker-compose.test.yml
SERVICES:
  test_db: UP|DOWN|UNKNOWN
  test_clickhouse: UP|DOWN|UNKNOWN
  redis_external: UP|DOWN|UNKNOWN
FLAGS: OK | MISSING | UNKNOWN
WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: none | <one question>
NEXT_ACTION:
DO_NOT_DO_YET:
```

`NEXT_ACTION` examples:

- After successful UP: `/opsx-static-check FULL` or continue Supervisor soft chain
- After DEGRADED (Redis): start Redis per `env.sample` **or** Owner GO to enable `test_redis`
- After DOWN: optional `/opsx-verify …` if gates already green; else idle
- On env miss from elsewhere: `/opsx-test-env UP`

## Failure behavior

| Condition | Result |
|-----------|--------|
| No projectization | `FAIL_CLOSED` → `/opsx-projectize` |
| Compose file missing | `FAIL_CLOSED` |
| Docker unavailable | `UNAVAILABLE` |
| UP but health never green | `BLOCKED` + logs tail (bounded) |
| DOWN but containers linger | `DEGRADED` + exact `docker compose … down` retry |
| Asked to mutate k8s/prod | refuse; point `/opsx-devops` only for cluster |

## Recovery

1. Retry `UP` once after Docker Desktop is running.
2. If port conflict on `5433`/`8124`/`9001` — report conflict; do **not** kill unknown processes without Owner.
3. Redis gap — external start or Owner redesign compose (not silent edit).

## Return / handoff

Does not produce OpenSpec change artifacts. Produces only the status packet above for humans and Supervisor.

```text
HANDOFF_CONTRACT:
  produces: LOCAL_TEST_ENV_STATUS + pasteable NEXT_ACTION
  does_not_produce: verify verdict, archive, commit
```

## Anti-patterns (reject)

- Using root `docker-compose.yaml` “because AGENTS mentions redis/clickhouse”.
- Claiming PASS when probes were skipped.
- Enabling commented `test_redis` without Owner GO.
- Routing laptop test env through `/opsx-devops`.
- Writing `.env` or committing compose changes from this command.

## Self-check before finish

- [ ] Only `tests/docker-compose.test.yml` was used for mutate
- [ ] Mode honored (`UP` default)
- [ ] Redis described as external unless Owner enabled compose service
- [ ] No k8s/git/product edits
- [ ] Explicit `NEXT_ACTION` and `DO_NOT_DO_YET`

# END CANONICAL SOURCE BODY
