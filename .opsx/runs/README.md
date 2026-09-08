# OPSX canonical run store (`.opsx/runs`)

## Purpose

Durable, repo-local store for OPSX **run artifacts** that must survive across
hops and may be git-tracked after Owner review. This is the single canonical
location (`ONE_CANONICAL_OPSX_RUN_STORE`) for durable OPSX run data.

## Durability and Git policy

- **Durable:** bug episodes, bootstrap merge receipts, inbound packets,
  scenario-coverage receipts, distribute briefs.
- **Git:** intended to be tracked; `.opsx/sources.yaml` allowlist includes
  `.opsx/runs/**` for export/bind flows.
- **No dual-write:** writers MUST NOT mirror the same durable object under
  `.tmp/` and `.opsx/runs/`.

## Namespaces

| Namespace | Path | Notes |
|-----------|------|-------|
| bug-cases | `.opsx/runs/bug-cases/` | INDEX, CASE dirs, findings, results |
| bootstrap | `.opsx/runs/bootstrap/` | Durable `MERGE_RECEIPT.md` per UTC dir |
| inbound | `.opsx/runs/inbound/` | mkdir-on-write |
| scenario-coverage | `.opsx/runs/scenario-coverage/` | mkdir-on-write |
| distribute | `.opsx/runs/distribute/` | mkdir-on-write |

**Not here:** chat-audit stays `.tmp/opsx-chat-audit` (ephemeral).

**Export:** repo-root `opsx-export/` (gitignored), **not** under `.opsx/runs`.

## Difference from `.tmp`

`.tmp/` is **EPHEMERAL_ONLY** (gitignored): hop scratch, harness sandboxes,
bootstrap DIFF packets (`BOOTSTRAP_DIFF_PACKET.md`), staging (`_staging`),
chat-audit. Never use `.tmp` as the durable SoT for the namespaces above.

## Hop-scratch exclusion

Files matching `team/packets/_*.py` and `team/packets/_*.json` under bug-case
trees are hop-scratch — leave untracked; do not blanket-gitignore `*.py` here.

## Identity preservation

`CASE_ID`, `FINDING_ID`, `WEX` ids, and content hashes in historical artifacts
are preserved verbatim during migration; only **live recovery path strings**
point at `.opsx/runs/...`.
