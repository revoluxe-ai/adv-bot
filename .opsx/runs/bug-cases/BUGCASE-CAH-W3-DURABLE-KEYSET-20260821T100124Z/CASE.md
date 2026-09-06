# CASE: BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z

CASE_ID: BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z
PRIMARY_INTAKE_ID: INTAKE-001
ROOT_FINDING_ID: ROOT-001
SOURCE_TYPE: manual
SOURCE_REFERENCE: USER_MESSAGE / WEX/MATERIALIZER/56bd3ed61c
PARENT_CASE_ID:
SOURCE_FINDING_ID:
ANCESTOR_CHAIN: [BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z]
DEPTH: 0
STATUS: adjudicating
CURRENT_STAGE: adjudication_pending
NEXT_ACTION: /opsx-classify-bug case=BUGCASE-CAH-W3-DURABLE-KEYSET-20260821T100124Z finding=ROOT-001
PROPOSED_INVARIANT:
ROOT_FINGERPRINT:
CREATED_AT: 2026-08-21T10:01:24.329377+00:00
UPDATED_AT: 2026-08-21T10:10:00+00:00
LAST_COMMAND: /opsx-materialize-bug-queue mode=intake create_root_finding=true

## Summary

Raw intake text preserved verbatim: «Да, в таком случае убирать ключ нельзя».
The supplied W3 context records a concern that a partial live factual-position
response can cause a subset to be persisted and remove a previously confirmed
durable keyword. The materializer recorded this as a root finding for later
classification and did not assert a production classification, invariant, root
cause, or fix.

## Duplicate search

DUPLICATE_SEARCH_ROOT: .opsx/runs/bug-cases
DUPLICATE_OUTCOME: NEW_CASE_CREATED
NOTES: The only prior case found under the search root was
BUGCASE-CAH-EXIT-FAIL-OPEN-20260821T075030Z, whose recorded scope concerns
missing Telegram actor identity on the EXIT path. No prior case or finding
matched the durable confirmed-keyword retention signal in this intake.

## Materializer boundaries

PRODUCTION_CLASSIFICATION_SET: false
FIX_PROPOSED: false
ROOT_FINGERPRINT_SET: false
NEXT_WORKER: CLASSIFIER
