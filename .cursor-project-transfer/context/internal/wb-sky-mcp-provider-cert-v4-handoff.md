---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# READY_FOR_HOME_PC_PROVIDER_CERT_V4

PR [#452](https://github.com/revoluxe-ai/adv-bot/pull/452) · change `wb-sky-mcp-read-interface`

## Status block

| Field | Value |
|-------|-------|
| **FINAL_STATUS** | `READY_FOR_HOME_PC_PROVIDER_CERT_V4` |
| **OLD_HEAD** | `73716172b093d0d1198ceb9ecc7fa3f29b3bdcd5` |
| **NEW_HEAD** | `44e5e646b6f02243bae00d5b6476cdd310dae5f1` |
| **ORIGIN_STAGE_CURRENT** | `6b62da98df322d6fd1bdf6c4f838c0b792964d33` |
| **MERGE_TREE** | CLEAN vs `origin/stage` |
| **REBASE_REQUIRED** | NO (merge commit integrated stage) |
| **V3_STATUS** | `SUPERSEDED_UNUSED` |
| **V3_PROVIDER_EXECUTED** | NO |
| **PROVIDER_RUN_EXECUTED_IN_CLOUD** | NO |

### Blocker repairs

| Item | Implementation |
|------|----------------|
| **ATOMIC_ONE_SHOT_IMPLEMENTATION** | `try_claim_one_shot_authorization()` uses `os.open(..., O_CREAT\|O_EXCL\|O_WRONLY)` on `.opsx/runs/scenario-coverage/<change_id>/authorizations/<one_shot_authorization_id>.json`; corrupt JSON → `EXPIRED_OR_INVALID`; claim never rolled back. |
| **CONCURRENT_CONTENDERS_TEST** | `test_concurrent_one_shot_claim_exactly_one_winner`, `test_concurrent_run_guarded_exactly_one_provider_spawn` (ProcessPoolExecutor, 2 workers). |
| **TOTAL_PROVIDER_SPAWNS_EXPECTED** | 1 |
| **SEALED_ARGV_BINDING** | `canonical_pytest_argv_sha256` on packet + `# CANONICAL_PYTEST_ARGV_SHA256` in block; verify rejects argv/block drift. |
| **UNGUARDED_PROVIDER_PATHS** | Heuristic ban on `pytest` / `py.test` / `python -m pytest` / `poetry run pytest` on non-comment lines; regression `test_pytest_smuggled_on_guard_line_rejected`. |
| **GUARD_RESULT_MODEL** | Preserved: `guard_permission`, `provider_result`, `provider_spawned`, `authorization_state`, exit codes 0/3/4/5/6. |

### Gates (Cloud)

| Gate | Result |
|------|--------|
| UNIT_TESTS (opsx + wb_sky_mcp + alembic head) | PASS (64) |
| CONCURRENCY_TESTS | PASS |
| MCP_TESTS (unit) | PASS |
| ALEMBIC | PASS (single head `010e7ee6eac0`) |
| RUFF (guard paths) | PASS |
| PYRIGHT_STRICT | PASS |
| PYRIGHT_DEFAULT | not re-run full repo (strict gate green) |
| OPENSPEC_STRICT | `poetry run check-openspec` config contract PASS; `openspec validate` CLI unavailable in Cloud VM |
| OPSX_VERIFY | not automated (no `openspec` binary); scenario plan unchanged on branch |
| DIFF_CHECK | PASS |

### v4 authorization (unused — Home PC only)

| Field | Value |
|-------|-------|
| **V4_PACKET_ID** | `PROVIDER-PACKET-v4` |
| **V4_AUDITED_HEAD** | `44e5e646b6f02243bae00d5b6476cdd310dae5f1` |
| **V4_RUN_SPEC_HASH** | `7b78f9d4d5f0bac4216a8d98b55c6a496cfc5630902a0f4910712faa364077a5` |
| **V4_AUTHORIZATION_ID** | `13f24750155269a910cfe2cd2b7d20b2d42f52ee25c050815ab052a284d246f2` |
| **V4_AUTH_STATE** | `AUTHORIZED_UNUSED` |

**`AUTHORIZE_ONE_LIVE_RUN` secret (one-time, do not commit):**

```
666ccad86428fbec024a5cc1f3cbe631424264dfe03277d69a852b6077b4e7dd
```

Cloud did **not** call `guard run` and did **not** write authorization ledger files.

### Independent review (Composer 2.5)

| Severity | Finding | Disposition |
|----------|---------|-------------|
| HIGH | Pytest smuggle via `opsx_provider_run_guard.py` line skip | **Fixed** + test |
| MEDIUM | Corrupt ledger JSON | **Fixed** (invalid → `EXPIRED_OR_INVALID`) |
| MEDIUM | Verify→claim fingerprint window | Accepted (inherent; documented) |
| LOW | `run_spec_sha256` not verified in guard | Open LOW |
| **INDEPENDENT_REVIEW_RESULT** | **APPROVE_WITH_LOW** after HIGH fix |

### Cloud preflight note

`opsx_provider_preflight.py` → **FAIL** on `docker` / `docker compose` (not installed on Cloud Agent). Expected `BLOCKED_EXTERNAL_FOR_PROVIDER_EXECUTION` here; Home PC must pass full preflight including Docker.

---

## HOME-PC sequence (exact)

Branch: `cursor/wb-sky-mcp-read-interface-127c`

```bash
git fetch origin cursor/wb-sky-mcp-read-interface-127c
git checkout cursor/wb-sky-mcp-read-interface-127c
test "$(git rev-parse HEAD)" = "44e5e646b6f02243bae00d5b6476cdd310dae5f1"

export AUTHORIZE_ONE_LIVE_RUN='666ccad86428fbec024a5cc1f3cbe631424264dfe03277d69a852b6077b4e7dd'

poetry run python .opsx/tools/opsx_provider_preflight.py --repo .

poetry run python .opsx/tools/opsx_seal_provider_packet.py \
  --repo . \
  --change-id wb-sky-mcp-read-interface \
  --live-token "$AUTHORIZE_ONE_LIVE_RUN"

poetry run python .opsx/tools/opsx_provider_run_guard.py verify \
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json \
  --repo .

# Start disposable test stack (per sealed block), then:
poetry run python .opsx/tools/opsx_provider_run_guard.py run \
  --packet .opsx/runs/scenario-coverage/wb-sky-mcp-read-interface/provider-run-packet.json \
  --repo .
```

Run **once**. Second `run` must yield `BLOCKED_AUTHORIZATION` / `AUTH_CONSUMED`, `provider_spawned=false`, `spawn_count=0`.

After seal, do not modify tracked files before `guard run` (packet is gitignored; sealing updates untracked manifest only).
