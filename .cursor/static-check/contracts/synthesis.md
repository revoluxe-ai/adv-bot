# Orchestrator synthesis contract

SoT for Final report PROBLEMS after fan-in. Orchestrator must follow this
exactly; do not paste worker RAW_TAIL or full FINDINGS lists into the report.

## Steps

1. **Normalize** findings from all packets (path, symbol/node, code, message,
   severity, check_id).
2. **Bucket** every finding into exactly one of:
   - `STATIC` — pyright-strict, mypy
   - `TESTS` — pytest-unit, pytest-full
3. **Deduplicate intersections** before grouping (never emit the same issue as
   two P# entries):
   - same path + symbol, or
   - same path + primary diagnostic code family, or
   - same pytest node id, or
   - same environment root cause (e.g. identical
     `DEV_TUNNELS_ENABLED` / connection-refused message across many nodes)
   → one problem group with `seen_in: [check_ids…]` and merged `count`.
4. **Group shape** (each P# must include all fields):
   - short title
   - `path` or test `node`
   - `count` (merged finding count)
   - `top` — ≤2 codes or assert summaries
   - `fix_target` — one line (file/symbol or test to repair; not an opsx command)
   - `fix_cmd` — recommended repair command for this group:
     - STATIC bucket → `/opsx-fix-types`
     - TESTS bucket → `/opsx-test-triage`
     - env/config group (if any) → `/opsx-test-env UP` (ports `5433`/`8124`/`6390`; session `REDIS_PORT=6390`; not `/opsx-devops`)
   - `seen_in`
   Evidence lines inside a group: ≤4.
5. **Rank** within each bucket (then print STATIC first, then TESTS):
   environment/config → collection → multi-tool typing → typing →
   multi-seen pytest → other pytest → other.
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
   - env/config → `/opsx-test-env UP` (then re-run FULL with `REDIS_PORT=6390`)
   - else typing / multi-tool typing → `/opsx-fix-types`
   - else pytest → `/opsx-test-triage`
   - PASS → continue (optional `/opsx-verify` hint only; never archive GO)
   Per-group `fix_cmd` does **not** replace this single NEXT_ACTION.
9. **Delivery:** Final report is mandatory after fan-in even when Agent Team /
   UI already displayed a failed subagent. Orchestrator prints it; do not
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
