# Destructive selective cache — design (all entry points)

```text
STATUS: DESIGN_READY + PIPELINE_GUARDS_ACTIVE
SCOPE: every OPSX / agent path that executes @pytest.mark.destructive_local
AUTHORITY: shared contract; SoT for CACHE_MODE defaults + fingerprint
ARCHIVE_POLICY: cache MUST NOT be sole archive/PR green evidence
CREATED: 2026-08-09
UPDATED: 2026-08-09
```

## Problem

Long `@pytest.mark.destructive_local` tests re-run from multiple entry points
even when their causal surface did not change, burning Owner time and local
PG/CH.

## Goal

**Default everywhere:** execute only destructive nodes whose fingerprint is
missing, stale, or forced; skip cache hits with an explicit `SKIPPED_CACHED`
receipt.

Never pretend a cache hit is freshly executed archive evidence.

## Universal default (Owner lock)

```text
Any entry that would run destructive_local
→ CACHE_MODE=dev by default
→ run MUST_RUN only; CACHE_HIT skipped
```

Opt-out is always explicit:

```text
CACHE_OFF     → run all selected destructive (no skip)
CACHE_FORCE   → run all selected destructive; rewrite receipts
CACHE_DEV     → alias of default (optional no-op)
```

`authorized_live` / `AUTHORIZE_ONE_LIVE_RUN` is a **different** execution
class — not covered by this cache (one-shot Owner authorize stays required).

## Non-goals

- New OPSX command (no `/opsx-test-cache`).
- Hand-maintained nodeid allowlist as membership SoT.
- Skipping pyright / mypy / pytest-unit / non-destructive suites.
- Weakening archive/PR by treating CACHE_HIT as EXECUTED green.
- Committing cache receipts into product git.

## Entry points (all must honor default=dev)

| Entry | Default | Opt-out tokens / note |
|-------|---------|------------------------|
| `/opsx-static-check` (FULL / bare) | `CACHE_MODE=dev` | `CACHE_OFF`, `CACHE_FORCE` |
| `/opsx-static-check FAST` | N/A (no destructive Wave B) | ignore `CACHE_*` |
| `pytest-full` worker | inherits orchestrator `CACHE_MODE` | same |
| `/opsx-test` when invocation selects any `destructive_local` | `dev` | `CACHE_OFF`, `CACHE_FORCE` in `$ARGUMENTS` |
| `/opsx-apply` / agent ad-hoc `poetry run pytest …` that collects destructive | `dev` via testing-rules | require `CACHE_OFF`/`CACHE_FORCE` in the shell plan or Owner text |
| `/opsx-test-env` | does not run pytest | NEXT may suggest FULL; cache policy applies at static-check/test |
| `/opsx-verify` | does not run destructive mutation tests | if it ever shells pytest with destructive markers → same default |
| `/opsx-close-external-gap` live certify | `authorized_live` path | **out of scope** of this cache |

Shared planner (single implementation):

```text
.cursor/static-check/bin/destructive_cache_plan.py
```

All entry points MUST call this planner (or equivalent thin wrapper) before
executing any `destructive_local` node — not reimplement skip logic in chat.

## INTERIM (planner missing — mandatory)

Until
`.cursor/static-check/bin/destructive_cache_plan.py` exists **and** exits 0
with a valid plan:

```text
CACHE_MODE token may still parse as dev (default)
effective execution = CACHE_DEGRADED
→ run ALL selected destructive_local nodes
→ print CACHE_DEGRADED=yes
→ FORBIDDEN: invent deselect / skip / “already green on branch” filters
→ FORBIDDEN: claim CACHE_HIT without planner receipt
```

After planner ships, default `dev` selective path applies; INTERIM lifts
automatically when the planner file is present and healthy.

## Modes

```text
CACHE_MODE=dev        # DEFAULT; selective destructive
CACHE_MODE=off        # explicit; run all selected destructive
CACHE_MODE=force      # explicit; run all + rewrite receipts
```

### `/opsx-static-check` examples

```text
/opsx-static-check                      → FULL + CACHE_MODE=dev
/opsx-static-check FULL                 → FULL + CACHE_MODE=dev
/opsx-static-check FULL CACHE_OFF       → FULL + CACHE_MODE=off
/opsx-static-check FULL CACHE_FORCE     → FULL + CACHE_MODE=force
/opsx-static-check FAST                 → FAST; CACHE_MODE=n/a
```

### `/opsx-test` examples

```text
/opsx-test …                            → if destructive selected: CACHE_MODE=dev
/opsx-test … CACHE_OFF                  → run all selected destructive
/opsx-test … CACHE_FORCE                → run all + rewrite receipts
```

Hard rules:

1. Missing `CACHE_*` → **dev** (not off).
2. Archive / pre-PR / merge confidence → `CACHE_OFF` or `CACHE_FORCE`.
3. Final/status output MUST print `CACHE_MODE` + ran/cached counts whenever
   destructive nodes were in the plan.
4. `CACHE_HIT` ≠ archive / Scenario certify EXECUTED green.

## Registry (auto, not hand list)

**Source of truth:** pytest collection with marker `destructive_local`.

```text
poetry run pytest --collect-only -q -m destructive_local
```

When the entry already narrows paths/nodeids, intersect:

```text
planned_destructive = collect(destructive_local) ∩ entry_selection
```

- Unfingerprintable node → `MUST_RUN` (fail-closed).
- New / renamed nodeids → `MUST_RUN`.
- Hand inventory = debug dump only, never membership SoT.

### v1 execution shape (static-check FULL)

```text
CACHE_MODE=off|force:
  poetry run pytest

CACHE_MODE=dev:
  1) poetry run pytest -m "not destructive_local"
  2) plan destructive via destructive_cache_plan.py
  3) run only MUST_RUN destructive nodeids
```

On deselect/composition failure → `CACHE_DEGRADED=yes`, run all planned
destructive (fail open toward execution, not toward fake PASS).

### v1 execution shape (targeted `/opsx-test` / ad-hoc)

```text
1) resolve entry_selection (paths/nodeids/markers)
2) planned_destructive = intersection with destructive_local collect
3) if empty → run entry as today (no cache)
4) if non-empty and CACHE_MODE=dev:
     run (entry_selection minus CACHE_HIT destructive)
   else:
     run entry_selection fully
5) upsert receipts for destructive nodes that actually ran
```

## Fingerprint schema

Per nodeid: `TEST_ID` = repo-relative `path::nodeid`.

```text
FINGERPRINT_VERSION: 1

TEST_CONTENT_SHA:      sha256(test module) + conftest chain under tests/
PRODUCTION_BOUNDARY_SHA:
  v1: static imports from test module into app/|alembic_/
  uncertain parse → MUST_RUN
SHARED_HARNESS_SHA:
  pytest.ini, root/tests conftest, pytest-full instructions,
  compose pins used by /opsx-test-env (freeze list at implement)
SCHEMA_ENV_SHA:
  alembic head / CH migration pins when store-touching; probe miss → MUST_RUN
TOOL_CLASS:
  python major.minor + poetry.lock hash prefix
WORKTREE_EPHEMERAL:
  branch/HEAD recorded only; not part of CACHE_HIT equality
```

```text
CACHE_HIT iff receipt exists AND version match AND all *SHA+TOOL_CLASS equal
             AND receipt.LAST_STATUS == PASS
else MUST_RUN
```

## Local artifact (shared, not product SoT)

```text
Path: .cursor/static-check/.cache/destructive-last-run.json
Git:  MUST be gitignored
```

One cache file for **all** entry points (static-check, opsx-test, ad-hoc).

## Wire-in points

| Layer | Change |
|-------|--------|
| This contract | SoT for defaults + fingerprint |
| `destructive_cache_plan.py` | shared planner |
| `opsx-static-check.md` | tokens; default dev; pass CACHE_MODE to Wave B |
| `checks/pytest-full/instructions.md` + `context.md` | call planner |
| `opsx-test.md` | when destructive selected → default dev + tokens |
| `testing-rules.mdc` | universal agent rule: destructive ⇒ planner + default dev |
| `TEST_EVIDENCE_TAXONOMY.md` | CACHE_HIT ≠ EXECUTED green |
| `worker-packet.md` / `synthesis.md` | counters |
| `.gitignore` | `.cursor/static-check/.cache/` |
| `GRAPH.md` | note default cache on destructive; CACHE_OFF for archive confidence |

### Packet / report extras

```text
CACHE_MODE: off|dev|force|n/a
DESTRUCTIVE_TOTAL: <int>
DESTRUCTIVE_RAN: <int>
DESTRUCTIVE_CACHED: <int>
DESTRUCTIVE_FORCED: <int>
CACHE_DEGRADED: yes|no
```

```text
destructive_cache: ran=N cached=M (CACHE_HIT ≠ archive EXECUTED green)
```

## Fail-closed matrix

| Situation | Action |
|-----------|--------|
| Marker collect fails | BLOCKED / ERROR; no PASS |
| Fingerprint scanner error | that node MUST_RUN |
| Cache file corrupt | ignore file; all planned destructive MUST_RUN |
| New destructive node | MUST_RUN |
| Prod boundary uncertain | MUST_RUN |
| Schema/env probe missing for PG/CH node | MUST_RUN |
| Unknown CACHE_* token on a command that parses tokens | `STATUS=BLOCKED` |
| Planner missing / broken | CACHE_DEGRADED: run **all** planned destructive; no improvised skip |

## Relation to TEST_EVIDENCE_TAXONOMY

```text
CACHE_HIT / SKIPPED_CACHED is an optimization receipt for CACHE_MODE=dev
across all destructive_local entry points. It is not EXECUTED=YES green
evidence for /opsx-verify archive, Scenario certify, or authorized_live.
```

## Implementation phases

1. gitignore + cache schema + `destructive_cache_plan.py` (fail-closed)
2. Wire default `dev` into `/opsx-static-check` → pytest-full
3. Wire same default into `/opsx-test` + `testing-rules.mdc`
4. PRODUCTION_BOUNDARY_SHA v1 + taxonomy paragraph + GRAPH note
5. Manual validation: clean cache skip vs one dirty destructive MUST_RUN

## Owner decisions locked

| Decision | Lock |
|----------|------|
| Default on **all** destructive entry points | `CACHE_MODE=dev` |
| Opt-out | explicit `CACHE_OFF` / `CACHE_FORCE` |
| Membership SoT | pytest marker collect |
| Shared cache file | one local artifact for all entries |
| Branch-only skip | **forbidden** |
| Archive sole evidence from cache | **forbidden** |
| `authorized_live` | **out of scope** |
| New OPSX command | **not required** |

## Open (implement-time)

1. Exact compose/alembic/CH path list for harness/schema SHAs.
2. FULL split vs single pytest + deselect.
3. Import-graph depth for PRODUCTION_BOUNDARY_SHA v1 vs v2.

## NEXT_ACTION

Implement phases 1–3: shared planner + default `dev` on static-check and
opsx-test/testing-rules; `CACHE_OFF` restores run-all destructive.
