# Runtime

This directory is the typed execution boundary for `/opsx-resolve-conflict`.

The command must not use raw shell, Cursor direct-edit tools, subagents,
workers, nested OPSX commands, or untyped repository scripts.

Review entrypoint:

```text
runtime/opsx_conflict/runtime.py
```

Candidate status: not installed, not authorized for live execution.
