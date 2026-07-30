---
description: "READ_ONLY cross-case bug debt board: open findings, OPEN_CANDIDATE, CLOSED_WITH_RESIDUAL, stale claims; pasteable recovery exits."
argument-hint: "[case=<CASE_ID>] [focus=all|open_candidates|claims|residuals|closed_with_debt] [limit=<N>]"
---

# /opsx-bug-debt-board

Покажи **весь видимый bug debt** по `.tmp/opsx-bug-cases/` — open findings,
`OPEN_CANDIDATE` / HARD_BLOCK_READY residuals, CLOSED-with-residual,
stale claims — и дай **pasteable** next step на каждую строку.

Цель: после потери чата / FANIN / GREEN нельзя спокойно идти дальше, не видя
что ещё висит. INDEX — storage; эта команда — **operator front-door**.

## What this is

* Cross-case **READ_ONLY** debt inventory (sibling UX к
  `/opsx-antipattern-gate`, но про bug cards / residuals, не code smell).
* Soft quality / recovery step: anytime; especially post-GREEN / FANIN,
  pre-`/opsx-verify` / archive, after chat loss.
* Default **over-report**: лучше лишняя строка, чем забытый HC residual.
* Pasteable exits only — never invents close / commit / push.

## What this is NOT

* NOT writer of `INDEX.md` (→ `/opsx-materialize-bug-queue mode=update`).
* NOT claim / classify / fix / close (→ claim-next / classify / fix-bug /
  materialize close / bug-team).
* NOT FANIN authority / `READY_FOR_CLOSURE` re-decide (→ FAN_IN_ASSEMBLER /
  `/opsx-bug-team`).
* NOT archive `GO` / `NO_GO` (→ `/opsx-verify`).
* NOT antipattern / code-smell scan (→ `/opsx-antipattern-gate`).
* NOT product bug hunt (→ `/opsx-project-bug-hunt`).

## User input

```text
$ARGUMENTS
```

| Token | Effect |
|-------|--------|
| `case=<CASE_ID>` | optional; limit scan to one case |
| `focus=all\|open_candidates\|claims\|residuals\|closed_with_debt` | optional; default `all` |
| `limit=<N>` | optional; max debt rows shown (default 40) |
| unknown token | `STATUS=BLOCKED`, не менять файлы |

Примеры:

```text
/opsx-bug-debt-board
/opsx-bug-debt-board case=BUGCASE-AB-HOLD-ENTER-RECLASS-20260730T082531Z
/opsx-bug-debt-board focus=open_candidates
/opsx-bug-debt-board focus=closed_with_debt limit=20
```

## Modes

### Default — SCAN (READ_ONLY)

* Не менять репозиторий.
* Только отчёт + pasteable `NEXT_ACTION` / per-row exits.

## Authority surfaces

```text
INDEX:     .tmp/opsx-bug-cases/INDEX.md          (read; SoT for recovery rows)
CASES:     .tmp/opsx-bug-cases/<CASE_ID>/        (LEDGER, FANIN, findings, HC-*)
CONTRACTS: .cursor/pipeline/contracts/bug-episode/FANIN.md
           .cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md
MATERIALIZE INDEX rules: /opsx-materialize-bug-queue (INDEX writer)
```

This command **consumes** INDEX + case artifacts. It does **not** become a
second SoT for case status.

## Debt row kinds (over-report)

| ROW_KIND | Signal |
|----------|--------|
| `OPEN_FINDING` | finding `STATUS` open / available / blocked (not closed_*) |
| `OPEN_CANDIDATE` | `STATUS ∈ {open_candidate, OPEN_CANDIDATE}` (HC-* / hunt residual) |
| `HARD_BLOCK_READY_DEBT` | SAME_INVARIANT `OPEN_CANDIDATE` that forbids READY / closure |
| `CLOSED_WITH_RESIDUAL` | case/INDEX shows CLOSED_* but residual / HC / OPEN_CANDIDATE remains |
| `STALE_CLAIM` | `STATUS=claimed` with no recent progress / forgotten list |
| `INDEX_STALE_VS_FANIN` | disk has OPEN_CANDIDATE / FANIN_INCOMPLETE but INDEX omits or implies closable |
| `FANIN_INCOMPLETE` | FANIN / team state incomplete / BLOCKING_FINDINGS open |

When unsure whether a residual is still open → emit the row as debt, not silence.

## Scan algorithm

1. If `.tmp/opsx-bug-cases/` missing → `STATUS=BLOCKED` with create hint.
2. Read `INDEX.md` (bounded). If missing → `BLOCKED` + pasteable
   `/opsx-materialize-bug-queue` (or note that no cases exist yet).
3. Enumerate case dirs under `.tmp/opsx-bug-cases/` (skip non-case paths).
   If `case=` set → only that case; unknown case → `BLOCKED`.
4. For each in-scope case, bounded Grep/Read (prefer section reads ≤ 120 lines):
   - `INDEX.md` recovery / CLOSED / RESIDUAL notes for that case
   - `LEDGER.md` / finding rows
   - `findings/**` including `HC-*`
   - `results/FANIN.md` / FANIN tokens when present
   - claim / AVAILABLE / BLOCKED lists if present in INDEX aggregates
5. Apply `focus=`:
   - `open_candidates` → OPEN_CANDIDATE + HARD_BLOCK_READY_DEBT
   - `claims` → STALE_CLAIM + claimed OPEN_FINDING
   - `residuals` → OPEN_CANDIDATE + HARD_BLOCK + CLOSED_WITH_RESIDUAL
   - `closed_with_debt` → CLOSED_WITH_RESIDUAL (+ INDEX_STALE if relevant)
   - `all` → union
6. Cap at `limit=` (default 40); if truncated, say so and prefer HARD_BLOCK /
   OPEN_CANDIDATE / CLOSED_WITH_RESIDUAL first.
7. For every row emit pasteable exit (see map). Prefer `LOC_LINK` when a
   concrete finding file/line is known
   (`.cursor/rules/opsx-clickable-loc-link-contract.mdc`).
8. Print Final report. **Do not write files.**

## Pasteable exit map

| ROW_KIND | Pasteable next |
|----------|----------------|
| `OPEN_CANDIDATE` / `HARD_BLOCK_READY_DEBT` / `FANIN_INCOMPLETE` | `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout` |
| `OPEN_FINDING` available | `/opsx-claim-next-bug case=<CASE_ID>` or claim with finding if required |
| `OPEN_FINDING` claimed / classify next | paste INDEX `NEXT_ACTION` if valid; else claim/classify with case= |
| `STALE_CLAIM` | Owner: continue claim path **or** materialize recovery; do not auto-reclaim |
| `CLOSED_WITH_RESIDUAL` | `/opsx-bug-team case=<CASE_ID> mode=resume-family-fanout` (re-open residual path) |
| `INDEX_STALE_VS_FANIN` | `/opsx-materialize-bug-queue mode=update case=<CASE_ID>` then re-run this board |

Never paste close/commit as the primary exit for open debt.

## Status

| STATUS | Когда |
|--------|--------|
| `CLEAR` | no debt rows in focus (after scan) |
| `DEBT_FOUND` | ≥1 debt row |
| `BLOCKED` | missing cases dir / INDEX (when required) / bad `case=` / unknown token |

`CLEAR` with empty `.tmp/opsx-bug-cases/` (no cases ever) is `BLOCKED` or
explicit empty-board note — prefer `BLOCKED` with create hint if INDEX absent.

## Authority boundaries

* Не пиши `INDEX.md`, LEDGER, findings, `closed_fixed`.
* Не объявляй archive `GO` / `NO_GO`.
* Не подменяй FANIN / HARD_BLOCK_READY contracts — только **surface** them.
* Soft recommend from verify / bug-team — this command is not a hard archive
  gate in v1.
* Over-report is intentional; use `focus=` / `case=` / `limit=` to tame noise.

## Final report (required)

```text
STATUS: CLEAR | DEBT_FOUND | BLOCKED

FOCUS: all | open_candidates | claims | residuals | closed_with_debt
CASE_FILTER: <CASE_ID|all>
LIMIT: <n>
INDEX: .tmp/opsx-bug-cases/INDEX.md
CASES_SCANNED: <n>
ROWS_SHOWN: <n>
ROWS_TRUNCATED: yes|no

DEBT_ROWS:
- ROW_KIND: <kind>
  CASE_ID: <id>
  FINDING_OR_CANDIDATE: <id|none>
  PATH: <path|none>
  LOC_LINK: <path:line|none>
  SIGNAL: <short>
  INDEX_NOTE: <short|none>
  FIX_EXIT: <pasteable command>
  NOTE: <short>

GAPS:
- <ROW_KIND> @ <CASE_ID>/<id>: → <FIX_EXIT>

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OWNER_DECISION_REQUIRED: none | pick which debt row to work | refresh INDEX
NEXT_ACTION:
DO_NOT_DO_YET:
```

### Typical NEXT_ACTION

After `DEBT_FOUND`:

```text
NEXT_ACTION: <first HARD_BLOCK / OPEN_CANDIDATE FIX_EXIT>
ALSO_OK: re-run /opsx-bug-debt-board after that hop
DO_NOT_DO_YET: /opsx-verify archive GO; treat CLOSED as done while residual open
```

After `CLEAR`:

```text
NEXT_ACTION: continue planned verify/archive/product hop
DO_NOT_DO_YET: skip re-check if new FANIN/hunt just landed — re-run board
```

## Soft handoff (producers → this command)

Callers may **recommend** (not hard-block):

* `/opsx-verify` when a linked `BUGCASE-…` / INDEX exists
* `/opsx-bug-team` when `FANIN_INCOMPLETE` or HARD_BLOCK_READY debt
* post-GREEN / chat-loss recovery

## Self-check

- [ ] READ_ONLY: no INDEX / finding / closed_fixed writes
- [ ] Over-report: uncertain residual → emit row
- [ ] Every row has pasteable `FIX_EXIT` with `case=` when case-scoped
- [ ] No archive GO/NO_GO claimed
- [ ] HARD_BLOCK_READY / OPEN_CANDIDATE prioritized when truncating
- [ ] Does not steal materialize INDEX authority
