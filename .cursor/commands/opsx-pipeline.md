---
description: "Operator assistant over not-admin OPSX commands: navigate the as-is pipeline via a materialized graph; UPDATE / UPDATE GO maintain the graph."
argument-hint: "[NAVIGATE] | UPDATE | UPDATE GO [optional change name / hint]"
---

# /opsx-pipeline

Operator navigation assistant over **not-admin** OpenSpec/OPSX commands.

Uses one shared **materialized traversal graph** of the current pipeline
**as-is** (including known flaws). Does not redesign the pipeline.

Pipeline redesign / improvement analysis belongs to
`/opsx-admin-command-analyze-pipeline` (ephemeral, READ_ONLY).

## Shared materialization (mandatory link)

`.cursor/pipeline/GRAPH.md` (+ `META.md`) is the **only durable shared
materialization** that links:

1. not-admin command contracts (source of edges);
2. optional ephemeral drafts from `/opsx-admin-command-analyze-pipeline`
   (input evidence for UPDATE only — never authoritative alone);
3. `/opsx-pipeline` NAVIGATE recommendations.

Rules:

- Chat graphs, conversation memory, and analyze-pipeline `CURRENT_GRAPH`
  are **not** the shared map until promoted via `UPDATE` → `UPDATE GO`.
- NAVIGATE must read the materialized files by exact path; do not rebuild
  a private alternate graph for advice.
- UPDATE / UPDATE GO own refresh of that single shared materialization.
- Command contracts remain independently authoritative; the graph only
  **indexes** them for orientation.

## Soft recommendation (graph is not a gate)

`NEXT_ACTION` from NAVIGATE is an **advisory recommendation** only.

- The operator **may deviate** from the graph at any time (skip, reorder,
  jump branch, run a different not-admin command).
- Deviation is **not** a process violation and must not be framed as an
  error, bypass, or NO_GO.
- The navigator must **not** block, refuse, or rewrite the operator’s
  chosen not-admin command solely because it is off-graph.
- When the operator is off-graph, still give best-effort advice: nearest
  graph node, `ON_GRAPH: false`, and one advisory next step — without
  demanding return to the canonical edge first.
- Target command contracts still own their own gates; soft graph advice
  never weakens or strengthens those gates.

## User input

```text
$ARGUMENTS
```

Parse mode from arguments (case-insensitive):

| Token present | Mode |
|---|---|
| `UPDATE GO` | `UPDATE_GO` |
| `UPDATE` (without `GO`) | `UPDATE` |
| otherwise / empty / `NAVIGATE` | `NAVIGATE` |

Optional trailing change name or free-text hint may follow the mode token.

## Purpose

Help a human walk the current not-admin pipeline without memorizing hidden
ordering rules.

- **NAVIGATE** — where am I, what is the one next pasteable command, what
  known flaws apply.
- **UPDATE** — rebuild the current pipeline graph draft for owner agreement
  (no file writes).
- **UPDATE GO** — persist the agreed materialized graph.

## When to use

- Unclear next not-admin step after a command result.
- Starting or resuming work on a change and needing orientation.
- After adding/changing not-admin commands — refresh the graph via UPDATE.

## When not to use

- Redesign or improve process contracts → `/opsx-admin-command-analyze-pipeline`
- Fix command defects → `/opsx-admin-command-fix-command-defects`
- Design a new command → `/opsx-admin-command-design-command`
- Commit process surfaces → `/opsx-admin-command-commit`
- Commit product/code → `/opsx-commit`
- Execute apply / verify / archive / bug-fix / etc. — only **recommend** them

## Authority boundary (mandatory)

The materialized graph is a **shared navigation snapshot**, not a second
lifecycle authority and not an enforcement rail.

- Target command contracts remain authoritative for their own GO / NO_GO /
  gates / write boundaries.
- This command MUST NOT override verify, archive, approval, sync, or commit
  gates.
- This command MUST NOT silently re-decide another command’s verdict.
- This command MUST NOT treat off-graph operator choices as forbidden.
- Known flaws in the graph are first-class: surface them; do not hide or
  “fix” them during NAVIGATE.
- Recommendation strength is always `advisory`.

## Scope of the graph

`SCOPE = ALL_NON_ADMIN_OPSX`

Include user-facing `.cursor/commands/opsx-*.md` except:

```text
opsx-admin-command-*
opsx-execution-preflight.md
opsx-source-resolution.md
opsx-pipeline.md
```

Also exclude `.cursor/opsx-review-commands` (admin review surface).

Branches inside the graph (core change lifecycle, bug-hunt, typing, static
check, commit/PR) may be separate subgraphs, but all stay in one GRAPH file.

## Canonical artifacts

Follow `.cursor/commands/opsx-source-resolution.md`.

```text
.cursor/pipeline/GRAPH.md
.cursor/pipeline/META.md
```

`GRAPH.md` — shared approved traversal map (states, commands, transitions,
flaws). Single materialization for all not-admin orientation.
`META.md` — freshness metadata (`updated_at`, `source_fingerprint`, `scope`,
`approved_by_token`).

Do not invent alternate graph locations or a second private navigator map.

**Source resolution / I/O budgets:** Follow
`.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

## Modes

### NAVIGATE (default) — READ_ONLY

1. Resolve `.cursor/pipeline/GRAPH.md` and `META.md` by exact path.
2. If missing → `BLOCKED_MISSING_GRAPH`. Do not invent edges.
3. Optionally resolve change name (argument / unambiguous context). If known,
   run `openspec status --change "<name>" --json` only when REQUIRED_FOR
   position detection; skip unconditional `git status`.
4. Match current position against the graph using:
   - change artifact status when available;
   - last completed not-admin command if stated in context;
   - graph entry/exit states.
5. Emit exactly one pasteable `NEXT_ACTION` (a not-admin `/opsx-*` command or
   `none` when terminal / blocked on owner). Mark it
   `RECOMMENDATION_STRENGTH: advisory`.
6. Set `ON_GRAPH: true | false`. If false, explain nearest node and that
   deviation is allowed.
7. List `KNOWN_FLAWS` that apply at this node/edge from the graph.
8. Never execute the recommended command in the same turn unless the user
   separately invoked that command.
9. Never refuse advice or mark failure only because the operator plans to
   violate the typical edge.

Freshness: if `META.md` is missing, or `source_fingerprint` cannot be checked
cheaply, proceed with `GRAPH_FRESHNESS: unknown` and recommend UPDATE when
commands were recently changed. Do not block NAVIGATE solely for unknown
freshness when GRAPH.md exists.

### UPDATE — READ_ONLY draft

Rebuild the pipeline model for owner agreement. **No file writes.**

1. Inventory not-admin command filenames (filename inventory only).
2. Grep-first for ownership / handoff / NEXT_ACTION / entry-exit tokens.
3. Parallel Read max **2**; large files: section Read ≤ 120 lines.
4. Cap substantive section-Reads at **8** per UPDATE run.
5. Build draft graph: states, commands, transitions, known flaws,
   ambiguous edges marked explicitly.
6. Compare to existing GRAPH.md if present (`DIFF_SUMMARY`).
7. Ask owner to approve with `UPDATE GO` (or revise).

Unopened commands: mark fields `NOT_OPENED_BUDGET` — do not invent.

### UPDATE GO — write materialized graph

Requires exact token `GO` as part of `UPDATE GO`.

1. Perform the same evidence pass as UPDATE (or reuse a draft from this
   conversation if it is still the active UPDATE draft and owner did not
   request a rebuild).
2. Write only:

```text
.cursor/pipeline/GRAPH.md
.cursor/pipeline/META.md
```

3. Do not edit command contracts, product code, openspec changes, or other
   process files in this mode.
4. After write, hand off commit:

```text
NEXT_ACTION: /opsx-admin-command-commit
```

If `GO` is absent while mode would be UPDATE: stay on UPDATE (no write).

## Graph schema (GRAPH.md)

Write markdown with these sections:

```text
# OPSX not-admin pipeline graph

## Meta
- scope: ALL_NON_ADMIN_OPSX
- role: shared_materialization
- authority: navigation_snapshot_only
- recommendation_strength: advisory
- operator_may_deviate: true
- not_authority_for: verify_go_nogo, archive, commit, command_contracts, forced_path

## States
- <state_id>: <one-line meaning>

## Commands
### /opsx-<name>
- purpose:
- input_state:
- output_state:
- artifacts_read:
- artifacts_written:
- decision_owner:
- next_typical:
- known_flaws:

## Transitions
state --/opsx-cmd--> state

## Known pipeline flaws
- id / where / symptom / operator workaround / do_not_pretend_fixed

## Terminal / recovery
- ...
```

`META.md`:

```text
# pipeline graph meta
updated_at_utc:
scope: ALL_NON_ADMIN_OPSX
source_fingerprint:
notes:
```

`source_fingerprint`: short stable summary of included command path list +
mtime or content hashes when cheap to compute; otherwise inventory hash of
filenames only, with `fingerprint_strength: names_only`.

## Output contract (every mode)

```text
STATUS:
MODE:
WHAT_HAPPENED:
WHY:
CURRENT_STATE:
ON_GRAPH: true | false
GRAPH_PATH:
GRAPH_FRESHNESS: fresh | stale_suspected | unknown | missing
RECOMMENDATION_STRENGTH: advisory
KNOWN_FLAWS:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### STATUS values

```text
NAVIGATED
UPDATE_DRAFT_READY
GRAPH_MATERIALIZED
BLOCKED_MISSING_GRAPH
BLOCKED_NEEDS_EVIDENCE
BLOCKED_AMBIGUOUS_POSITION
```

### Human fields (mandatory meaning)

- `WHAT_HAPPENED` — what this invocation did
- `WHY` — why that action/recommendation
- `CURRENT_STATE` — operator position in graph terms (or nearest node)
- `ON_GRAPH` — whether the current position matches a typical edge
- `RECOMMENDATION_STRENGTH` — always `advisory` for NAVIGATE
- `OWNER_DECISION_REQUIRED` — `none` or exact decision
- `NEXT_ACTION` — one pasteable **recommended** command or `none`
  (operator may ignore)
- `DO_NOT_DO_YET` — actions that would bypass **command** gates or skip
  UPDATE GO; never “do not leave the graph”

## Failure / recovery

| Condition | STATUS | NEXT_ACTION |
|---|---|---|
| GRAPH.md missing on NAVIGATE | `BLOCKED_MISSING_GRAPH` | `/opsx-pipeline UPDATE` |
| Position ambiguous | `BLOCKED_AMBIGUOUS_POSITION` | ask one clarifying question OR `/opsx-pipeline UPDATE` |
| Evidence budget exhausted on UPDATE | `BLOCKED_NEEDS_EVIDENCE` | narrow extraction request |
| Redesign needed (not navigation) | stay navigational | `/opsx-admin-command-analyze-pipeline` |
| After UPDATE GO | `GRAPH_MATERIALIZED` | `/opsx-admin-command-commit` |

## Anti-patterns (reject)

- Inventing graph edges without command evidence
- Treating GRAPH.md as override of verify/archive/commit
- Treating GRAPH.md as a mandatory path the operator must follow
- Scolding or blocking the operator for off-graph choices
- Building a second private graph instead of the shared materialization
- Executing recommended not-admin commands inside `/opsx-pipeline`
- Writing GRAPH without `UPDATE GO`
- Mixing admin-command redesign into this assistant
- Hiding known flaws to make the pipeline look cleaner
- Creating a second GO/NO_GO taxonomy for the whole lifecycle

## Self-review checklist

Before returning:

- [ ] Mode parsed correctly (`UPDATE GO` ≠ `UPDATE`)
- [ ] NAVIGATE/UPDATE did not write files
- [ ] UPDATE GO wrote only `.cursor/pipeline/**`
- [ ] Exactly one `NEXT_ACTION`, marked advisory on NAVIGATE
- [ ] Shared materialization used (no alternate durable map)
- [ ] Graph not claimed as lifecycle authority or forced path
- [ ] Off-graph deviation allowed without framing as failure
- [ ] Known flaws surfaced when relevant
- [ ] After UPDATE GO, next step is `/opsx-admin-command-commit`
