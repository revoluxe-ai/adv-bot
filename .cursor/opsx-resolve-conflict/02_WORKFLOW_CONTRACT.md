# 02_WORKFLOW_CONTRACT — PREVIEW_ONLY (R34)

## CLI

```text
python -B -m opsx_conflict preview --repo <repository> [--path <conflicted-path>] [--format json|human]
```

Preview is an **explicit** mode. It is never inferred from GO or residual state.

## Platform gate

1. Windows → preview may proceed.
2. Linux / macOS → typed `UNSUPPORTED_PLATFORM` **before** any repository
   subprocess.

## Inputs

Conflict input is derived from the unmerged index:

- stage 1 base blob
- stage 2 ours blob
- stage 3 theirs blob
- path, operation type, HEAD identity when available

Worktree conflict markers are diagnostic only and never replace stage-blob
identity.

## Outputs

Machine-readable preview report (`opsx-resolve-conflict/preview-report/v1`) and
optional Russian human rendering. Human output always begins with:

```text
ADVISORY PREVIEW — изменения не применялись.
Решение должен проверить и применить пользователь.
```

## Fail-closed

STOP when: not unmerged; path not unmerged; stage blobs unreadable; Git argv
outside read-only allowlist; repository mutates during analysis; non-Windows;
unexpected exception.

Authority/sandbox absence alone does **not** STOP preview.

## GO

GO remains disabled (`GO_CAPABILITY=false`). Staging/write workflows are out of
PREVIEW_ONLY scope.
