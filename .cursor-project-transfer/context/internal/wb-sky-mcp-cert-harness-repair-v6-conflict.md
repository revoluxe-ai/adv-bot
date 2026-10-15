---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# Cert harness repair — V6 evidence conflict

## Decisions

| Question | Answer |
|----------|--------|
| COMPOSE_SELF_INVALIDATION | **YES** |
| V6_CONSUMPTION_EXPLAINED | **YES** |
| DURABLE_RESULT_RECEIPT_SUFFICIENT | **YES** (post-repair at `d2586c4ba`) |
| CERT_HARNESS_REPAIR_REQUIRED | **YES** (implemented) |

## Root causes

**Compose:** `tests/docker-compose.test.yml` used `.\tests\postgres-init` / `.\tests\clickhouse-config`. Compose resolves bind paths relative to the compose file directory (`tests/`), producing host paths under `tests/tests/…` and changing the untracked manifest before guard verify.

**V6 ledger:** Pre-repair guard atomically wrote `{auth_id}.json` (`AUTHORIZED_CONSUMED`) at claim without a mandatory paired `{auth_id}.run_result.json`. A consumed ledger therefore did not prove spawn, return code, or PASSED/FAILED — enabling conflict with chat prose (e.g. verify `BLOCKED_FINGERPRINT_MISMATCH` / `NOT_RUN` while ledger shows CONSUMED).

## Repair (commit `d2586c4ba`)

- Compose volumes: `./postgres-init`, `./clickhouse-config`
- Guard: `persist_provider_run_result`, verify `CERTIFICATION_EVIDENCE_CONFLICT` when ledger exists without receipt (checked before `AUTH_CONSUMED`)
- Tests: +3 unit tests in `test_opsx_provider_run_guard.py`
- README: run-result receipt documented

V5/V6 ledgers untouched. V7 **not** issued (per owner stop).

## Gates

- pytest unit guard: 29 passed
- ruff: pass
- pyright-strict (guard module): 0 errors
- openspec CLI: not in Poetry env (BLOCKED_EXTERNAL for validate)
- Full `/opsx-verify`: not executed this turn
