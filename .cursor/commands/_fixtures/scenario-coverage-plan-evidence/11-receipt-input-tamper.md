# T11 — receipt input tamper

## Given

Receipt `INPUTS.*.content_hash` values tampered so they no longer match
files (or claim false CURRENT).

## When

Consumer validation.

## Expected

```text
STALE | INVALID | INTEGRITY_FAIL
Never PASS
```
