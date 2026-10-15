---
cursor:
  subagentId: "bc-1334b977-28ff-5e36-8226-4f0b5f5822ef"
---

# WB Sky MCP — provider-run fail-closed repair

## OWNER template

```text
FEATURE: wb-sky-mcp-read-interface
PR: #452
BASE_HEAD: fb5410ad2815e3529d55058d729ac6ac27dc84b0
FINAL_HEAD: 5e3c08bfbbc990fefc6a71535283d1825e80bb72
ORIGIN_STAGE_CURRENT: d5f9306ad70438785f366284f2a8823ac8bac0d2

ROOT_CAUSE:
  Independent re-audit published ALLOWED_RUN_BLOCK_SHA256 metadata
  (dc15859a…) that did not match SHA-256 of the fenced ```bash block
  (canonical trailing-LF rule → 65529731…). Prior authorized provider
  path validated git audited-state hashes but did not hard-stop on run-block
  mismatch; ad-hoc shell invoked pytest anyway → AUTHORIZE_ONE_LIVE_RUN
  consumed with 6 setup ERROR (no Docker).

EXPECTED_HASH_SOURCE:
  INDEPENDENT_REAUDIT YAML field ALLOWED_RUN_BLOCK_SHA256 in
  internal/wb-sky-mcp-pg-independent-reaudit.md (was stale dc15859a…).

COMPUTED_HASH_SOURCE:
  SHA-256(utf8(fenced block) + optional single trailing LF) per
  opsx-close-external-gap B2; matches 65529731… for current fence text.

MISSING_ENFORCEMENT_POINT:
  No repo tool enforced ALLOWED_RUN_BLOCK_SHA256 before subprocess;
  close-external-gap contract is prompt-only for agents — live run used
  direct poetry pytest without guard CLI.

FILES_CHANGED:
  - .opsx/tools/opsx_provider_run_guard.py (new)
  - tests/unit/opsx/test_opsx_provider_run_guard.py (new)
  - .opsx/tools/README.md (guard usage)
  - internal/wb-sky-mcp-pg-independent-reaudit.md (ALLOWED_RUN_BLOCK_SHA256 → 65529731…)

REPAIR_SUMMARY:
  Added fail-closed guard: verify HEAD, three audited git hashes, frozen
  run-block SHA, pytest argv + PG host/port/dbname vs block, provider test
  path coverage — then optional single subprocess. Mismatch →
  BLOCKED_FINGERPRINT_MISMATCH, spawn_count=0. Corrected re-audit metadata
  hash to match fenced block.

FAIL_CLOSED_GUARD:
  SCRIPT: .opsx/tools/opsx_provider_run_guard.py
  EXIT_BLOCKED: 3 (stderr BLOCKED_FINGERPRINT_MISMATCH)
  UNIT_TESTS: 6 passed (mocked git compute injectors; no pytest spawn on reject)

MATCHING_PACKET_WOULD_EXECUTE:
  YES when packet matches worktree + block (use `run --dry-run` or injectors
  in tests); production path must call guard before pytest.

ACTUAL_PROVIDER_RUN_PERFORMED: NO

DOCKER_REQUIRED:
  YES — destructive_local integration conftest runs docker_preflight
  (setup_test_database). Full provider certify needs /opsx-test-env UP
  (test_db, test_clickhouse, test_redis @ 6390) on a host with Docker.

CURRENT_VM_DOCKER: UNAVAILABLE (docker: command not found, exit 127)

NEXT_VALID_PROVIDER_ENVIRONMENT:
  Laptop or cloud environment build with Docker + /opsx-test-env UP;
  REDIS_PORT=6390; fresh independent re-audit + new AUTHORIZE_ONE_LIVE_RUN;
  invoke: poetry run python .opsx/tools/opsx_provider_run_guard.py run \
    --packet <json> --repo .  (never raw pytest on mismatch)

TESTS:
  poetry run pytest tests/unit/opsx/test_opsx_provider_run_guard.py -v → PASS (6)

RUFF:
  poetry run ruff check .opsx/tools/opsx_provider_run_guard.py \
    tests/unit/opsx/test_opsx_provider_run_guard.py → PASS

PYRIGHT: not run (new tooling under .opsx/tools; not in strict app surface)

OPENSPEC_VALIDATE: not run (no normative openspec file edits)

GIT_DIFF_CHECK: PASS

FINAL_STATUS: READY_FOR_FRESH_REAUDIT

COMMIT: 5e3c08bfbbc990fefc6a71535283d1825e80bb72
PUSH: origin/cursor/wb-sky-mcp-read-interface-127c
```

## Integration lifecycle note

Provider integration tests marked `destructive_local` depend on root
`conftest.py` → `destructive_lifecycle.ensure_resources` → Docker compose
preflight. A VM without Docker cannot pass setup even when Postgres is
reachable on 5433. Treat missing Docker as an **environment blocker**, not a
product defect. Prepare with `/opsx-test-env UP` before any new authorized run.
