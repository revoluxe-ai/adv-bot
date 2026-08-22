# Fixture 06 — clean current Owner Contract
(`auto-shelf-exhausted-pause-retest`)

## Live artifact

```text
openspec/changes/auto-shelf-exhausted-pause-retest/owner-contract.md
```

## PASS precondition (durable provenance)

`PASS` is allowed **only when** all material `## Решения Owner` bullets and
key acceptance constraints have durable sources (EVOLUTION_HANDOFF /
EXPLORE_HANDOFF / Owner correction paste), including at least:

* resolve CPO (not always Max) for pause decision;
* per-tick recheck while pause block is held; clear only our block (no forced start);
* feature only when module «Управление ставкой в полках» is ON;
* calendar retest waits full interval; «Сбросить паузу» clears our block early;
  clear ≠ force Auto start if other blocks remain;
* remove mid-cycle cost pause when shelf module ON; exhausted-test pause is a
  separate reason;
* main-bid mode gate («Best plan» only) if present in contract — must have its
  own durable confirmation (bundled agent proposals do not count).

Terminology must unambiguously separate:

* Авто-РК / placement «в полках», vs
* module «Управление ставкой в полках»
  (optional gloss: `auto_shelf_bid_control_enabled`).

Internal consistency must hold: Auto start after clearing our block is allowed
only when no higher-priority blocks remain (not “always starts”).

## Expected when preconditions met

```text
INTENT_PRESERVATION: PASS
OWNER_DECISION_PROVENANCE: PASS
INTERNAL_CONSISTENCY: PASS
TERMINOLOGY: PASS
SCOPE_INTEGRITY: PASS
ACCEPTANCE_COHERENCE: PASS
STALE_ASSUMPTIONS: PASS
CONTRACT_VS_REALITY: PASS | NOT_CHECKED

VERDICT: PASS
```

## Expected when durable provenance missing

If a material decision exists only in prior chat history and is not available
as durable handoff/paste:

```text
OWNER_DECISION_PROVENANCE: NEEDS_OWNER
VERDICT: NEEDS_OWNER
```

Do **not** invent PASS from chat memory.
