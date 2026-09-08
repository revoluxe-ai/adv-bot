# FANIN — BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z

```text
STATUS: FANIN_READY
CASE_ID: BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z
ROOT_FINDING_ID: FINDING-001
ASSEMBLED_AT: 2026-08-28T15:33:22Z
ASSEMBLER: FAN_IN_ASSEMBLER
WORKER_EXECUTION_ID: WEX/FAN_IN_ASSEMBLER/38f14651a4
ORCHESTRATION_ID: ORCH/bug-team/9745ba6a72d6
EXECUTION_MODE: CONTROLLED_LIVE_UNCOMMITTED
MAPS_TO: /opsx-materialize-bug-queue mode=fanin_assemble
```

## ROOT_BUG

`AttributeError: 'BufferedInputFile' object has no attribute 'startswith'` in
`app/file_handler.py:_get_telegram_file` when `get_telegram_image` receives a
`BufferedInputFile` (AdvKeywordsSetting / manage_file_id path) and the helper
calls `image_path.startswith("http")` without a type guard.

## ROOT_CAUSE_PATTERN

Union-typed image/path argument (`str | BufferedInputFile`) treated as `str`
via str methods (`startswith`) before `isinstance` / type narrowing.

## ERROR_CLASS

`TYPE_UNION_STR_METHOD_ON_INPUTFILE` — Telegram `InputFile`/`BufferedInputFile`
passed through helpers that assume filesystem/URL `str`.

## ROOT_INVARIANT

Callers/helpers must not assume image/path args are `str` when the API accepts
`BufferedInputFile`/`InputFile`; never call str methods (`startswith` /
`endswith` / …) without `isinstance`/type guard.

## SIBLING_VARIANTS

None found. Bounded hunt (`results/HUNT-FINDING-001.md`) returned
`HUNT_RESULT: CLEAR`, `CANDIDATES: []`. No `findings/HC-*` stubs. No
`RELATION_TO_ROOT_CANDIDATE=SAME_INVARIANT_FINDING` open candidates.

Residual note (not a candidate): guard is `isinstance(..., BufferedInputFile)`
not base `InputFile`; no `FSInputFile`/`URLInputFile` usage under `app/`.

## FIX_PATTERNS

1. Early `isinstance(image_path, BufferedInputFile)` → return as-is (passthrough).
2. Keep `BytesIO` → `BufferedInputFile` wrap branch.
3. Call `str.startswith("http")` only after non-InputFile / non-BytesIO narrowing
   (`image_path is not None and image_path.startswith("http")`).
4. Widen type hint to `str | BytesIO | BufferedInputFile | None`.

Production path: `app/file_handler.py` (uncommitted).
PRODUCTION_HASH_BEFORE: `sha256:7d425e30354685dfee73202234529f065ea9d45d334fc913fee114052d6fb458`
PRODUCTION_HASH_AFTER: `sha256:480bf4a77a3ca8ad2a467d37c1e1d7560d7b75ea5df0f5d1960e358bc4075215`

## REGRESSION_TEST_PATTERN

Frozen unit tests assert BufferedInputFile passthrough without `startswith`:

- `tests/unit/test_file_handler_buffered_input_file.py::test_get_telegram_image_accepts_buffered_input_file_without_startswith`
- `tests/unit/test_file_handler_buffered_input_file.py::test_get_telegram_file_accepts_buffered_input_file_without_startswith`

TEST_CONTENT_SHA256: `d6386cded0528f71e428e832d792e8eee94d3aa8eff35f5d92826e3411490169`
(RED ↔ GREEN match; NON_WEAKEN_DELTA: none)

## PREVENTION_RULE_CANDIDATE

When a public helper types an arg as `str | BufferedInputFile` (or broader
InputFile union), forbid bare `.startswith`/`.endswith`/other str methods on
that name until after an explicit `isinstance(..., (str, type(None)))` (or
equivalent) narrowing; prefer early InputFile passthrough.

## REUSABLE_CHECK_CANDIDATE

Static/heuristic scan: under `app/`, sites where a name typed or documented as
InputFile-capable union is used with `.startswith`/`.endswith` without a
preceding `isinstance` guard for InputFile/BufferedInputFile.

## REMAINING_EXCEPTIONS

NONE (no open SAME_INVARIANT candidates; speculative InputFile-base hardening
not promoted).

## BRANCH_SUMMARY

| FINDING_ID | ROLE | EPISODE_TERMINAL | RED | FIX | GREEN | OWNER_PRODUCTION_GO | NOTES |
|---|---|---|---|---|---|---|---|
| FINDING-001 | ROOT | FIXED | results/RED-FINDING-001.md | results/FIX-FINDING-001.md | results/GREEN-FINDING-001.md | N/A (CONTROLLED_LIVE_UNCOMMITTED) | GREEN_CONFIRMED; hunt CLEAR |

BRANCH_REGISTRY (LEDGER snapshot): no child branches started.
ACTIVE_BRANCH_COUNT: 0
Child FINDING rows: none beyond root.

## HUNT_SUMMARY

```text
HUNT_RESULT: CLEAR
HUNT_PASSES_EXECUTED: 1
MAX_HUNT_PASSES: 3
CANDIDATES: []
OPEN_SAME_INVARIANT_CANDIDATES: 0
HUNT_EVIDENCE: results/HUNT-FINDING-001.md
```

## SAME_INVARIANT_SCAN

```text
findings/: FINDING-001 only (root; RELATION_TO_ROOT=root)
findings/HC-*: none
HUNT CANDIDATES: []
STATUS open_candidate / OPEN_CANDIDATE: none
BLOCKING_FINDINGS: NONE
```

## CLOSURE_READINESS

```text
CLOSURE_READINESS: READY_FOR_CLOSURE
BLOCKS_ROOT_CLOSURE: false
BLOCKING_FINDINGS: NONE
NO_OPEN_SAME_INVARIANT_CANDIDATES: true
LEARNING_READY: NOT_CLAIMED_BY_FANIN
```

Note: `LEARNING_READY ≠ FANIN_READY`. Class lesson / Owner FINAL remain
downstream of `/opsx-learn-from-bug`.

## REGRESSION_STATUS

```text
RED_CONFIRMED → FIXED_UNCOMMITTED → GREEN_CONFIRMED
PYTEST: 2 passed (verify)
TEST_CONTENT_SHA256_MATCH_RED: YES
NON_WEAKEN_DELTA: none
```

## LIMITS_CHECK

```text
LIMITS_CHECK: PASS
HUNT_PASSES_EXECUTED: 1 ≤ MAX_HUNT_PASSES: 3
MAX_DEPTH_SEEN: 0 ≤ MAX_DEPTH_FROM_ROOT: 3
ACTIVE_BRANCH_COUNT: 0 ≤ MAX_ACTIVE_BRANCHES: 3
DEPTH: 0
```

## CHECKS

```text
1_FIXED_HAVE_RED_GREEN_GO: PASS
   RED + FIX + GREEN present for FINDING-001.
   OWNER_PRODUCTION_GO: N/A under CONTROLLED_LIVE_UNCOMMITTED
   (ORCHESTRATION: local worktree writes after RED; no intermediate Owner GO).
2_NO_WEAKEN: PASS
   TEST_CONTENT_SHA256 identical RED→GREEN; NON_WEAKEN_DELTA=none.
3_NO_DOUBLE_FIX: PASS
   Single production edit path; one IMPLEMENTATION_EXECUTOR hop.
4_NO_CONFLICTING_PRODUCTION_DIFFS: PASS
   Sole production file: app/file_handler.py; single before/after hash pair.
5_ONE_ROOT_INVARIANT_OR_EXPLICIT_OUTEPISODE: PASS
   One root invariant; hunt CLEAR; no out-of-episode siblings.
6_LIMITS_NOT_EXCEEDED: PASS
   Limits within MAX_HUNT_PASSES / MAX_DEPTH / MAX_ACTIVE_BRANCHES.
```

## NEXT_ACTION

```text
/opsx-learn-from-bug case=BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z FANIN_PATH=.opsx/runs/bug-cases/BUGCASE-BUFFEREDINPUTFILE-STARTSWITH-20260828T142953Z/results/FANIN.md
```
