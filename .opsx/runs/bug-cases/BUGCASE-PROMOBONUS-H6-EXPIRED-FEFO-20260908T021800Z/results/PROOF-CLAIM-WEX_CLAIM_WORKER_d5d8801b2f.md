# Claim proof — WEX/CLAIM_WORKER/d5d8801b2f

## Worker

- WORKER_ID: CLAIM_WORKER
- WORKER_EXECUTION_ID: WEX/CLAIM_WORKER/d5d8801b2f
- ATTEMPT: 3
- CASE_ID: BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z
- FINDING_ID: ROOT-001
- CHAT_LABEL: SUP-PROMOBONUS-H6-FIX-20260908

## Input validation

- INPUT packet: `team/packets/WEX_CLAIM_WORKER_d5d8801b2f.in.json`
- FIRST_CLAIM_CANDIDATE: ROOT-001
- DO_NOT_CLAIM_HIGH6: true (honored — no HIGH6 finding in this case)
- DO_NOT_CLAIM_H2: true (honored — no H2 finding in this case)
- Only finding in case: ROOT-001 (`findings/ROOT-001.md`)

## Claim action

- Prior attempt 2 output existed but was rejected (`ATTEMPT_2_REJECT_REASON: host_role_play_no_real_Task_no_identity_json`).
- Finding packet already held durable claim fields from attempt 2; token reused (valid, same chat).
- LEDGER was stale (`STATUS=available`); synced to `claimed` on this hop.

## Evidence after write

| Artifact | Field | Value |
|---|---|---|
| findings/ROOT-001.md | STATUS | claimed |
| findings/ROOT-001.md | OWNER_CHAT | SUP-PROMOBONUS-H6-FIX-20260908 |
| findings/ROOT-001.md | CLAIM_TOKEN | CLAIM/BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z/ROOT-001/2026-09-08T02:45:00Z |
| findings/ROOT-001.md | CLAIMED_AT | 2026-09-08T02:45:00Z |
| LEDGER.md | ACTIVE_FINDING_ID | ROOT-001 |
| LEDGER.md | ROOT-001 STATUS | claimed |
| LEDGER.md | CLAIMED_NOT_COMPLETED | 1 |
| CASE.md | ACTIVE_FINDING_ID | ROOT-001 (pre-existing) |

## Boundaries

- No production edits
- No classification
- No tests or fix
- Single active claim: ROOT-001 only

## Result

STATUS: PASS
