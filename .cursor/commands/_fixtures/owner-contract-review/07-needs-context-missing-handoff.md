# Fixture 07 — T1 missing durable OWNER_INTENT source

## Given

```text
change=auto-shelf-exhausted-pause-retest
owner-contract.md: present
EVOLUTION_HANDOFF: not provided
EXPLORE_HANDOFF: not provided
No other durable OWNER_INTENT source available
```

## Expected

```text
REVIEW_STATE: NEEDS_CONTEXT
VERDICT: NEEDS_CONTEXT

Human asks for the concrete missing source (e.g. paste EVOLUTION_HANDOFF entirely).
must NOT be FAIL
must NOT dump a full findings list requiring Owner to invent recovery
MODE: READ_ONLY
FILES_CHANGED: none
```

## Why

Missing provenance context is a recoverable dialog state, not a contract FAIL.
