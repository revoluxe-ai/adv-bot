---
component_id: opsx.commands.evolution
component_version: 1.0.0
ownership: TARGET_ONLY
runtime_class: ACTIVE
contract_id: OPSX-WB-EVOLUTION-01
canonical_source_body: adapted_target_native
source_command_sha256: b9a43046e1a29c30308ffdffe2fbcda737b3e7cf628aaece3d585b81578a87f9
required_adapters: ["opsx-lite"]
local_modification_note: "Imported 2026-08-07 via /opsx-meta-import-command KEEP=opsx-evolution; remapped GAME→WB; companions not in donor"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-EVOLUTION-01`  
**Runtime class:** `ACTIVE`  
**Authority:** project-local North Star planning under `openspec/evolution/**`.
`DOTO/WORKLOG.md` is secondary raw Owner notes only — never the registry SoT.

## Target safety and authority

Before any write, read `.opsx/projectization.yaml`. If projectization is not
`COMPLETE` or normal commands are disabled, return:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

Authoritative target paths:

```text
policy:   openspec/policies/EVOLUTION_POLICY.md
index:    openspec/evolution/index.md
template: openspec/evolution/_template/north-star.md
cards:    openspec/evolution/<star-slug>.md
worklog:  DOTO/WORKLOG.md   (secondary peek; raw notes; not SoT)
decisions: openspec/decisions/**
```

Hard bans:

- no product-code (`app/**`), dependency, `pyproject.toml` / Poetry lock,
  `package.json`, production, secret, deployment, remote Git, PR, or archive mutation;
- no source-project domain assumptions;
- no writes without an accepted current draft and exact Owner `GO`;
- `GO` authorizes only the disclosed card/index writes;
- do not invoke downstream commands automatically;
- do not treat `openspec/config.yaml` `rules.*` as Evolution SoT; follow
  `EVOLUTION_POLICY` + registry only.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` for bounded reads and writes.
No standalone store or upstream runtime is required on this WB Sky / Poetry target.

# /opsx-evolution

Human-native front door for durable product evolution **and** the owner of
task-narrowed handoff onto a new/apply-ready OpenSpec change for capability /
star work:

```text
idea → existing/new North Star → STAR_ROUTE (advisory)
     → CHANGE_CANDIDATES (+ one RECOMMENDED) → Owner pick
     → COPY_BLOCK (paste SoT)
     → Owner Copy → new chat → Owner types /opsx-new | /opsx-ff | /opsx-update
```

Do **not** jump from «star saved» straight to `/opsx-ff` without showing
`STAR_ROUTE`, **`CHANGE_CANDIDATES`** (with one **`RECOMMENDED`**), and an
Owner pick/confirm of the next Change / increment.

**ROLE:** Help the Owner choose **one well-bound OpenSpec Change** that fits a
single finished thought — not a wish list. After pick + `ARTIFACT_CONTEXT`
study, print an exhaustive **`COPY_BLOCK`** (paste SoT for that change). Owner
copies it into a new chat and chooses `/opsx-new` | `/opsx-ff` | `/opsx-update`
**themselves**. Do **not** put `/opsx-*` inside the COPY_BLOCK fence.
`/opsx-explore` researches and may emit `EVOLUTION_CANDIDATE`; it does not own
that handoff. No durable handoff file is required.

Examples:

```text
/opsx-evolution
/opsx-evolution Хочу поэтапно развивать крупную возможность WB Sky
/opsx-evolution star=<id>
/opsx-evolution 3
/opsx-evolution n=7
/opsx-evolution GO
```

The human does not need to know modes or `STAR_ID`. Infer map, lookup, draft,
revision, or persistence from intent.

## Core boundary

Read and follow `openspec/policies/EVOLUTION_POLICY.md`.

```text
North Star         = long-term direction
Evolution Path     = revisable increment hypotheses
Current Increment  = only scope owed by the next/current change
Future Increments  = context only, never current DoD
```

This command never creates an OpenSpec change, edits implementation, applies a
task, verifies a change, archives it, or commits it.

`DOTO/WORKLOG.md` is **secondary** raw notes (per `EVOLUTION_POLICY` Authority):
it may mention `STAR_ID` / `INCREMENT_ID` / deferred parks. Peek and account for
relevant lines; never treat WORKLOG as North Star registry, Current Increment
DoD, or paste SoT. This command never writes or appends WORKLOG
(`/opsx-bound-scope:GO` owns deferred parks).

## Relationship to other commands

| Need | Owner |
|---|---|
| Deep research / wise all-round counsel (not speed) | `/opsx-explore` |
| Persist/find/revise a North Star, pick increment, **handoff to new/ff/update** | this command |
| Create a step-by-step change | `/opsx-new` (after evolution handoff when capability-sized) |
| Create an apply-ready change | `/opsx-ff` (after evolution handoff when capability-sized) |
| Reconcile an existing change | `/opsx-update` |
| Cut an oversized change | `/opsx-bound-scope` |

`/opsx-explore` may emit an `EVOLUTION_CANDIDATE`; it never writes cards and must
not be the primary «Want `/opsx-ff`?» door for capability/star work. This
command validates that candidate against the registry and produces an approved
`EVOLUTION_HANDOFF`. STANDALONE / NOT_APPLICABLE local maintenance may skip
the star path when explicitly labeled.

## Human-native operation inference

```text
no goal / "что есть?"       → show active map (READ_ONLY)
natural-language goal       → bounded overlap lookup + draft (READ_ONLY)
exact title / star=<id>      → card status + next-increment draft (READ_ONLY)
GO                           → persist the last still-current accepted draft
```

If `GO` is supplied without a current accepted draft in this conversation,
return `BLOCKED_NEEDS_PLAN`. Never reconstruct approval from another chat or an
old transcript.

## Applicability

```text
LINKED          — approved card/increment selected
STANDALONE      — Owner intentionally wants an unlinked change
LEGACY_UNLINKED — existing change predates this policy
CANDIDATE       — capability-sized work likely benefits from a card
NOT_APPLICABLE  — local bugfix/refactor/maintenance
```

Linking is optional. Do not force a card for local fixes or legacy work. For an
unlinked capability-sized change, show a recommendation and bounded overlap
candidates; do not hard-block `/opsx-new` or `/opsx-ff`.

## Change candidate selection (boundary reviewer)

On advice / `ROUTE_SHOWN` / «с чего начать» / post-save pick-prep turns
(**not** pure `MAP_SHOWN`), **before** `COPY_BLOCK`, act as a **Change boundary
reviewer** (not a mechanical splitter) and emit chat-only
**`CHANGE_CANDIDATES`**.

**Governing question:**

```text
Какой следующий самостоятельный результат имеет достаточную ценность и при
этом естественно помещается в одну мысль, которую агент сможет понять,
реализовать и проверить без необходимости самостоятельно додумывать ещё
несколько продуктовых решений?
```

### Count

Default **5** candidates. If the Owner argument is an integer (`3`, `7`, `10`)
or `n=<int>`, emit **exactly** that many (clamp **1..10**).

### What counts as a good Change candidate

A Change has **one clear intent**: one finished behavior/capability change that
can be accepted, implemented, and verified on its own.

- Do **not** split by file count, module count, task count, or guessed code
  volume. Diff size / specs/tasks/models count is **never** the primary signal.
- A large Change is OK when every part is required for **one** result.
- A small Change should be split when it actually contains **two** independently
  meaningful goals.

For each candidate, check:

- can its meaning be one sentence without «и ещё заодно»;
- do its parts serve one result and need each other for correctness;
- can a part be independently deferred, accepted, rolled back, or verified;
- do separate ownership / lifecycle / failure / verification models appear inside;
- is a useful-but-standalone capability included only because it sits nearby in
  code.

If a natural independent slice appears → propose it as a **separate** Change,
not auto-include it. Do **not** fragment for fragmentation's sake: if the Owner
thinks of one finished function and splitting would create artificial
cross-change deps, keep one Change.

### Value

Prefer candidates that combine: clear natural boundary + noticeable standalone
value + finishable verifiable result + no packing of independent goals.

- Do not prefer an ideally tiny Change that barely delivers alone.
- High value does **not** justify merging several independent Changes.
- When value lands only after a series, label each candidate's value class:
  `STANDALONE` | `ENABLING_FOUNDATION` | `UNLOCK_ONLY` (visible at pick time).

### Wide or couple-able wants

- Valuable but too wide → do **not** discard. Show that the idea is valuable
  but contains several Changes; propose the most natural **first** Change plus
  boundaries of the later ones.
- Two wants that lack finished sense alone → may propose **one** joint Change
  and explain the coupling.

### Recommendation card shape (each of N)

```text
CHANGE_CANDIDATES:
- Change: <short working title>
  Мысль: <one-sentence finished intent>
  Почему такая граница: <why one Change; what is consciously out>
  Ценность: <what lands after THIS Change> | class: STANDALONE | ENABLING_FOUNDATION | UNLOCK_ONLY
  Зависимости: <real predecessors/blockers only, or none>
  Не включать: <nearby wants that must stay separate Changes>
RECOMMENDED: <exactly one Change title from the list>
```

Do **not** write full proposal/design/tasks here.

### RECOMMENDED

Exactly **one** candidate marked `RECOMMENDED` — best **next** Change by:
standalone value, boundary coherence, requirements readiness, dependencies,
risk, finished verifiable result, and reasonable agentic context/coordination
cost. Not merely «most valuable» and not merely «smallest».

### Mapping and pick gate

Candidates **MAY** align to a card `INCREMENT_ID` / existing
`SUGGESTED_CHANGE`, or propose split/merge vs card increments. Owner may
override `RECOMMENDED`. Do **not** emit `COPY_BLOCK` until Owner pick/confirm.
`CHANGE_CANDIDATES` / `RECOMMENDED` are **chat-only** — never inside the
`COPY_BLOCK` fence.

## READ_ONLY plan flow

1. Read the policy and `openspec/evolution/index.md` first.
1b. **Secondary WORKLOG peek** (mandatory on draft / advice / `ROUTE_SHOWN` /
    pick-prep / handoff turns; lightweight or skippable only for pure
    `MAP_SHOWN` «что есть?» / index-only):

    - Path: `DOTO/WORKLOG.md`. If missing → continue with
      `WORKLOG not found, continuing without it.` (never FAIL / never
      `EVIDENCE_GAP` solely for absence).
    - Prefer bounded `Grep` for selected `STAR_ID`, theme aliases,
      `[deferred-from:…]`, or Owner goal keywords; do **not** dump the whole
      inbox into advice.
    - Emit chat-only **`WORKLOG_CONTEXT`** (label notes `Worklog-derived`):

      ```text
      WORKLOG_CONTEXT:
      - status: read | missing_continue
      - relevant_notes: <0..N one-liners, Worklog-derived>
      - influence: none | overlap_hint | priority_hint | deferred_park_seen
      ```

    - Use as overlap / priority / deferred-park hints only. Do **not**
      auto-promote every WORKLOG line into `CURRENT_INCREMENT`,
      `CHANGE_CANDIDATES`, `FUTURE_INCREMENTS`, or `COPY_BLOCK`. On conflict,
      prefer registry card + `ARTIFACT_CONTEXT` over WORKLOG.
2. Resolve an exact selected card, or read at most three strongest candidates.
3. Search overlap using titles/aliases, capability scope, domains, linked
   active/archived changes, Current/Future Increment outcomes, and any
   `WORKLOG_CONTEXT` hints from step 1b.
4. Display candidates as `Title (STAR_ID)` with one-line overlap reasons.
5. If several plausible cards exist, ask one Owner question:

```text
Использовать существующую | связать направления | создать отдельную?
```

6. Build or revise:
   - `NORTH_STAR`;
   - `EVOLUTION_PATH`;
   - exactly one `CURRENT_INCREMENT`;
   - `CONTRIBUTION_TO_NORTH_STAR`;
   - `FORWARD_COMPATIBILITY_CONSTRAINTS`;
   - `OUT_OF_SCOPE`;
   - `FUTURE_INCREMENTS`;
   - `DEPENDS_ON` / Related edges when linking stars (unidirectional DAG).
7. Check relevant accepted decisions under `openspec/decisions/**`. A card may
   describe direction but must not contradict an accepted architecture decision.
8. Verify Current Increment is independently testable/verifiable and excludes
   future wishes.
9. Build MAP / plan UX from policy **Star dependency DAG**:
   - show star `DEPENDS_ON` edges (no cycles);
   - emit `DEPENDS_ON_WARN` when parents are not yet sufficient (**SOFT** — do
     not hard-block handoff or recommend blocking `/opsx-new` / `/opsx-ff`);
   - show `VALUE_CHAIN` (depth ≤ 3): increment → this star → parents.
10. Emit **`STAR_ROUTE`** (advisory achievement route) from the card
    `EVOLUTION_PATH` (+ star DAG sketch): ordered `INCREMENT_ID` / title /
    `STATUS`; label that the route **may go stale or be wrong** — not DoD, not
    a promised backlog. Mark ACTIVE and/or suggested-next increment.
10b. Emit **`CHANGE_CANDIDATES`** (+ exactly one **`RECOMMENDED`**) per
    **Change candidate selection (boundary reviewer)** — default N=5 or Owner
    `n=<int>` / bare integer arg. This is the primary pick surface; `STAR_ROUTE`
    remains advisory context, not a substitute for well-bound Change options.
11. **Artifact study before increment advice / COPY_BLOCK** (mandatory when this
    turn recommends a next `INCREMENT_ID` / Change candidate, answers «с чего
    начать», or will emit `COPY_BLOCK` after pick). Pure `MAP_SHOWN`
    («что есть?» / index-only) MAY skip this step.

    Bounded lookup (prefer exact paths from card domains / `LINKED_CHANGES` /
    increment text; no full recursive dump):

    1. relevant `openspec/specs/**` for the increment's capability domains
       (typical budget ≤ 3 specs unless `EVIDENCE_GAP` expands);
    2. active `openspec/changes/**` that overlap the increment;
    3. Prefer `openspec/changes/archive/**` (canonical archive SoT). Use
       `openspec/archive/**` only as **legacy read-only fallback** when nested
       has no hit and older delivery evidence may still live there
       (`LINKED_CHANGES` empty, domains match archived work, or delivery risk
       is «already done / partial»). Do not treat legacy as write target.

    Emit **`ARTIFACT_CONTEXT`** in chat before advice/COPY_BLOCK:

    ```text
    ARTIFACT_CONTEXT:
    SPECS:
    - <path> — <one-line relevance>
    CHANGES_ACTIVE:
    - <path or none>
    CHANGES_ARCHIVE:
    - <path or none | skipped_reason>
    VERDICT_PER_HIT: ALREADY_DELIVERED | PARTIAL | GAP | N/A
    ```

    Material gaps (unread required artifact within budget, or contradiction
    with card ACTIVE status) → `EVIDENCE_GAP`; do **not** invent KEEP /
    suggested change slug from card prose alone. Do not reopen unbounded
    decision dumps (decisions stay context-first per step 7).
12. **`OWNER_CHOICE`**: present `CHANGE_CANDIDATES` + `RECOMMENDED`; ask Owner
    to confirm `RECOMMENDED` or pick another listed candidate (or an explicit
    ACTIVE/`CANDIDATE` increment that maps to one). Do not emit `COPY_BLOCK`
    until that pick/confirm (or the draft already records an explicit
    Owner-chosen `INCREMENT_ID` / Change). After pick: when
    `ARTIFACT_CONTEXT.CHANGES_ACTIVE` is non-empty and a hit is (or will be)
    `SUGGESTED_CHANGE`, emit chat-only **`EXISTING_CHANGE_COLLISION`** (see
    Chat-only context) **before** the fenced COPY_BLOCK; then print COPY_BLOCK
    (SUGGESTED_CHANGE + KEEP from `ARTIFACT_CONTEXT`). Soft exit / return
    `NEXT_ACTION` MUST follow collision rules (DRIFTED|UNKNOWN → lead
    `/opsx-update`; SAME → `/opsx-ff`|`/opsx-new`|`/opsx-update` OK). Prefer
    keeping `SUGGESTED_CHANGE` as the existing directory for reconcile; do not
    greenfield a change that archives already delivered work.
13. Show exact file writes and stop for Owner `GO`.

Similarity never authorizes an automatic merge. Missing material evidence is
`EVIDENCE_GAP`, not permission to guess.

## GO flow

Exact Owner `GO`, or an explicit request to persist the displayed current draft,
authorizes only the disclosed local registry writes.

1. Recheck that the accepted draft and target paths are still current.
2. Validate star DAG edges in the draft: `DEPENDS_ON` targets exist (or are
   created in the same disclosed multi-card GO); **refuse cycles** (`NO_GO`).
3. New card:
   - derive a stable kebab-case `STAR_ID`;
   - create `openspec/evolution/<star-slug>.md` from the template;
   - add exactly one row to `openspec/evolution/index.md` (include **Depends on**).
4. Existing card:
   - preserve `STAR_ID`;
   - update semantic sections only;
   - append a concise History entry;
   - preserve delivered evidence as evidence, not a future hypothesis;
   - keep index **Depends on** in sync with card `DEPENDS_ON`.
5. Re-read the written card and index and validate required fields and exact link.
6. Emit **`STAR_ROUTE`** (advisory) from the saved card(s) `EVOLUTION_PATH` +
   star `DEPENDS_ON` sketch. Include the stale/incorrect disclaimer.
7. If Owner has not yet confirmed/picked the next Change / `INCREMENT_ID` in
   this conversation, stop with `STATUS: ROUTE_SHOWN` (or keep `CARD_SAVED` +
   `OWNER_DECISION_REQUIRED: yes`) — emit `STAR_ROUTE` + `CHANGE_CANDIDATES` +
   `RECOMMENDED`; **do not** jump to `/opsx-ff` yet.
8. After Owner pick/confirm, run READ_ONLY step 11 artifact study if not
   already current for that `INCREMENT_ID` / Change in this conversation. If
   study yields `EVIDENCE_GAP`, do not emit COPY_BLOCK until gaps are closed or
   Owner explicitly accepts STANDALONE with recorded gap.
9. Emit chat context (STAR_ROUTE, CHANGE_CANDIDATES, RECOMMENDED,
   ARTIFACT_CONTEXT, DEPENDS_ON, DEPENDS_ON_WARN, VALUE_CHAIN, and when
   applicable `EXISTING_CHANGE_COLLISION` + `RENAME_HINT`) for humans in this
   conversation — **not** inside the paste fence. Then emit exactly one
   fenced **`COPY_BLOCK`** (see template below) as the only paste payload.
   Outside the fence, soft exit / `NEXT_ACTION` MUST follow collision rules
   in Chat-only context (never embed those commands inside COPY_BLOCK).
   WARN / thin KEEP / `/opsx-bound-scope` remain allowed. Never treat bare
   `/opsx-ff` after star save as sufficient without COPY_BLOCK.
10. Do not invoke downstream commands automatically. Do not require a durable
    handoff file on disk.

## Card requirements

Every card contains:

```text
STAR_ID
STATUS
OWNER
NORTH_STAR
CAPABILITY_SCOPE
EVOLUTION_PATH
CONTRIBUTION_TO_NORTH_STAR for every increment
FORWARD_COMPATIBILITY_CONSTRAINTS
NON_GOALS
RELATED_NORTH_STARS
HISTORY
```

Each increment has a stable `INCREMENT_ID`, title, outcome, status, linked
changes/evidence when known, and a causal contribution statement. Candidate
increments are hypotheses, not tasks.

## COPY_BLOCK (paste SoT — after OWNER_PICK)

Print **one** fenced block the Owner can Copy into a new chat. Exhaustive for
the owed task; no essay; **no `/opsx-*` lines inside the fence**. Fence MUST
contain **only** the template keys below (exact headers). Downstream
`/opsx-ff` / `/opsx-new` / `/opsx-update` / `/opsx-continue` treat **canonical
keys** as DoD SoT — they MUST NOT re-open the North Star card body to invent
Future scope or broaden `IN_SCOPE`.

**Completeness invariant:** `OWNER_INTENT`, `IN_SCOPE`, `OUT_OF_SCOPE`,
`FORWARD_COMPATIBILITY`, `KEEP`, and `HARD` MUST be concrete enough that a
consumer with paste alone can scaffold/ff/continue without reading
`openspec/evolution/<card>.md` for DoD. `OWNER_INTENT` MUST preserve the
Owner's human meaning (see rules below). If study shows the handoff would be
incomplete → `EVIDENCE_GAP`; do **not** emit COPY_BLOCK until fixed or Owner
accepts STANDALONE with recorded gap. Never recommend pasting chat-only
fields (`CARD_PATH`, `STAR_ROUTE`, `ARTIFACT_CONTEXT`, …) into new/ff/continue.

```text
EVOLUTION_HANDOFF
EVOLUTION_LINK: LINKED
STAR_ID: <stable id>
INCREMENT_ID: <stable id>
OWNER_INTENT:
<short human Owner meaning — product/UI language; not implementation mapping>
CURRENT_INCREMENT: <one independently verifiable outcome>
IN_SCOPE:
- <owed unit>
OUT_OF_SCOPE:
- <explicit exclusion>
FORWARD_COMPATIBILITY:
- <constraint required now>
FUTURE_INCREMENTS (context only — NOT tasks/DoD):
- <INCREMENT_ID>
SUGGESTED_CHANGE: <kebab-slug or existing change name>
KEEP: <thin boundary one-liner>
HARD: EVOLUTION_SCOPE_DRIFT if artifacts/tasks include OUT_OF_SCOPE or FUTURE_INCREMENTS
```

`FUTURE_INCREMENTS`: **INCREMENT_ID lines only** — no outcome/title essays that
invite “prep” tasks.

### OWNER_INTENT (mandatory canonical key)

`OWNER_INTENT` is the durable semantic input for `/opsx-explore` → `/opsx-new`.
It is **not** a technical solution description and **not** interchangeable with
`CURRENT_INCREMENT` / `KEEP` / `HARD`.

**Source:** only Owner words, or a later explicit Owner correction. Agent
inference, repository findings, evolution decomposition, KEEP/HARD/FORWARD, and
implementation mapping MUST NOT silently rewrite it.

**MUST**

- preserve Owner terminology and UI / product names when Owner used them;
- describe the desired result / observable behavior, not presumed code paths;
- stay short and readable to Owner without internal jargon Owner did not use;
- survive further evolution decomposition unchanged in meaning.

**MUST NOT**

- replace Owner product language with code identifiers found in the repo
  (e.g. Owner «старое управление ставкой» → `cost_rule_failed` /
  `cost watchdog`) without explicit Owner confirmation;
- treat repository-plausible mappings as a new Owner intent;
- omit the field from COPY_BLOCK after OWNER_PICK when emitting
  `CURRENT_INCREMENT_READY`.

Repository evidence and candidate mappings belong in chat-only context
(`ARTIFACT_CONTEXT`, study notes) — never as a substitute for `OWNER_INTENT`.
If Owner wording contradicts repository reality → ask one clarification via
existing Owner-question flow; do **not** rewrite `OWNER_INTENT` to match the
code.

### FORBIDDEN inside COPY_BLOCK fence

Do **not** put these sections or tokens inside the paste fence (they bait
scope drift / wrong-lane DoD):

```text
VALIDATION* / VALIDATION HINTS
ALREADY_DELIVERED
GAP (as a section header)
DECISIONS (dumps / cite lists)
STAR_ROUTE / VALUE_CHAIN / ARTIFACT_CONTEXT / DEPENDS_ON*
CHANGE_CANDIDATES / RECOMMENDED
WORKLOG_CONTEXT / Worklog-derived dumps
any /opsx-* slash command
live-deploy / devops / soft_prod_server_ops “do this now” prose
RENAME_HINT
EXISTING_CHANGE_COLLISION
```

Thin forbid/re-do boundaries belong in `OUT_OF_SCOPE` / `KEEP` /
`FORWARD_COMPATIBILITY` only — not as extra paste sections.

### Chat-only context (not inside COPY_BLOCK)

Still emit for this conversation when useful: `STAR_ROUTE`,
`CHANGE_CANDIDATES`, `RECOMMENDED`, `ARTIFACT_CONTEXT` (incl. ALREADY_DELIVERED
/ GAP / validation notes), `WORKLOG_CONTEXT` (secondary raw notes; never SoT),
`DEPENDS_ON`, `DEPENDS_ON_WARN`, `VALUE_CHAIN`,
contribution notes, decision cites, `CARD_PATH` / North Star title. These help
humans here; they are **not** the paste payload and must not replace
COPY_BLOCK.

**`EXISTING_CHANGE_COLLISION` (chat-only, mandatory when applicable):** When
`ARTIFACT_CONTEXT.CHANGES_ACTIVE` is non-empty and a hit is chosen (or is the
only/primary overlap) as `SUGGESTED_CHANGE`, emit **before** COPY_BLOCK:

```text
EXISTING_CHANGE_COLLISION:
- change: <kebab>
- scope_compare: SAME | DRIFTED | UNKNOWN
- NEXT_ACTION: <see rules below>
- ALSO_OK: <optional>
```

`scope_compare` rules (bounded read of that change's `proposal.md` Evolution
Context when present; do not dump the whole change tree):

- `SAME` — proposal `INCREMENT_ID` matches paste `INCREMENT_ID` and KEEP is
  compatible with `CURRENT_INCREMENT` / `KEEP`.
- `DRIFTED` — proposal `INCREMENT_ID` / `STAR_ID` / KEEP conflicts with paste
  `CURRENT_INCREMENT` / `KEEP` / `STAR_ID`.
- `UNKNOWN` — no Evolution Context in proposal, or unread within budget.

Collision → soft exit / return `NEXT_ACTION`:

- `DRIFTED` | `UNKNOWN` → **lead** with `/opsx-update` (reconcile content to
  paste). `/opsx-new` / `/opsx-ff` only as `ALSO_OK` when Owner explicitly
  rejects reuse or chooses STANDALONE / a new name.
- `SAME` → `/opsx-ff` | `/opsx-new` | `/opsx-update` are all fine; prefer the
  Owner's stated pace (ff vs step-by-step new).

When no `CHANGES_ACTIVE` hit applies, soft exit may list:

```text
Owner chooses next command: /opsx-ff | /opsx-new | /opsx-update
```

**`RENAME_HINT` (chat-only, mandatory when triggered):** Emit outside the fence
when `SUGGESTED_CHANGE` is an **existing** kebab and either:

1. slug tokens include `placeholder` | `stub` | `honest-placeholder` (or
   similar) **and** `CURRENT_INCREMENT` / `KEEP` is not stub-only; **or**
2. `scope_compare=DRIFTED` and a slug rename is likely so the folder name
   matches the new KEEP.

```text
RENAME_HINT: /opsx-rename-change change=<old>
  (ANALYZE: content → numbered OPTIONS + WHY; Owner picks N or to= + GO);
  then /opsx-evolution GO to retarget LINKED_CHANGES;
  then /opsx-update under the new name for content. Do not put RENAME_HINT
  inside COPY_BLOCK. Do not git mv from this command.
```

When `RENAME_HINT` fires under `DRIFTED`|`UNKNOWN`, soft exit / `NEXT_ACTION`
may lead with `/opsx-update` and put rename in `ALSO_OK`, **or** lead with
`/opsx-rename-change` then update — either order is OK; do not omit the hint.

Prefer keeping `SUGGESTED_CHANGE` as the **existing** directory name when
reconciliation is the intent; slug rename is owned by `/opsx-rename-change`,
not a second change.

The handoff constrains a linked change. It never authorizes implementation.
`DEPENDS_ON_WARN` is informational under `DEPENDS_ON_MODE: SOFT`.
`ARTIFACT_CONTEXT` remains mandatory on pick/advice turns (chat); omit only
for pure `MAP_SHOWN`. No durable handoff file.

## Return contract

```text
STATUS: MAP_SHOWN | PLAN_READY | CARD_SAVED | CARD_UPDATED |
        ROUTE_SHOWN | CURRENT_INCREMENT_READY | BLOCKED_NEEDS_PLAN |
        BLOCKED_NEEDS_OWNER | EVIDENCE_GAP | FAIL_CLOSED | NO_GO
MODE: READ_ONLY | GO
EVOLUTION_LINK: LINKED | STANDALONE | LEGACY_UNLINKED |
                CANDIDATE | NOT_APPLICABLE

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OVERLAP_CANDIDATES:
STAR_ROUTE:
CHANGE_CANDIDATES: (N items; omit only pure MAP_SHOWN)
RECOMMENDED: <exactly one Change title; omit only pure MAP_SHOWN>
DEPENDS_ON:
DEPENDS_ON_WARN:
VALUE_CHAIN:
ARTIFACT_CONTEXT:
WORKLOG_CONTEXT: (secondary; omit only pure MAP_SHOWN or missing+noted)
EXISTING_CHANGE_COLLISION: (when applicable; else omit or none)
RENAME_HINT: (when triggered; else omit or none)
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

On `CARD_SAVED` / `CARD_UPDATED` without Owner pick yet: emit `STAR_ROUTE` +
`CHANGE_CANDIDATES` + `RECOMMENDED` + ask pick; `OWNER_DECISION_REQUIRED: yes`;
do **not** treat `/opsx-ff` as the default exit.
On `ROUTE_SHOWN` / after pick: chat `ARTIFACT_CONTEXT` + when applicable
`EXISTING_CHANGE_COLLISION` (+ `RENAME_HINT` when triggered) + fenced
`COPY_BLOCK`; soft exit / `NEXT_ACTION` follow collision rules (DRIFTED|UNKNOWN
→ lead `/opsx-update`; SAME → ff|new|update OK).
On `MAP_SHOWN`, include star DAG sketch + `STAR_ROUTE` + soft warns when
relevant; `CHANGE_CANDIDATES` optional until advice/handoff; artifact study
optional until advice/handoff.

## Failure and recovery

- ambiguous overlap → `BLOCKED_NEEDS_OWNER`, at most three candidates;
- missing/malformed registry → `EVIDENCE_GAP` with exact path;
- increment advice/handoff without `ARTIFACT_CONTEXT` study → `EVIDENCE_GAP`
  (do not invent KEEP from card prose alone);
- `GO` without current plan → `BLOCKED_NEEDS_PLAN`;
- accepted decision conflict → `NO_GO`, do not rewrite the card as a workaround;
- `DEPENDS_ON` cycle or missing parent id on write → `NO_GO` until edges fixed;
- unmet `DEPENDS_ON` parents (soft) → `DEPENDS_ON_WARN` only; continue allowed;
- card saved but next increment / Change not picked → `ROUTE_SHOWN` /
  `OWNER_DECISION_REQUIRED: yes` with `CHANGE_CANDIDATES` + `RECOMMENDED`;
  do not recommend `/opsx-ff` yet;
- non-independent Current Increment / multi-intent Change → remain
  `PLAN_READY` or re-emit split candidates; ask one scope-boundary question
  only when N candidates cannot be formed yet;
- Future Increments in downstream owed scope → `/opsx-update`, or
  `/opsx-bound-scope` when explicit parking is required.

## Guardrails

- Never require linking for every change.
- Never migrate legacy changes automatically.
- Never store cards in `WORKLOG.md`.
- Never treat `DOTO/WORKLOG.md` as North Star registry, Current Increment DoD,
  or paste SoT; peek as secondary raw notes only.
- Never omit the WORKLOG peek (`WORKLOG_CONTEXT`) on draft / advice /
  `ROUTE_SHOWN` / pick-prep / handoff turns when the file exists (pure
  `MAP_SHOWN` may keep it lightweight or skip; missing file → continue, not
  fail).
- Never write, append, or rewrite `DOTO/WORKLOG.md` from this command
  (deferred parks: `/opsx-bound-scope:GO` only).
- Never auto-promote every WORKLOG line into `CURRENT_INCREMENT`,
  `CHANGE_CANDIDATES`, `FUTURE_INCREMENTS`, or `COPY_BLOCK`.
- Never promote an `EVOLUTION_CANDIDATE` without Owner `GO`.
- Never treat `EVOLUTION_PATH` as a promised backlog.
- Never add Future Increments to specs, acceptance, or tasks.
- Never create speculative frameworks under forward-compatibility language.
- Never merge similar cards without Owner choice.
- Never create or edit implementation code.
- Never hard-block `/opsx-new` / `/opsx-ff` on unmet `DEPENDS_ON` while mode is SOFT.
- Never put the star DAG into not-admin execution `GRAPH.md` as apply/verify states.
- Never allow cyclic `DEPENDS_ON` graphs.
- Never recommend `/opsx-ff` / `/opsx-new` / `/opsx-update` as the immediate
  post-star-save exit without `STAR_ROUTE` + `CHANGE_CANDIDATES` + one
  `RECOMMENDED` + Owner pick/confirm of next Change / `INCREMENT_ID` + a
  fenced `COPY_BLOCK`.
- Never omit `CHANGE_CANDIDATES` + exactly one `RECOMMENDED` on advice /
  `ROUTE_SHOWN` / pick-prep turns (pure `MAP_SHOWN` is the only skip).
- Never put `CHANGE_CANDIDATES` / `RECOMMENDED` **inside** COPY_BLOCK.
- Never put `WORKLOG_CONTEXT` / Worklog-derived dumps **inside** COPY_BLOCK.
- Never use diff size, file/module/task count, or specs/tasks/models count as
  the primary Change-boundary signal.
- Never mechanically split a human-natural single finished function into
  artificial cross-dependent Changes.
- Never auto-include an independent nearby capability into the main Change
  only because it sits next to in-scope code.
- Never put `/opsx-ff` / `/opsx-new` / `/opsx-update` **inside** COPY_BLOCK.
- Never put non-canonical bait sections inside COPY_BLOCK
  (`VALIDATION*`, `ALREADY_DELIVERED`, `GAP`, `DECISIONS` dumps, `STAR_ROUTE`,
  `CHANGE_CANDIDATES`, `RECOMMENDED`, `VALUE_CHAIN`, `ARTIFACT_CONTEXT`,
  `WORKLOG_CONTEXT`, `DEPENDS_ON*`, `EXISTING_CHANGE_COLLISION`, `RENAME_HINT`,
  deploy/devops “do now” prose); keep those chat-only.
- Never put outcome essays under `FUTURE_INCREMENTS` (ids only).
- Never omit COPY_BLOCK after OWNER_PICK when emitting CURRENT_INCREMENT_READY.
- Never omit `OWNER_INTENT` from COPY_BLOCK after OWNER_PICK.
- Never silently rewrite `OWNER_INTENT` from repository findings, agent
  inference, decomposition, or KEEP/HARD/FORWARD mapping; only Owner words or
  explicit Owner correction may set/change it.
- Never emit a thin/incomplete COPY_BLOCK that forces consumers to read the
  North Star card body for DoD (`OWNER_INTENT` / `IN_SCOPE` / `OUT_OF_SCOPE` /
  `FORWARD_COMPATIBILITY` / `KEEP` / `HARD` must be paste-sufficient).
- Never recommend `CARD_PATH` or other chat-only bait as paste into
  `/opsx-new` / `/opsx-ff` / `/opsx-continue` / change artifacts.
- Never omit `EXISTING_CHANGE_COLLISION` when `CHANGES_ACTIVE` hit is (or will
  be) `SUGGESTED_CHANGE` on a pick/handoff turn.
- Never list `/opsx-ff`|`/opsx-new` as the leading soft exit when
  `scope_compare` is `DRIFTED` or `UNKNOWN` (lead `/opsx-update`; ff/new only
  as `ALSO_OK` / Owner-explicit reject-reuse).
- Never omit `RENAME_HINT` when its trigger conditions fire (placeholder/stub
  slug vs non-stub KEEP, or DRIFTED with likely slug rename).
- Never recommend increment advice / COPY_BLOCK without bounded
  `ARTIFACT_CONTEXT` study (specs + active changes + archive when needed);
  pure `MAP_SHOWN` is the only skip.
- Never present `STAR_ROUTE` as mandatory DoD or an immutable backlog.
- Never require a durable on-disk handoff file; paste COPY_BLOCK is the cross-chat SoT.
