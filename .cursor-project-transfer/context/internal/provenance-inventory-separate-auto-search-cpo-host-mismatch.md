---
cursor:
  subagentId: "bc-46a6495a-00a8-57d5-a117-f79b3a89a196"
---

# Provenance inventory — STOP: HOST_MISMATCH

## Result

**HOST_MISMATCH** — inventory not run. Target worktree was not accessed.

## Host proof (first action)

| Check | Expected | Actual |
|-------|----------|--------|
| `hostname` | `vkita-pc` or `HOME-PC` | `cursor` |
| `whoami` | Owner Windows user | `ubuntu` |
| `Test-Path C:\Users\vkita\my_code\meta-repo\fix-search-cpc` | `True` | **Not executed** — shell is bash on Linux; `powershell.exe` unavailable |

## Environment

- **cwd:** `/agent`
- **OS (user_info):** linux 6.12.94+
- **Shell used:** bash (PowerShell syntax failed on first attempt)

## Git / provenance

No `git fetch`, status, diff classification, or branch checks performed (per stop rule).

## Parent action

Re-run this READ-ONLY inventory on **vkita-pc / HOME-PC** with PowerShell and working directory `C:\Users\vkita\my_code\meta-repo\fix-search-cpc`.
