# Evolution / North Star Policy

This policy defines how long-term product direction is connected to bounded
OpenSpec changes without turning a roadmap into the current change's DoD.

## Core invariant

```text
North Star                    = long-term direction
Evolution Path                = ordered, revisable increment hypotheses
Current Increment             = the only scope owed by the linked change
Contribution to North Star    = explicit causal claim for why this increment advances the direction
Forward Compatibility        = constraints for avoiding a dead-end design
Future Increments             = context only, never current tasks or acceptance
```

Passing an `EVOLUTION_HANDOFF` never authorizes implementation and never
bypasses proposal, design, apply, verify, archive, architecture-decision, or
Owner GO gates.

## Authority and storage

- Durable cards live under `openspec/evolution/` in the selected planning home.
- `openspec/evolution/index.md` is the lookup index; cards are the semantic
  source of truth.
- `DOTO/WORKLOG.md` remains raw notes. It may reference `STAR_ID` and
  `INCREMENT_ID`, but it is not a North Star registry.
- `/opsx-evolution` owns creation and semantic revision of North Star cards.
- `/opsx-bound-scope:GO` may append deferred raw detail to WORKLOG and may emit
  a candidate-increment handoff, but must not silently rewrite a card.
- Linked change artifacts own the delivered contract for one increment.
  A card cannot override their specs, decisions, tasks, or verification result.
- Paste `COPY_BLOCK` / `EVOLUTION_HANDOFF` keys owned by
  `.cursor/commands/opsx-evolution.md` (TARGET OVERRIDE) are the cross-chat
  DoD SoT for consumers; this policy states invariants, not a second paste
  template.

## Optional linking and backward compatibility

Every change has one evolution-link state:

```text
LINKED          — an approved EVOLUTION_HANDOFF is present
STANDALONE      — Owner intentionally proceeds without a North Star
LEGACY_UNLINKED — change predates this policy; no migration required
CANDIDATE       — capability-sized intent may match a card; lookup recommended
NOT_APPLICABLE  — local bugfix/refactor/maintenance with no useful evolution link
```

`STAR_ID` is optional. Absence never blocks legacy changes. A new
capability-sized change without a link receives a bounded overlap warning, not
an automatic hard stop. Only an explicit Owner policy may make linking
mandatory later.

## Human-native lookup

The human is not required to know `STAR_ID` or operation modes. Commands display
`Title (STAR_ID)` and accept a natural-language goal or title.

Before creating or updating a card:

1. Read the index first.
2. Match title/aliases, capability scope, domains, and linked changes.
3. Read at most three strongest candidate cards unless an `EVIDENCE_GAP`
   justifies a bounded expansion.
4. Show `OVERLAP_CANDIDATES`.
5. Let Owner choose: reuse, relate, or create separately.

Similarity is evidence for a question, never permission to merge cards.

## Star dependency DAG

Stars may declare unidirectional `DEPENDS_ON` edges (no cycles). Unmet parents
default to soft `DEPENDS_ON_WARN` — they do not hard-block `/opsx-new` or
`/opsx-ff` while mode is SOFT.

## Consumer obligations

When an approved handoff is supplied:

- `/opsx-new` links the scaffold but does not create artifacts.
- `/opsx-ff` and `/opsx-continue` carry the Evolution Context into artifacts.
- Every linked consumer preserves `CONTRIBUTION_TO_NORTH_STAR`; a missing or
  unrelated contribution is not inferred from `STAR_ID`.
- `/opsx-update` narrows/reconciles an existing change to the handoff.
- `/opsx-apply` implements only `IN_SCOPE`.
- `/opsx-verify` audits only Current Increment requirements and treats accidental
  Future Increment implementation as scope drift, not as extra credit.
- `/opsx-bound-scope` preserves `STAR_ID`/`INCREMENT_ID` in its handoff and raw
  deferred notes.

Consumers must not silently broaden `CURRENT_INCREMENT`, move
`FUTURE_INCREMENTS` into tasks, or reinterpret a card as implementation GO.
Canonical paste keys live in `/opsx-evolution` COPY_BLOCK (including mandatory
`OWNER_INTENT` — Owner product meaning). Consumers MUST NOT re-open the North
Star card body to invent Future scope, and MUST NOT rewrite `OWNER_INTENT`
from repository inference or explore findings without explicit Owner
correction. `/opsx-explore` may add evidence/mapping alongside a handoff but
must pass `OWNER_INTENT` through unchanged.

## NORTH_STAR_ALIGNMENT contract

`/opsx-apply` emits this receipt before linked code edits.
`/opsx-verify` independently emits it before archive:

```text
NORTH_STAR_ALIGNMENT:
EVOLUTION_LINK: LINKED | STANDALONE | LEGACY_UNLINKED | NOT_APPLICABLE
STAR_LINK_VALID: yes | no | not_applicable
INCREMENT_MATCH: yes | no | not_applicable
CONTRIBUTION_STATUS: supported | weak | none | not_applicable
CONTRIBUTION_EVIDENCE: <artifact/runtime evidence or not_applicable>
SCOPE_CONFORMANCE: pass | drift | not_applicable
FORWARD_COMPATIBILITY: pass | violated | unknown | not_applicable
FUTURE_SCOPE_LEAK: none | found | not_applicable
VERDICT: PASS | WARN | FAIL | NOT_APPLICABLE
RATIONALE: <concise evidence-based reason>
```

Hard `FAIL` for linked changes:

- card/increment is missing or superseded;
- Current Increment does not match handoff/artifacts;
- `CONTRIBUTION_STATUS=none`;
- `SCOPE_CONFORMANCE=drift`;
- `FORWARD_COMPATIBILITY=violated`;
- `FUTURE_SCOPE_LEAK=found`.

Before apply, `unknown` may be `WARN` when the evidence can exist only after
implementation. Missing source evidence needed to understand the linked
constraint is an `EVIDENCE_GAP` and blocks code edits. During verify, `unknown`
for an explicit mandatory constraint is `FAIL` / archive `NO_GO`.

`WARN` covers weak contribution evidence, a stale Evolution Path, newly
discovered future hypotheses, implementation-dependent Forward Compatibility
evidence before code exists, or incomplete non-mandatory evidence. `WARN` does
not block archive by itself. Future Increments are never audited as owed DoD.
Standalone, legacy-unlinked, and not-applicable changes produce
`NOT_APPLICABLE`, never a synthetic failure.

## Explore boundary

`/opsx-explore` may read cards, surface likely overlaps, and emit an
`EVOLUTION_CANDIDATE`. It remains exploratory and must not create/update cards.
When the direction is mature enough to persist, hand off to `/opsx-evolution`.
