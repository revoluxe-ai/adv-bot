# Worker: FAMILY_LEARNING_WORKER

```text
WORKER_ID: FAMILY_LEARNING_WORKER
ACTIVATION_STATUS: LIVE
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
CONTRACT: .cursor/pipeline/bug-team/contracts/LEARNING_DECISION.md
```

## Role

Mandatory learning stage after fan-in readiness and before
`CLOSURE_OPERATOR` / `close_family`.

Live terminal path:

```text
FAN_IN_ASSEMBLER → FAMILY_LEARNING_WORKER → CLOSURE_OPERATOR
```

## Required write

Always write exactly one canonical:

```text
family/LEARNING_DECISION.json          # when family/ exists
results/LEARNING_DECISION.json         # episode-only compatibility
```

`LEARNING_STAGE_INVOKED` must be `true`.
`LEARNING_STATUS` ∈ {`COMPLETE`, `BLOCKED`, `OWNER_WAIT`}.

## Conditional full packet

Write `family/LEARNING_PACKET.json` **only** when:

```text
LEARNING_VERDICT ∈ {
  COMPLIANCE_ENFORCEMENT_CANDIDATE,
  CLASS_LESSON_CANDIDATE,
  SUPERCLASS_SEED_EVIDENCE
}
```

For `NO_REUSABLE_LESSON` / `LOCAL_CASE_NOTE_ONLY` /
`EXISTING_POLICY_COMPLIANCE_FAILURE`, the validated decision alone is enough.

## Promotion boundary

May record verdict, recommendations, queue/defer promotion.
Must **not** activate global rules, class lessons, superclasses, static-check,
project hunt, or testing-rules mutation. Promotion is separate
(`/opsx-admin-command-promote-process-lesson`).

## Preconditions

Family path: fan-in `READY_FOR_FAMILY_CLOSURE` (BF-V9-003).
Episode path: `FANIN.md` `READY_FOR_CLOSURE` + `BLOCKING_FINDINGS=NONE`.
