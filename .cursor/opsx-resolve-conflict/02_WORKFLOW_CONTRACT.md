# 02_WORKFLOW_CONTRACT — PREVIEW_ONLY (R40)

## CLI

```text
python -B -m opsx_conflict preview --repo <repository> [--path <conflicted-path>] [--format json|human]
```

Preview is an **explicit** mode. It is never inferred from GO or residual state.

## Single-path selection (R40)

1. No unmerged paths → typed STOP (`PREVIEW_NO_UNMERGED_PATHS` or no active
   conflict operation).
2. Exactly one unmerged path and `--path` omitted → analyze that path.
3. More than one unmerged path and `--path` omitted → typed STOP
   `PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS` with sorted
   `details.unmerged_paths`.
4. `--path` supplied and unmerged → analyze exactly that path.
5. `--path` supplied and not unmerged → `PREVIEW_PATH_NOT_UNMERGED`.

A successful report must not claim multi-path semantic coverage.
`CONTEXT.paths_analyzed` is always a single-element list of the selected path.
`unmerged_paths_inventory` / `all_unmerged_paths` are inventory only.

## Platform gate

1. Windows → preview may proceed.
2. Linux / macOS → typed `UNSUPPORTED_PLATFORM` **before** any repository
   subprocess.

## Inputs

Conflict input is derived from the unmerged index for the selected path:

- stage 1 base blob
- stage 2 ours blob
- stage 3 theirs blob
- path, operation type, HEAD identity when available

Worktree conflict markers are diagnostic only and never replace stage-blob
identity.

## Outputs

Machine-readable preview report (`opsx-resolve-conflict/preview-report/v2`) and
optional Russian human rendering. Human output always begins with:

```text
ADVISORY PREVIEW — изменения не применялись.
Решение должен проверить и применить пользователь.
```

## Fail-closed

STOP when: not unmerged; multiple conflicts without `--path`; path not
unmerged; stage blobs unreadable; Git argv outside read-only allowlist;
repository mutates during analysis; non-Windows; unexpected exception.

Authority/sandbox absence alone does **not** STOP preview.

## GO

GO remains disabled (`GO_CAPABILITY=false`). Staging/write workflows are out of
PREVIEW_ONLY scope.
