# BRANCH_REGISTRY schema definition

This file is the **schema**. The only runtime instance is:

```text
.opsx/runs/bug-cases/<ROOT_CASE_ID>/LEDGER.md
  ## BRANCH_REGISTRY
```

Do not create `BRANCH_REGISTRY.md` inside the case map.

## Row fields

```text
FINDING_ID
PARENT_FINDING_ID | ROOT
DEPTH
EPISODE_TERMINAL          # parallel to claim STATUS; see TERMINAL_STATUS_MAP.md
OWNER
CHAT_REQUIRED
CLAIM_STATUS              # existing durable STATUS; unchanged by this schema
TEST_ID?
RED_EVIDENCE_PATH?
GREEN_EVIDENCE_PATH?
OWNER_PRODUCTION_GO: yes | no | n/a
OWNER_GO_RECEIPT_PATH?
FIX_EVIDENCE_PATH?
PRODUCTION_PATHS?
NOTES
```

## Episode counters (LEDGER summary / BRANCH_REGISTRY header)

```text
HUNT_PASSES_EXECUTED
MAX_DEPTH_SEEN
ACTIVE_BRANCH_COUNT
MAX_HUNT_PASSES: 3
MAX_DEPTH_FROM_ROOT: 3
MAX_ACTIVE_BRANCHES: 3
```

## Started branch

A branch is **started** when it has a BRANCH_REGISTRY row with a working
or terminal episode path (claimable child, root under fix, or already
terminal). Fan-in requires every started branch to have
`EPISODE_TERMINAL` set.
