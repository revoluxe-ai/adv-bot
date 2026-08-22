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
- Producer commands (`/opsx-spec-scenario-coverage`, `/opsx-external-call-coverage`,
  `/opsx-verify`, …) emit `LOCAL_HOP_COPY_BLOCK` with runnable hops.
  `/opsx-pipeline` NAVIGATE **reuses** packet bodies from chat when recommending
  the same consumer — it does not replace producers with paste-advice prose.

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

- Unclear which process/admin command applies, or need to discuss
  command relationships / odd admin behavior → `/opsx-admin-command-consult`
- Redesign or improve process contracts → `/opsx-admin-command-analyze-pipeline`
- Fix command defects → `/opsx-meta-fix-command-defects`
- Design a new command → `/opsx-admin-command-design-command`
- Commit process surfaces → `/opsx-meta-commit`
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
   **Executable-now rule:** `NEXT_ACTION` must be Owner-runnable as written.
   Forbidden in `NEXT_ACTION` (and in the primary `LOCAL_HOP_COPY_BLOCK`
   `Command:` line): angle-bracket packet stubs (`<paste…>`,
   `<paste that packet>`), empty packet bodies, or any content that is not
   already present in this turn’s chat evidence. If the true consumer hop
   needs a packet that does not yet exist → set `NEXT_ACTION` to the
   **packet-producing** command (e.g. `mode=audit`), never the consumer
   with a fake paste.
6. Set `ON_GRAPH: true | false`. If false, explain nearest node and that
   deviation is allowed.
7. List `KNOWN_FLAWS` that apply at this node/edge from the graph.
8. When `NEXT_ACTION` is a pasteable `/opsx-*` command (not `none`), emit
   exactly one `LOCAL_HOP_COPY_BLOCK` (see Output) after the structured
   fields. The fence is the **primary Owner copy-paste hop** — not prose
   advice about where to paste. Pattern mirrors
   `.cursor/pipeline/contracts/VERIFY_PHASES.md` `LOCAL_HOP_COPY_BLOCK`:
   one fenced plain-text block with Workspace, Change, Current state,
   `Command:` (exact filled args, **one line, no packet body**), then any
   inline packet body when evidence exists, `DO_NOT_DO_YET`, `ALSO_OK`.
   Outside that fence: at most one status line. No Web four-block form.
9. **Chat-evidence lift (mandatory when packet exists):** If `NEXT_ACTION`
   is a packet consumer (`/opsx-test`, `/opsx-close-external-gap`, …) and
   a complete packet already appears in this conversation (prior command
   output: `SCENARIO_TEST_ONLY_PACKET`, `TEST_ONLY_PACKET`,
   `SCENARIO_REFACTOR_AND_TEST_PACKET`, `CERTIFY_PACKET`, or fenced
   `LOCAL_HOP_COPY_BLOCK` from `/opsx-spec-scenario-coverage`,
   `/opsx-external-call-coverage`, etc.), duplicate the **full packet text**
   inside `LOCAL_HOP_COPY_BLOCK` immediately after `Command:` — do not tell
   Owner to «paste from above», «see ROUTE_PACKETS», or «insert packet from
   audit». Prose-only handoff when the packet is already in chat = invalid
   NAVIGATE output (self-review FAIL).
   When the packet does **not** yet exist: `NEXT_ACTION` = producer only;
   sequenced consumer belongs in `ALSO_OK` / `DO_NOT_DO_YET` (e.g. after
   audit returns packet → `/opsx-test`) — never as current hop with
   placeholder paste.
10. Never execute the recommended command in the same turn unless the user
    separately invoked that command.
11. Never refuse advice or mark failure only because the operator plans to
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
NEXT_ACTION: /opsx-meta-commit
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
ALSO_OK:
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
- `NEXT_ACTION` — one line: pasteable **recommended** command or `none`
  (operator may ignore). Must be executable now — **no packet body** on
  this line, no packet placeholders.
- `ALSO_OK` — optional advisory alternate or **sequenced** follow-up only
  when the packet for a consumer hop is **not** yet in chat evidence
  (solo walk, explore, handback, “after producer returns packet X → run
  consumer”). Does **not** replace `NEXT_ACTION`. Never frame ignoring
  `NEXT_ACTION` for an `ALSO_OK` path as a violation. Never put a
  packet-consumer in `ALSO_OK` as if runnable with `<paste that packet>` when
  the packet is already in chat — lift it into `LOCAL_HOP_COPY_BLOCK` instead.
- `DO_NOT_DO_YET` — actions that would bypass **command** gates or skip
  UPDATE GO; never “do not leave the graph”; list premature consumer hops
  only when producer packet is still missing

### LOCAL_HOP_COPY_BLOCK (mandatory on NAVIGATE when NEXT_ACTION is a command)

After the structured Output fields above, when `NEXT_ACTION` is a pasteable
`/opsx-*` (not `none`), emit exactly **one** fenced copy-paste prompt.
Bare `NEXT_ACTION:` does **not** replace this block. Owner runs **this
fence** in a new chat — not a hunt through prior messages.

**Shape (fill from run — no packet stubs):**

```text
Workspace: <abs-path>
Change: <change-name or none>
Current state: <CURRENT_STATE>
Command: <exact NEXT_ACTION — one /opsx-… line, filled args, no packet>
<when packet in chat evidence: full SCENARIO_TEST_ONLY_PACKET | TEST_ONLY_PACKET | REFACTOR_AND_TEST | CERTIFY body here>
DO_NOT_DO_YET: <gates / premature consumers>
ALSO_OK: <sequenced alternate or none>
```

Rules:

1. `Command:` = **only** the single-line invocation (e.g.
   `/opsx-spec-scenario-coverage mode=audit change=fair-leg-pause-billing`
   or `/opsx-test`).
2. Packet consumers: if recommending `/opsx-test` and
   `SCENARIO_TEST_ONLY_PACKET` exists in conversation → paste **entire**
   packet under `Command:` (same for `/opsx-close-external-gap` + Scenario /
   ECC packets). Aligns with producer commands that emit
   `LOCAL_HOP_COPY_BLOCK` (`/opsx-spec-scenario-coverage`, `/opsx-verify` …).
3. Simple hops (no packet): fence ends after `Command:` + `DO_NOT_DO_YET` /
   `ALSO_OK`.
4. Forbidden: «вставьте packet из audit», «см. ROUTE_PACKETS выше»,
   `Command: /opsx-test (+ SCENARIO_TEST_ONLY_PACKET из прошлого audit)` as
   substitute for full packet body.

Outside the fence (except structured report above): at most **one** status
line. Forbidden: Web four-block form; inventing packet bodies not in chat
evidence.

When at a bug-episode fork (see GRAPH soft `BUG_EPISODE_FORK` /
`CLOSE_POLICY.md`): set `NEXT_ACTION` to the **PRIMARY** path for the
current node (often team handback after GREEN/invariant/Owner-block exit,
or apply/fix-bug while mid solo walk); put the other path in `ALSO_OK`
with `case=` IDs. Never recommend a silent return to bug-team.

## Failure / recovery

| Condition | STATUS | NEXT_ACTION |
|---|---|---|
| GRAPH.md missing on NAVIGATE | `BLOCKED_MISSING_GRAPH` | `/opsx-pipeline UPDATE` |
| Position ambiguous | `BLOCKED_AMBIGUOUS_POSITION` | ask one clarifying question OR `/opsx-pipeline UPDATE` |
| Evidence budget exhausted on UPDATE | `BLOCKED_NEEDS_EVIDENCE` | narrow extraction request |
| Redesign needed (not navigation) | stay navigational | `/opsx-admin-command-analyze-pipeline` |
| Process ambiguity / which admin command? | stay navigational | `/opsx-admin-command-consult` |
| After UPDATE GO | `GRAPH_MATERIALIZED` | `/opsx-meta-commit` |

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
- Emitting `NEXT_ACTION` / primary fence with `<paste that packet>` or
  other stubs for packets not yet in chat evidence
- Prose-only handoff when packet exists in chat («paste from audit»,
  «see ROUTE_PACKETS») instead of full fence with packet body
- Recommending `/opsx-close-external-gap` (or any packet consumer) as the
  current hop before the packet-producing command has returned
  `ROUTE_PACKETS` / Scenario fences **and** that packet is not already in chat
- Omitting `LOCAL_HOP_COPY_BLOCK` on NAVIGATE when `NEXT_ACTION` is a command
- `LOCAL_HOP_COPY_BLOCK` with only `Command:` when consumer needs packet that
  is already in conversation evidence

## Self-review checklist

Before returning:

- [ ] Mode parsed correctly (`UPDATE GO` ≠ `UPDATE`)
- [ ] NAVIGATE/UPDATE did not write files
- [ ] UPDATE GO wrote only `.cursor/pipeline/**`
- [ ] Exactly one `NEXT_ACTION`, marked advisory on NAVIGATE
- [ ] `NEXT_ACTION` executable now (no packet placeholders)
- [ ] `LOCAL_HOP_COPY_BLOCK` present when NAVIGATE `NEXT_ACTION` is a command
- [ ] Fence includes full packet body when consumer hop + packet in chat
- [ ] Packet consumers only as sequenced `ALSO_OK` / `DO_NOT_DO_YET` when
  producer packet not yet in evidence
- [ ] `ALSO_OK` used for bug-episode forks (team vs solo) when relevant
- [ ] Shared materialization used (no alternate durable map)
- [ ] Graph not claimed as lifecycle authority or forced path
- [ ] Off-graph deviation allowed without framing as failure
- [ ] Known flaws surfaced when relevant
- [ ] After UPDATE GO, next step is `/opsx-meta-commit`
