# Orchestrator synthesis contract

SoT for Final report PROBLEMS after fan-in. Orchestrator must follow this
exactly; do not paste worker RAW_TAIL or full FINDINGS lists into the report.

Run metadata contract (printed in Final SUMMARY):

- `A_REUSED: yes|no (fingerprint=<id|n/a>)`
- when resume profile `FROM_WAVE=U` is used, Wave A checks must appear in
  CHECKS as `SKIPPED (A_REUSED)` and are not treated as failures.

## Steps

1. **Normalize** findings from all packets (path, line, symbol/node, code,
   message, severity, check_id). Use FINDINGS.`line` when present; do not drop
   line numbers when synthesizing PROBLEMS.
2. **Bucket** every finding into exactly one of:
   - `STATIC` — pyright-strict, mypy
   - `TESTS` — pytest-targeted, pytest-unit, pytest-integration,
     pytest-destructive (retired id `pytest-full` must not appear)
3. **Deduplicate intersections** before grouping (never emit the same issue as
   two P# entries):
   - same path + line + symbol, or
   - same path + line + primary diagnostic code family, or
   - same path + primary diagnostic code family when both lines are `n/a`, or
   - same pytest node id, or
   - same environment root cause (e.g. identical
     `DEV_TUNNELS_ENABLED` / connection-refused message across many nodes)
   → one problem group with `seen_in: [check_ids…]` and merged `count`.
4. **Group shape** (each P# must include all fields):
   - short title
   - `path` or test `node` — for STATIC: print `path: <filepath:line>` when
     `line` is an int; else `path: <filepath>`. Prefer a representative line
     from the group (lowest line if merged). TESTS keep pytest `node`.
   - `count` (merged finding count)
   - `top` — ≤2 codes or assert summaries
   - `fix_target` — one line (file:line/symbol or test to repair; not an opsx command)
   - `fix_cmd` — recommended repair command for this group:
     - STATIC bucket → `/opsx-fix-types`
     - TESTS bucket with failed node ids / assertion failures → `/opsx-test-triage`
    - TESTS / pytest-unit `ERROR infra_suite_hard` (fallback non-xdist also
      infra-crashed without failed nodes) → owner recover:
      kill leftover pytest for REPO_ROOT, inspect env/xdist instability,
      re-run `/opsx-static-check` Wave U (or canonical unit command) —
      **not** `/opsx-test-triage`
     - TESTS / pytest-unit `ERROR interrupted` / `STOP_RUN` (Owner abort or
       Shell interrupt; no failed nodes) → re-run `/opsx-static-check` (or
       `FROM_WAVE=U` only with valid `A_REUSE_FINGERPRINT`) after confirming
       no leftover pytest; **not** `/opsx-test-triage`
     - env/config group (if any) → `/opsx-test-env UP` (not ad-hoc
      `docker-compose` / `/opsx-devops`; laptop test compose owns PG:5433 +
      CH:8124; Redis is external `:6379` while `test_redis` stays commented —
      UP may return DEGRADED until Redis is up; not `/opsx-fix-*`)
   - `seen_in`
   Evidence lines inside a group: ≤4.
5. **Rank** within each bucket (then print STATIC first, then TESTS):
   environment/config → STOP_RUN/interrupted → infra_suite (xdist worker-death) →
   collection → multi-tool typing → typing → multi-seen pytest → other pytest →
   other.
6. **Hard body budget** (Final PROBLEMS section only, ~half chat max):
   - ≤12 problem groups total across both buckets
   - ≤80 lines AND ≤3500 characters for the PROBLEMS body
   - Prefer complete *groups* over raw diagnostics
   - On overflow: keep highest-ranked groups; set `TRUNCATED: yes` and
     `OMITTED_GROUPS: <n>`; keep full counters in SUMMARY
     (`static_findings`, `test_findings`, `problem_groups`, …)
7. **Forbidden in Final report:** worker `RAW_TAIL`, full `FINDINGS` dumps,
   repeating the same stack/source blob across groups.
8. **One NEXT_ACTION** (what to run *first* now; still exactly one line):
   - env/config → `/opsx-test-env UP` (then PROBE; if DEGRADED on Redis
     `:6379`, start external Redis or Owner-separate enable of compose
     `test_redis` — not silent uncomment from static-check)
   - else pytest-unit `ERROR infra_suite_hard` / fallback infra crash without
     failed nodes → kill leftover pytest; recover env; re-run unit/static-check
     (not test-triage)
   - else pytest-unit / suite `ERROR interrupted` / `STOP_RUN` → re-run
     `/opsx-static-check` (full or valid `FROM_WAVE=U`); not test-triage
   - else typing / multi-tool typing → `/opsx-fix-types`
   - else pytest with failed nodes → `/opsx-test-triage`
   - PASS → continue (optional `/opsx-verify`; after FULL with live services,
     soft advisory `/opsx-test-env DOWN`; never archive GO)
   Per-group `fix_cmd` does **not** replace this single NEXT_ACTION.
9. **Delivery:** Final report is mandatory after fan-in even when Agent Team /
   UI already displayed a failed subagent. Orchestrator prints it; do not
   treat Task completion notifications as the report. Final is also mandatory
   on Owner `STOP_RUN` / Shell interrupt / abort mid-cascade: synthesize from
   packets already collected + in-flight ERROR + later SKIPPED — never leave
   `INCOMPLETE_RUN` as the only outcome when abort is known.1. **Normalize** findings from all packets (path, symbol/node, code, message,
   severity, check_id).
   - `TESTS` — pytest-unit, pytest-full
   - same path + symbol, or
   - same path + primary diagnostic code family, or
   - `path` or test `node`
   - `fix_target` — one line (file/symbol or test to repair; not an opsx command)
     - TESTS bucket → `/opsx-test-triage`
     - env/config group (if any) → `/opsx-test-env UP` (ports `5433`/`8124`/`6390`; session `REDIS_PORT=6390`; not `/opsx-devops`)
   environment/config → collection → multi-tool typing → typing →
   multi-seen pytest → other pytest → other.
   - env/config → `/opsx-test-env UP` (then re-run FULL with `REDIS_PORT=6390`)
   - else pytest → `/opsx-test-triage`
   - PASS → continue (optional `/opsx-verify` hint only; never archive GO)
   treat Task completion notifications as the report.
10. **Destructive cache SUMMARY (mandatory when pytest-full ran or
    destructive was in plan):** Final report SUMMARY MUST include exactly:
    ```text
    CACHE_MODE: <dev|off|force|n/a>
    CACHE_DEGRADED: <yes|no|n/a>
    destructive_cache: ran=N cached=M (CACHE_HIT ≠ archive EXECUTED green)
    ```
    If pytest-full PASS but these lines are missing while MODE=FULL → treat
    Final report as **incomplete**; re-emit with lines (do not invent cached
    skips). Prefer `CACHE_DEGRADED=yes` when planner missing.
11. **NEXT_ACTION after FULL PASS + CACHE_MODE=dev + cached>0** (soft):
    prefer paste `/opsx-static-check FULL CACHE_OFF` before archive verify;
    otherwise `/opsx-verify mode=archive <change>` when in pre-archive chain.