---
name: /opsx-evolution
id: opsx-evolution
category: Workflow
description: "Human-native North Star registry: find or formalize a direction and hand off one bounded increment."
argument-hint: "[natural-language goal | title | star=<id>] [GO]"
---

# /opsx-evolution

Human-native front door for durable product evolution:

```text
idea → existing/new North Star → Evolution Path → one Current Increment
     → /opsx-new | /opsx-ff | /opsx-update
```

The human does not need to know modes or `STAR_ID`:

```text
/opsx-evolution
/opsx-evolution Хочу организовать постоянный сбор WB-данных
/opsx-evolution Безопасный сбор WB-данных
```

The command infers whether to show the map, inspect an existing direction, or
draft a new/revised direction. Internal operation labels may appear in receipts,
but are not required user syntax.

## Core boundary

Read and follow `openspec/policies/EVOLUTION_POLICY.md`.

```text
North Star         = long-term direction
Evolution Path     = revisable increment hypotheses
Current Increment  = only scope owed by the next/current change
Future Increments  = context only, never current DoD
```

This command never creates an OpenSpec change, edits product code, implements a
task, verifies a change, or archives it.

## Store and source resolution

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md`.

If a standalone OpenSpec store is named, run `openspec store list --json`,
resolve its planning home, and use that store's `evolution/` registry. Otherwise
use the nearest local OpenSpec planning home.

Canonical local paths:

```text
openspec/evolution/index.md
openspec/evolution/<star-slug>.md
openspec/evolution/_template/north-star.md
```

Read the index first. Resolve exact card paths from it. Do not recursively dump
all cards. For overlap lookup, read at most three strongest candidates unless
an explicit `EVIDENCE_GAP` justifies bounded expansion.

## Relationship to other commands

| Need | Owner |
|---|---|
| Think freely, inspect code, compare options | `/opsx-explore` |
| Persist/find/revise a North Star and choose one increment | this command |
| Create a step-by-step change | `/opsx-new` |
| Create an apply-ready change | `/opsx-ff` |
| Reconcile an existing change | `/opsx-update` |
| Cut an already oversized change | `/opsx-bound-scope` |

`/opsx-explore` may emit an `EVOLUTION_CANDIDATE`; it never writes cards.
This command may consume that candidate, validate it against the registry, and
produce an approved `EVOLUTION_HANDOFF`.

## Human-native operation inference

Do not ask the human to select a mode when intent is clear.

```text
no goal / "что есть?"       → show active North Star map (READ_ONLY)
natural-language goal       → overlap lookup + draft (READ_ONLY)
exact title / star=<id>     → status + next-increment draft (READ_ONLY)
GO                          → persist the last still-current accepted draft
```

If `GO` is supplied without a current draft in this conversation, stop with
`BLOCKED_NEEDS_PLAN`; reconstructing approval from old chat is forbidden.

## Applicability

Classify the requested work:

```text
LINKED          — approved card/increment selected
STANDALONE      — Owner intentionally wants an unlinked change
LEGACY_UNLINKED — existing change predates this policy
CANDIDATE       — capability-sized work likely benefits from a card
NOT_APPLICABLE  — local bugfix/refactor/maintenance
```

North Star linking is optional. Do not force a card for local fixes or legacy
changes. When capability-sized work appears unlinked, show a recommendation and
overlap candidates; do not hard-block `/opsx-new` or `/opsx-ff`.

## READ_ONLY plan flow

1. Resolve the selected planning home and read:
   - `openspec/policies/EVOLUTION_POLICY.md`;
   - `evolution/index.md`;
   - an exact selected card or at most three overlap candidates.
2. Search overlap using:
   - human title and aliases;
   - capability scope and domains;
   - linked active/archived changes;
   - similar Current/Future Increment outcomes.
3. Print candidates as `Title (STAR_ID)` with one-line overlap reasons.
4. If multiple plausible cards exist, ask one Owner question:

```text
Использовать существующую | связать направления | создать отдельную?
```

5. Build or revise:
   - `NORTH_STAR`;
   - `EVOLUTION_PATH`;
   - exactly one `CURRENT_INCREMENT`;
   - one explicit `CONTRIBUTION_TO_NORTH_STAR` explaining why that increment
     advances the selected direction;
   - `FORWARD_COMPATIBILITY_CONSTRAINTS`;
   - `OUT_OF_SCOPE`;
   - `FUTURE_INCREMENTS`.
6. Check that Current Increment is independently verifiable and does not
   include every future wish.
7. Show the exact write plan and stop for GO.

Similarity never authorizes an automatic merge. Missing evidence about a
material overlap returns `EVIDENCE_GAP`, not a guessed new card.

## GO flow

Exact `GO`, or an explicit request to persist the displayed current draft,
authorizes only the disclosed card/index writes.

1. Recheck that the accepted draft is still current.
2. For a new card:
   - derive a stable kebab-case `STAR_ID`;
   - create `evolution/<star-slug>.md` from the template;
   - add one entry to `evolution/index.md`.
3. For an existing card:
   - preserve `STAR_ID`;
   - update semantic sections only;
   - append a concise History entry;
   - never rewrite delivered change evidence as a hypothesis.
4. Emit one `EVOLUTION_HANDOFF`.
5. Recommend exactly one next command based on Owner intent:
   - `/opsx-new` for step-by-step artifacts;
   - `/opsx-ff` for apply-ready artifact generation;
   - `/opsx-update` for an existing change.
6. Do not invoke the downstream command automatically.

## Card requirements

Every durable card contains:

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

Each increment has a stable `INCREMENT_ID`, human title, outcome, status, and
linked changes/evidence when known. Candidate increments are not tasks.

## EVOLUTION_HANDOFF

```text
EVOLUTION_HANDOFF:
STATUS: CURRENT_INCREMENT_READY
EVOLUTION_LINK: LINKED
STAR_ID: <stable id>
STAR_TITLE: <human title>
CARD_PATH: <planning-home>/evolution/<slug>.md
NORTH_STAR: <long-term outcome>
INCREMENT_ID: <stable id>
CURRENT_INCREMENT: <one independently verifiable outcome>
CONTRIBUTION_TO_NORTH_STAR: <how this outcome advances the North Star>
IN_SCOPE:
- <owed unit>
FORWARD_COMPATIBILITY_CONSTRAINTS:
- <constraint required now>
OUT_OF_SCOPE:
- <explicit exclusion>
FUTURE_INCREMENTS:
- <context only; not owed DoD>
RECOMMENDED_NEXT: /opsx-new | /opsx-ff | /opsx-update
```

The handoff constrains a linked change. It does not authorize implementation.

## Return contract

Every invocation returns:

```text
STATUS: MAP_SHOWN | PLAN_READY | CARD_SAVED | CARD_UPDATED |
        CURRENT_INCREMENT_READY | BLOCKED_NEEDS_PLAN |
        BLOCKED_NEEDS_OWNER | EVIDENCE_GAP
MODE: READ_ONLY | GO
EVOLUTION_LINK: LINKED | STANDALONE | LEGACY_UNLINKED |
                CANDIDATE | NOT_APPLICABLE

WHAT_HAPPENED:
WHY:
CURRENT_STATE:
OVERLAP_CANDIDATES:
OWNER_DECISION_REQUIRED: yes | no
NEXT_ACTION:
DO_NOT_DO_YET:
```

On `CARD_SAVED` / `CARD_UPDATED`, include `EVOLUTION_HANDOFF`.

## Failure and recovery

- Ambiguous overlap → `BLOCKED_NEEDS_OWNER`; show at most three human titles.
- Missing registry → `EVIDENCE_GAP`; point to the exact expected path.
- GO without a current plan → `BLOCKED_NEEDS_PLAN`.
- Existing card contradicts accepted architecture decisions → `NO_GO`; do not
  change the card as a workaround.
- Current Increment is not independently deliverable → remain `PLAN_READY` and
  ask one scope-boundary question.
- Downstream artifacts include Future Increments → route to `/opsx-update` or,
  when already oversized and parking is wanted, `/opsx-bound-scope`.

## Guardrails

- Never require North Star linking for every change.
- Never migrate legacy changes automatically.
- Never store North Star cards in WORKLOG.
- Never promote an `EVOLUTION_CANDIDATE` without Owner GO.
- Never treat `EVOLUTION_PATH` as a promised backlog.
- Never add Future Increments to current tasks/spec acceptance.
- Never create speculative frameworks under forward-compatibility language.
- Never merge similar cards without Owner choice.
- Never create or edit implementation code.

