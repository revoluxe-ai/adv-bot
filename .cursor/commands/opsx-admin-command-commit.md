---
description: "OBSOLETE thin redirect — use /opsx-meta-commit (sole process-commit front-door; includes .cursor/devops/**)."
argument-hint: "GO → redirect to /opsx-meta-commit"
---

# OBSOLETE — thin redirect (META-COMMIT-DUAL-FRONTDOOR-001)

`/opsx-admin-command-commit` is **not** a second process-commit SoT.

**Redirect (mandatory on invoke):**

| Situation | Use instead |
|---|---|
| Process / Cursor / OPSX / devops memory commits | `/opsx-meta-commit` (default current-chat; `ALL` for leftover cleanup) |
| Product / app / OpenSpec product commits | `/opsx-commit` |

On invoke:

1. State that this name is obsolete/redirect-only.
2. Print the table above.
3. If the user already pasted `GO` (or a check-mode / `ALL` token set), tell them
   to re-run the **same tokens** under `/opsx-meta-commit` — do **not** stage or
   commit from this file.
4. **Stop.** Do not maintain a parallel allowlist here.

Allowlist SoT for process commits: `.opsx/sources.yaml` +
`.cursor/commands/opsx-meta-commit.md` TARGET OVERRIDE (includes
`.cursor/devops/**` for `OPS_STATE.md` / `LAST.json`; never secrets/DSN).

Historical note: this file previously duplicated the full commit workflow and
was the only surface that listed `.cursor/devops/**`. That ownership moved to
`/opsx-meta-commit` so Owner has one front-door.
