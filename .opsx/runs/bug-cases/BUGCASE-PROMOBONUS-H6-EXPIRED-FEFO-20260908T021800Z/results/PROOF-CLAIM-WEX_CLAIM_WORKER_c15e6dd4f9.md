# Claim proof — WEX/CLAIM_WORKER/c15e6dd4f9

## Worker

- WORKER_ID: CLAIM_WORKER
- WORKER_EXECUTION_ID: WEX/CLAIM_WORKER/c15e6dd4f9
- ATTEMPT: 3
- MODEL: composer-2.5 (explicit)
- CASE_ID: BUGCASE-PROMOBONUS-H6-EXPIRED-FEFO-20260908T021800Z
- FINDING_ID: ROOT-001
- CHAT_LABEL: SUP-PROMOBONUS-H6-FIX-20260908

## Input validation

- INPUT packet: `team/packets/WEX_CLAIM_WORKER_c15e6dd4f9.in.json`
- FIRST_CLAIM_CANDIDATE: ROOT-001
- DO_NOT_CLAIM_HIGH6: true (honored — no HIGH6 finding in this case)
- DO_NOT_CLAIM_H2: true (honored — no H2 finding in this case)
- Only finding in case: ROOT-001 (`findings/ROOT-001.md`)

## Prior attempt context

- WEX/CLAIM_WORKER/d5d8801b2f (fast model) was CANCELLED (OWNER_ABORTED_FAST_MODEL).
- Its output was rejected: `MISSING_REQUIRED_FIELD: EXPIRES_AT`.
- This hop is the authoritative composer-2.5 claim for attempt 3.

## Claim action

- Durable CLAIM_TOKEN reused (same finding, same chat, token still valid).
- LEDGER and finding packet synced: STATUS=claimed, ACTIVE_FINDING_ID=ROOT-001.
- LAST_ACTIVITY_AT refreshed to 2026-09-08T03:00:00Z.

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

## Boundaries

- No production edits
- No classification
- No tests or fix
- Single active claim: ROOT-001 only
- HIGH6 and H2 not claimed

## Result

STATUS: PASS
