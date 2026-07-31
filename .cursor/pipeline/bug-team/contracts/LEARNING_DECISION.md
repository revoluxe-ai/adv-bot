# LEARNING_DECISION contract (mandatory terminal learning)

```text
ARTIFACT: LEARNING_DECISION.json
CANONICAL_LOCATIONS (exactly one per case):
  family/LEARNING_DECISION.json     # when family/ exists
  results/LEARNING_DECISION.json    # episode-only compatibility
```

## Purpose

Mandatory compact learning decision between fan-in readiness and closure.
Absence of this artifact forbids closure.

Full `LEARNING_PACKET.json` is **conditional** (see FULL_PACKET_REQUIRED).

## Minimum schema

```text
LEARNING_DECISION_ID
CASE_ID
BUG_FAMILY_ID          # nullable for episode-only
INVARIANT_ID           # nullable when N/A

LEARNING_STAGE_INVOKED   # must be true
LEARNING_VERDICT

POLICY_ALREADY_EXISTS    # bool | null
POLICY_REFS              # list
ENFORCEMENT_GAP          # none | candidate | confirmed | null

PROMOTION_DECISION       # NONE | DEFERRED | RESOLVED_NO_PROMOTE | QUEUED

RECOMMENDATIONS:
  STATIC_CHECK_CANDIDATE      # bool
  PROJECT_WIDE_HUNT_REQUEST   # bool
  TESTING_RULES_CANDIDATE     # bool

FULL_PACKET_REQUIRED     # bool
FULL_PACKET_PATH         # path or null

SOURCE_FANIN_PATH
SOURCE_FANIN_HASH
SOURCE_ARTIFACT_PATHS
SOURCE_ARTIFACT_HASHES

LEARNING_STATUS          # COMPLETE | BLOCKED | OWNER_WAIT
DECISION_RATIONALE

CREATED_AT
DECISION_HASH

# optional corrective metadata
PRODUCT_CLOSURE_VALID
PROCESS_METADATA_CORRECTED
LEARNING_DECISION_VALIDATED   # set by validator, not author
```

## LEARNING_VERDICT enum

```text
NO_REUSABLE_LESSON
LOCAL_CASE_NOTE_ONLY
EXISTING_POLICY_COMPLIANCE_FAILURE
COMPLIANCE_ENFORCEMENT_CANDIDATE
CLASS_LESSON_CANDIDATE
SUPERCLASS_SEED_EVIDENCE
OWNER_DECISION_REQUIRED
LEARNING_BLOCKED
```

## Closure-allowed verdicts

```text
NO_REUSABLE_LESSON
LOCAL_CASE_NOTE_ONLY
EXISTING_POLICY_COMPLIANCE_FAILURE
COMPLIANCE_ENFORCEMENT_CANDIDATE   # + PROMOTION_DECISION ∈ {DEFERRED,RESOLVED_NO_PROMOTE,QUEUED}
CLASS_LESSON_CANDIDATE             # + same
SUPERCLASS_SEED_EVIDENCE           # + same; must not activate superclass
```

For packet-free verdicts (`NO_REUSABLE_LESSON`, `LOCAL_CASE_NOTE_ONLY`,
`EXISTING_POLICY_COMPLIANCE_FAILURE`) a validated decision alone is enough.

For candidate verdicts, `FULL_PACKET_REQUIRED=true` and a valid packet path
must exist.

## Closure-blocking verdicts

```text
OWNER_DECISION_REQUIRED
LEARNING_BLOCKED
```

## Rejection statuses (CLOSURE_OPERATOR / close_family)

```text
BLOCKED_LEARNING_DECISION_MISSING
BLOCKED_LEARNING_DECISION_INVALID
BLOCKED_LEARNING_INCOMPLETE
BLOCKED_OWNER_LEARNING_DECISION_REQUIRED
```

## Promotion boundary

Learning may record verdict, recommendations, materialize a candidate packet,
queue or defer promotion. Learning must **not** activate global OPSX rules,
class lessons, superclasses, project-wide remediation, or rewrite testing rules.

Promotion remains separate (`/opsx-admin-command-promote-process-lesson` or
Owner-authorized class/superclass path).

## Live terminal path

```text
FAN_IN_ASSEMBLER → FAMILY_LEARNING_WORKER → CLOSURE_OPERATOR
```
