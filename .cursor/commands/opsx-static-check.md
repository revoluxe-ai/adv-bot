---
description: "Единая read-only точка статических проверок: MODE=FULL|FAST; optional FROM_WAVE=U resume; сводный отчёт."
argument-hint: "[FAST|FULL] [PREFLIGHT] [FROM_WAVE=U] [A_REUSE_FINGERPRINT=<id>]"
---

# /opsx-static-check

Единая точка статических проверок.

Оркестратор читает registry, запускает Task workers параллельно (fan-out), собирает packets (fan-in), синтезирует пересечения и печатает STATUS + PROBLEMS + один NEXT_ACTION.

SoT инфраструктуры: `.cursor/static-check/`.
Методология расширения: skill `opsx-static-check-infra` (не во время обычного check-run).

## Язык

Пояснения — на русском. Токены STATUS/MODE/CHECK_ID/пути — на английском.

## User input

```text
$ARGUMENTS
```

Разбор токенов (порядок свободный):

| Token | Effect |
|-------|--------|
| (нет MODE) / `FULL` | `MODE=FULL` |
| `FAST` | `MODE=FAST` |
| `PREFLIGHT` | run optional env preflight before fan-out |
| `FROM_WAVE=U` | resume profile: skip Wave A, start from Wave U (only with A-reuse proof) |
| `A_REUSE_FINGERPRINT=<id>` | proof token for `FROM_WAVE=U` (must match current working-tree fingerprint) |
| иное неизвестное | `STATUS=BLOCKED`, не запускать agents |

Примеры:

- `/opsx-static-check` → FULL, **без** preflight
- `/opsx-static-check FAST` → FAST, без preflight
- `/opsx-static-check FULL PREFLIGHT` → FULL + preflight
- `/opsx-static-check PREFLIGHT FAST` → FAST + preflight
- `/opsx-static-check FULL FROM_WAVE=U A_REUSE_FINGERPRINT=<id>` → resume from Wave U (A reused)

## Purpose / boundaries

Read-only quality gate. Не заменяет `/opsx-verify`, `/opsx-fix-types`, `/opsx-test-triage`, targeted gates в `/opsx-apply`.

### Hard rules (абсолютно)

- **READ_ONLY end-to-end:** не изменять никакие файлы репозитория.
- Запрещено «чинить» даже инфраструктуру check-команды: `.cursor/commands/opsx-static-check.md`, `.cursor/static-check/**`, skills/rules этой подсистемы, `bin/run.sh`, configs.
- Не автофиксить production/tests.
- Не объявлять archive `GO`/`NO_GO`.
- Не создавать durable artifacts по умолчанию.
- При BLOCKED/FAIL: только отчёт + NEXT ACTION для **человека** / другой команды. **Этот** run ничего не патчит.
- **Completion gate:** run считается незавершённым, пока **оркестратор** не
  напечатал блок Final report (`STATUS` + `CHECKS` + `NEXT ACTION`) в **своём**
  ответе пользователю. Не финальный ответ:
  - «жду packets» / progress / `WORKER READY` alone;
  - system notification о завершении Task/subagent;
  - сырой worker packet / `RAW_TAIL` субагента (в т.ч. в Agent Team UI).
  Notification «pytest-* FAIL» **≠** Final report. После закрытия последней
  wave оркестратор **в том же ходе** (сразу после записи последнего packet)
  обязан сделать fan-in → synthesis → Final report — нельзя «просто остановиться».

Shared contracts: `.cursor/commands/opsx-source-resolution.md`, `.cursor/commands/opsx-execution-preflight.md` (общий opsx preflight ≠ optional PREFLIGHT этой команды).

**Local test services (soft, not this command):** optional token `PREFLIGHT` checks
tooling files only — it does **not** bring up Docker services. Before FULL /
`pytest-destructive` / live PG|CH|Redis integration, soft-recommend
`/opsx-test-env UP` (`tests/docker-compose.test.yml`: PG `5433`, CH `8124`;
Redis external `:6379` while compose `test_redis` remains commented — UP may be
`DEGRADED` until Redis is available). Env-class FAIL in Final → NEXT from
`contracts/synthesis.md` (`/opsx-test-env UP`, not ad-hoc root compose /
`/opsx-devops`). After FULL `PASS` with live services: soft advisory
`/opsx-test-env DOWN`. This command never mutates compose or starts Redis.

## Steps

### 1. Load registry

Read `.cursor/static-check/registry.yaml` and `.cursor/static-check/contracts/synthesis.md`.

If `FROM_WAVE=U` is present:

- require `A_REUSE_FINGERPRINT=<id>`; else `STATUS=BLOCKED`;
- compute current working-tree fingerprint using the same snapshot method as
  orchestrator status inventory;
- allow resume only when fingerprint matches and there is accepted evidence in
  the current conversation that Wave A (`pyright-strict`, `mypy`,
  `pytest-targeted`) is `PASS` for that same fingerprint;
- otherwise `STATUS=BLOCKED` with `NEXT ACTION`: run full `/opsx-static-check`.

Resume profile scope:

- `FROM_WAVE=U` executes only `pytest-unit` → `pytest-integration` →
  `pytest-destructive` cascade.
- Wave A checks are marked `SKIPPED (A_REUSED)` in final CHECKS.

Announce:

```text
STATIC CHECK
MODE: FULL|FAST
PREFLIGHT: off|on
Parallel plan: <waves from registry>
Checks: [ ] ...
A_REUSED: yes|no (fingerprint=<id|n/a>)
```

### 2. Optional PREFLIGHT (default OFF)

**По умолчанию шаг пропускается** (`PREFLIGHT: off`).

Выполнять `.cursor/static-check/base/preflight.md` **только** если в `$ARGUMENTS` есть точный токен `PREFLIGHT`.

`PREFLIGHT` ≠ `/opsx-test-env`: preflight = tooling/files probe; services =
`/opsx-test-env UP` (separate Owner step before FULL/destructive when needed).

Если `PREFLIGHT` задан и probe fail → STOP:

- `STATUS=BLOCKED`
- Problem / Cause / Action
- **не** запускать workers
- **не** править файлы

Если `PREFLIGHT` не задан → сразу launch (`SERIAL_ORCHESTRATOR` default).

### 3. Launch (from registry waves)

#### Default: `SERIAL_ORCHESTRATOR` (no nested Task)

Unless the Owner message contains the **exact** token `PARALLEL_TASKS`:

1. Do **not** call the Cursor Task tool for any static-check worker.
2. The **parent orchestrator** runs every scheduled check itself via Shell:
   `bash .cursor/static-check/bin/run.sh -- <canonical command from instructions>`
   (see `base/shell.md`), in **cascade order** for the mode, applying
   hard-stop / SKIPPED rules between steps.
3. Load shared contracts + each pack `instructions.md` / `context.md` in the
   parent context before that check's Shell.
4. Emit each worker packet yourself (same schema as Task workers).
5. Registry `task_type` and wave `parallel` are **ignored** under this default
   (documented for the optional parallel path only). See `registry.yaml`
   `default_launch: SERIAL_ORCHESTRATOR`.

FULL cascade order (example): pyright-strict → mypy → pytest-targeted →
pytest-unit → pytest-integration → pytest-destructive.

**pytest-unit under SERIAL (and always):** mandatory stale-pytest hygiene
before run; classify xdist worker-death / `INTERNALERROR` / exit ∈ {2,3}
**without** failed node ids as `ERROR` (`infra_suite`); then hygiene again +
**one** Shell re-run. Emit
`WORKER INFRA RETRY: pytest-unit → orchestrator-shell`. Do not route solely
to `/opsx-test-triage` for worker-death without failed nodes.
Hygiene must kill only eligible pre-run orphans (outside current run tree); if
probe ownership is ambiguous, return `blocked_hygiene_ambiguous` (no blind kill).
If xdist retry is exhausted with another infra death (still no failed nodes),
run one deterministic non-xdist classifier (`poetry run pytest -m unit -x`)
inside the same run. Record `UNIT_RECOVERY_PATH=xdist_retry|fallback_non_xdist`.
Only fallback infra crash may remain `ERROR infra_suite_hard`.

**SERIAL long-suite heartbeat (pytest-unit / similarly long Shell):** before
starting the canonical unit Shell, emit interim
`WORKER RUNNING: pytest-unit (xdist; expect multi-minute)`. Prefer sliced
waits (Shell `block_until_ms` in ~60–120s slices **or** background Shell +
`AwaitShell` re-block) with a periodic progress line such as
`WORKER RUNNING: pytest-unit (still in progress; ~Nm elapsed)` — **not** one
opaque multi-tens-of-minutes silence. Progress lines remain interim-only;
Final is still mandatory when the check (or STOP_RUN) closes. Live
`pytest`/`run.sh` under SERIAL + Owner «зависло»/hang report is **not**
launch-infra retry (pytest is running).

#### Opt-in: `PARALLEL_TASKS` (legacy Task fan-out)

Only when Owner passes exact token `PARALLEL_TASKS` — honor registry
`task_type`:

| `task_type` | Checks | Launch |
|-------------|--------|--------|
| `shell` | pyright-strict, mypy, pytest-targeted | Task `subagent_type: shell` |
| `orchestrator` | **pytest-unit only** | **No Task.** Orchestrator Shell + hygiene + `run.sh` (same as SERIAL for this check) |
| `generalPurpose` | pytest-integration, pytest-destructive | Task `subagent_type: generalPurpose` |

- Read prompt template from `.cursor/static-check/base/worker-prompt.md` for Task-launched checks.
- Fill REPO_ROOT / MODE / CHECK_ID; load packs via that template.
- Invoke tools only via `bash .cursor/static-check/bin/run.sh -- …` (see `base/shell.md`).
- Do **not** invent `bash -lc 'source ...; cmd'`.
- Do **not** attempt custom project agent names (`opsx-sc-*` or any non-Task-enum id).
- Do **not** fan-out a nested Task for `task_type: orchestrator`.

If registry `task_type` is unavailable in the live Task enum **and** the check
is not `orchestrator` → launch with `generalPurpose` and the **same** prompt.
Never invent undeclared tool wrappers.

**Launch-infra retry (exactly one Task retry per CHECK_ID):** for Task-launched
checks only (not pytest-unit / not SERIAL primary path). Treat as launch-infra
failure (not a pytest FAIL) and retry once via Task `generalPurpose` with the
same prompt when ANY of:

- first Task finishes with no parseable worker packet;
- Agent Looping / repeating-pattern abort, or Task error without packet body;
- **silent stall** (pre-completion): CHECK_ID still in-flight with no
  parseable packet, owner reports hang/завис/стоп-воркера (or orchestrator
  probes after that signal), **and** evidence shows no matching
  `pytest`/`run.sh` for that check and/or Task transcript is only the initial
  prompt (no command output). Interrupt/abandon the open Task if still open,
  emit `WORKER RETRY`, then the one GP Task retry.

Use the retry packet if valid. Never more than one Task retry.

**Orchestrator-direct fallback (exactly one, after Task budget exhausted):**
if the one Task launch-infra retry is exhausted **and** the check never
started → orchestrator runs **once** via its own Shell tool:
`bash .cursor/static-check/bin/run.sh -- <canonical command from instructions>`,
synthesizes a worker packet from exit code + tail, continues cascade.
Emit `WORKER DIRECT: <check_id> → orchestrator-shell`. This is **not** a
second Task retry and not a product FAIL path. If orchestrator-direct also
fails to start/finish → `STATUS=ERROR` for that check.

Does **not** replace pytest-unit primary path (already orchestrator Shell);
pytest-unit uses INFRA recovery when xdist workers die after a real start.

**Not** launch-infra / not orchestrator-direct (do not retry for these):

- matching `pytest`/`run.sh` is alive (e.g. PG/`DROP SCHEMA` lock hang) →
  env / concurrent-suite issue (not Task launch-infra);
- Owner «зависло»/hang while SERIAL pytest-unit/`run.sh` is **alive** →
  not launch-infra; keep heartbeat/poll or, if Owner aborts, treat as STOP_RUN;
- owner `STOP_RUN` / abort of the entire `/opsx-static-check` / Shell tool
  interrupted mid-check → **no** retry; **mandatory** Final in the same
  turn: in-flight check `STATUS=ERROR` (`interrupted` / `STOP_RUN`), later
  pytest waves `SKIPPED`, fan-in already-known packets (incl. Wave A typing),
  then §5 Final. Never leave mid-cascade silence or progress-only as terminal.

Task prompt MUST match `base/worker-prompt.md` (required body).

Progress lines (interim only — never terminal):

```text
WORKER READY: <check_id> → <STATUS> (findings=<n>)
WORKER HYGIENE: pytest-unit → cleared|none|blocked (found=<n> eligible=<n> killed=<n> skipped_current_tree=<n>)
WORKER RUNNING: pytest-unit (xdist; expect multi-minute)
WORKER RUNNING: pytest-unit (still in progress; ~Nm elapsed)
WORKER INFRA RETRY: pytest-unit → orchestrator-shell
WORKER INFRA FALLBACK: pytest-unit → non-xdist-classifier
WORKER RETRY: <check_id> → generalPurpose (launch-infra)
WORKER DIRECT: <check_id> → orchestrator-shell
```

#### Progress vs Final report (mandatory)

**Progress-only** messages are **not** a terminal Final report. Forbidden as
the sole/terminal user-visible content of a completed command turn:

- "Wave A in flight"
- "waiting for packets"
- "cascade continues"
- any equivalent progress-only wording without a Final `STATUS:` block

A turn that ends without a Final report starting with exactly:

```text
STATUS: PASS|FAIL|BLOCKED|ERROR
```

followed by the required `CHECKS` / synthesis fields is an **incomplete run**
(`INCOMPLETE_RUN` for supervisor / owner envelopes — not PASS/FAIL success).

Under default `SERIAL_ORCHESTRATOR`, complete the cascade in the orchestrator
turn (Shell steps until every scheduled check has a packet), then emit Final.
Long suites may use sliced/background Shell + `WORKER RUNNING` heartbeats
**inside** that turn; do **not** end the turn with only a progress sentence
while work is still intended to continue. On STOP_RUN / Shell interrupt /
Owner abort: stop the cascade and emit Final immediately (see STOP_RUN
rules above). Under `PARALLEL_TASKS`, WAIT until packets land **or** apply
STOP_RUN Final — never treat progress as completion.

Pytest cascade (registry waves; hard stop on FAIL|BLOCKED|ERROR):

1. Wave A: `pyright-strict`, `mypy`, `pytest-targeted`
   (SERIAL: sequential Shell; `PARALLEL_TASKS`: may Task-parallel).
   `pytest-targeted`: prefilter `destructive_local` before Shell; ≤1 run per
   non-empty bucket; empty/exit 5 bucket → PASS+note (no exclude+rerun).
2. Wave U `pytest-unit` — only if `pytest-targeted` STATUS=PASS;
   orchestrator Shell + hygiene; xdist only here; if xdist infra persists after
   one retry, run one in-run fallback non-xdist classifier (no manual rerun loop)
3. Wave I `pytest-integration` — only if `pytest-unit` STATUS=PASS
4. Wave D `pytest-destructive` — MODE=FULL only; only if
   `pytest-integration` STATUS=PASS (set ALLOW_* per pack). Never in FAST.

If a pytest gate fails → mark later pytest checks `SKIPPED` and continue to
synthesis (typing packets from Wave A still fan-in). Do **not** `--deselect`
dirty paths from suite waves. Do **not** launch retired `pytest-full` / bare
`poetry run pytest`. Never put xdist on targeted / integration / destructive.

### 4. Fan-in + synthesize

Follow `.cursor/static-check/contracts/synthesis.md` (SoT: STATIC/TESTS
buckets, intersection dedupe, actionable group fields, ≤ half-chat PROBLEMS
budget, TRUNCATED/OMITTED_GROUPS).
Update checkboxes from packets.
Do not edit repo files while synthesizing.
Do not paste worker RAW_TAIL or full FINDINGS into the Final report.

When the **last open check** of the run completes (final scheduled pytest
wave packet, or earlier when later waves are SKIPPED): **immediately**
synthesize and go to §5 — do not end the turn with only `WORKER READY`.

Mass `severity` / setup ERROR with the same root cause → one PROBLEMS group
with `count`, not a dump of every node id (see synthesis.md).

### 5. Final report

**Mandatory artifact of every completed `/opsx-static-check` run** (PASS, FAIL,
or BLOCKED). Print the full template below even when Team/UI already showed a
red subagent.

```text
STATUS: PASS | FAIL | BLOCKED | ERROR
MODE: FULL | FAST
PREFLIGHT: off|on|skipped|failed
CHECKS:
- <id>: PASS|FAIL|SKIPPED|BLOCKED|ERROR (command: ...)
SUMMARY:
- passed/failed/skipped checks
- A_REUSED: yes|no (fingerprint=<id|n/a>)
- UNIT_RECOVERY_PATH: none|xdist_retry|fallback_non_xdist
- static_findings / test_findings / findings_total
- problem_groups / truncated / omitted_groups
PROBLEMS:
### STATIC
#### P1. <short title>
- path: <filepath:line>   # or <filepath> if line unknown
- count: <n>
- top: <≤2 codes>
- fix_target: <one line — file:line/symbol>
- fix_cmd: /opsx-fix-types
- seen_in: [...]
### TESTS
#### P2. <short title>
- node: <pytest node id>   # or infra note if ERROR infra_suite
- count: <n>
- top: <≤2 assert summaries>
- fix_target: <one line — test/fixture or hygiene>
- fix_cmd: /opsx-test-triage   # or owner recover env + re-run unit if infra_suite_hard
- seen_in: [...]
TRUNCATED: yes|no
OMITTED_GROUPS: <n>
NEXT ACTION:
<one step for the human; never "I will patch run.sh now">
```

Error UX: Problem / Cause / Action (never bare FAILED).
Budgets, dedupe, `fix_cmd` mapping, and single NEXT_ACTION rank: only in
`contracts/synthesis.md` — do not weaken them here.

## Human checklist

- PREFLIGHT off unless explicitly requested?
- Soft `/opsx-test-env UP` before FULL/destructive when live PG|CH|Redis needed
  (not confused with PREFLIGHT; Redis `:6379` external while `test_redis`
  commented)?
- No self-repair of command/infra during this run?
- Default launch `SERIAL_ORCHESTRATOR` (no nested Task) unless exact token
  `PARALLEL_TASKS`? No custom agent names?
- pytest-unit: orchestrator Shell + stale-pytest hygiene; INFRA retry once on
  xdist worker-death without failed nodes; if still infra, one in-run fallback
  `pytest -m unit -x` before declaring `infra_suite_hard`?
- SERIAL long-suite: `WORKER RUNNING` before unit Shell + sliced/heartbeat
  waits (no opaque multi-tens-of-minutes silence)?
- STOP_RUN / Shell interrupt / Owner abort: mandatory Final with
  ERROR+SKIPPED same turn (never INCOMPLETE mid-cascade)?
- `PARALLEL_TASKS` only: Launch-infra one Task GP retry; then orchestrator-direct
  once if suite never started?
- Registry-driven waves? xdist only on full unit?
- Final report printed by orchestrator (not progress-only / not only notification)?
  Progress strings («Wave A in flight», «waiting for packets») never terminal?
- One NEXT_ACTION?
