# RAW_INTAKE packet

```text
SCHEMA: opsx-bug-team/RAW_INTAKE
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Authoritative source (verbatim)

```text
RAW_INTAKE_TEXT                 # never rewrite / paraphrase here
RAW_INTAKE_SOURCE:
  USER_MESSAGE
  | CURRENT_CHAT_CONTEXT
  | FILE
  | LOG
  | SCREENSHOT_REFERENCE
  | EXISTING_ARTIFACT
RAW_INTAKE_RECEIVED_AT
RAW_INTAKE_HASH                 # SHA-256 of RAW_INTAKE_TEXT (utf-8)
```

## Normalized layer (Materializer)

```text
OBSERVED_BEHAVIOR
EXPECTED_BEHAVIOR_CANDIDATE     # not normative until evidence
AFFECTED_AREA_CANDIDATE
REPRODUCTION_INFORMATION
EVIDENCE_REFERENCES
INFERRED_ASSUMPTIONS
UNRESOLVED_QUESTIONS
```

## Sufficiency

```text
INTAKE_SUFFICIENCY:
  SUFFICIENT_FOR_CLASSIFICATION
  | SUFFICIENT_FOR_MATERIALIZATION_ONLY
  | INSUFFICIENT
```

`SUFFICIENT_FOR_MATERIALIZATION_ONLY` may create case/finding; CLASSIFIER
may still return `INSUFFICIENT_EVIDENCE`.

## Duplicate outcomes

```text
NEW_CASE_CREATED
EXISTING_CASE_LINKED
DUPLICATE_ROOT_REJECTED
LEGACY_CASE_RESUME_REQUIRED
```

## Accepted free-form shapes

short description; long narrative; log/traceback; file path; failing test
name; case/artifact link; expected vs actual; screenshot reference;
mixed RU/EN technical text.
