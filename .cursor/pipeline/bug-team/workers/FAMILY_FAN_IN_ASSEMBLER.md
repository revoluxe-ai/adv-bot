# Worker: FAMILY_FAN_IN_ASSEMBLER (V8 shadow)

```text
WORKER_ID: FAMILY_FAN_IN_ASSEMBLER
V8_IMPLEMENTATION: SHADOW_CANDIDATE
BUG_FAMILY_FANOUT_ENABLED: false (default)
POLICY: .cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json
```

Replaces root-only FANIN when family fanout is enabled.

## WRITE_BOUNDARY

```text
ALLOWED: results/FAMILY-FANIN.md
FORBIDDEN: HUMAN_SUMMARY closure; learning; family status CLOSED without host
```

See policy `FAMILY_CLOSURE_CONDITIONS` and `BLOCKING_RULES`.
