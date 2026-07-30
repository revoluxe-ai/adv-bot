# Antipattern gate — class catalog

SoT for class IDs used by `/opsx-antipattern-gate`.
Practice decisions live in `PRACTICE_LEDGER.jsonl` (append-only).

Over-report policy: when unsure, scanners SHOULD emit `SUSPECT`.

## Classes

### AP_PROD_TEST_DOUBLE_SNIFF

Production (`app/**` / production scripts) detects or branches on test doubles
(`unittest.mock`, `MagicMock`, `AsyncMock`, `__module__ == "unittest.mock"`).

### AP_WEAK_WRITE_GATE

Write-gate / forbid regression proves only final mock silence
(`assert_not_called`, `call_count == 0`) without showing the entity was
filtered before candidate/handler/write boundary.

### AP_SOURCE_TOKEN_PROOF

Behavioral proof is only `inspect.getsource` / substring tokens in source,
not an observable call/write/state change.

### AP_FROZEN_RED_SIBLING_PROD_SKIP

Production skips a real sibling write because another seam is patched as a
test double (frozen RED / harness leak into prod).

### AP_ASYNC_MODULE_ATTR_MUTATION

Async test mutates shared `module.attr = fake` around `await` with manual
restore (forbidden by testing-rules).

### AP_DEAD_SURFACE_TEST_ONLY

New/changed exported production symbol is only referenced from `tests/**`.

### AP_PROCESS_TEST_ONLY_BRANCH_COMMENT

Comments/docs in production describe branches that exist only to satisfy tests.

## Extending

Add a new `AP_…` section here before relying on it in reports or ledger rows.
Keep IDs stable once accepted/rejected in the ledger.
