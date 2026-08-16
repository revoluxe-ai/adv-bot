---
name: "speckit-taskstoissues"
description: "Convert existing tasks into actionable, dependency-ordered GitHub issues for the feature based on available design artifacts."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/taskstoissues.md"
---


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks-to-issues conversion)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_taskstoissues` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, evaluate `condition` **in this agent session** (there is no separate HookExecutor runtime in Cursor skills). Do **not** skip a hook merely because `condition` is non-empty:
  - Resolve the hook entry's `extension` field (string). This is the only valid `<extension-id>` for that hook's `config.*` clauses. Do not infer `extension-id` from condition text, command name, or filesystem scan.
  - Resolve merged extension config using HookExecutor/ConfigManager semantics (later layers override earlier): (1) `extension.yml` → `config` → `defaults` in `.specify/extensions/{extension}/`, (2) project config `.specify/extensions/{extension}/{extension}-config.yml`, (3) overlay `local-config.yml` in that directory when present, (4) environment variables `SPECKIT_{EXTENSION}_*` where `{EXTENSION}` is the extension id with hyphens replaced by underscores then uppercased (e.g. `my-ext` → `SPECKIT_MY_EXT_*`; key path segments mapped per ConfigManager env rules).
  - If `condition` contains any `config.` token and `extension` is missing, null, or empty → evaluate condition as **false** (hook not executable; fail-closed, same as HookExecutor).
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If `condition` is non-empty, evaluate it using Spec Kit `HookExecutor` semantics and execute only when the result is true:
    - `config.<dotted.path> is set` — true when every segment of the dotted path exists in the merged extension config above (HookExecutor `has_value` / ConfigManager `has_value`): absent path → false; present path → true, including explicit `null` and falsy scalars (`false`, `0`, `""`)
    - `config.<dotted.path> == 'value'` / `!= 'value'` — normalize config values before compare (HookExecutor): YAML booleans → lowercase strings `true`/`false`; other scalars → string form; compare normalized value to the quoted RHS literal (strip quotes). Example: YAML boolean `true` matches `== 'true'`.
    - `env.<VAR_NAME> is set` — true when the environment variable is present (name uppercased)
    - `env.<VAR_NAME> == 'value'` / `!= 'value'` — compare against `os.environ` using the uppercased variable name (HookExecutor: same normalization as `is set`)
  - If the condition cannot be parsed or evaluation fails, treat the hook as **not** executable (same fail-closed default as HookExecutor)
  - Hooks whose condition evaluates to false are skipped; do not emit EXECUTE_COMMAND for them
- When constructing slash commands from hook command names, replace dots (`.`) with hyphens (`-`). For example, `speckit.git.commit` → `/speckit-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
1. **IF EXISTS**: Load `.specify/memory/constitution.md` for project principles and governance constraints.
1. From the executed script, extract the path to **tasks**.
1. Get the Git remote by running:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

1. **Fetch existing issues for deduplication**: Before creating anything, build the set of task IDs you are about to process from `tasks.md` (each is a `T` followed by three digits, e.g. `T001`). Then use the GitHub MCP server's `list_issues` tool to look for issues that already cover those IDs. Do not pass a `state` value, since omitting it makes the tool return both open and closed issues. Request `perPage: 100` to keep the number of calls down, and since the tool uses cursor-based pagination, request pages with the `after` parameter (using the `endCursor` from the previous response). For each issue title, match it against the task ID pattern `\bT\d{3}\b` (word boundaries so tokens like `ST001` or `T0010` are not matched by mistake; this also recognises titles written as `T001 ...`, `T001: ...` or `[T001] ...`) and, when it matches one of your task IDs, mark that ID as already having an issue. Stop paginating as soon as every task ID has been matched, or when there are no more pages, so you do not keep fetching the whole repository's issue history once all task IDs are accounted for. This bounds the number of calls on repos with large issue histories and still prevents duplicates when the command is re-run after `tasks.md` is regenerated or the skill is re-invoked.
1. For each task in the list, use the GitHub MCP server to create a new issue in the repository that is representative of the Git remote. Task lines in `tasks.md` start with a markdown checkbox, so first strip the leading `- [ ]` (and any `[P]` / `[US#]` markers) to recover the task ID and its description. Create the issue with a single canonical title of the form `T001: <description>`, with the ID written once followed by the task description (for example, the line `- [ ] T001 Create project structure` becomes the title `T001: Create project structure`).
   - **Skip** any task whose ID is already present in the set of existing issues from the previous step, and report it (for example, `T001 already has an issue, skipping`).
   - Only create issues for tasks that do not yet have a matching issue.

> [!CAUTION]
> UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL

## Post-Execution Checks

**Check for extension hooks (after tasks-to-issues conversion)**:
Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_taskstoissues` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, evaluate `condition` **in this agent session** (there is no separate HookExecutor runtime in Cursor skills). Do **not** skip a hook merely because `condition` is non-empty:
  - Resolve the hook entry's `extension` field (string). This is the only valid `<extension-id>` for that hook's `config.*` clauses. Do not infer `extension-id` from condition text, command name, or filesystem scan.
  - Resolve merged extension config using HookExecutor/ConfigManager semantics (later layers override earlier): (1) `extension.yml` → `config` → `defaults` in `.specify/extensions/{extension}/`, (2) project config `.specify/extensions/{extension}/{extension}-config.yml`, (3) overlay `local-config.yml` in that directory when present, (4) environment variables `SPECKIT_{EXTENSION}_*` where `{EXTENSION}` is the extension id with hyphens replaced by underscores then uppercased (e.g. `my-ext` → `SPECKIT_MY_EXT_*`; key path segments mapped per ConfigManager env rules).
  - If `condition` contains any `config.` token and `extension` is missing, null, or empty → evaluate condition as **false** (hook not executable; fail-closed, same as HookExecutor).
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If `condition` is non-empty, evaluate it using Spec Kit `HookExecutor` semantics and execute only when the result is true:
    - `config.<dotted.path> is set` — true when every segment of the dotted path exists in the merged extension config above (HookExecutor `has_value` / ConfigManager `has_value`): absent path → false; present path → true, including explicit `null` and falsy scalars (`false`, `0`, `""`)
    - `config.<dotted.path> == 'value'` / `!= 'value'` — normalize config values before compare (HookExecutor): YAML booleans → lowercase strings `true`/`false`; other scalars → string form; compare normalized value to the quoted RHS literal (strip quotes). Example: YAML boolean `true` matches `== 'true'`.
    - `env.<VAR_NAME> is set` — true when the environment variable is present (name uppercased)
    - `env.<VAR_NAME> == 'value'` / `!= 'value'` — compare against `os.environ` using the uppercased variable name (HookExecutor: same normalization as `is set`)
  - If the condition cannot be parsed or evaluation fails, treat the hook as **not** executable (same fail-closed default as HookExecutor)
  - Hooks whose condition evaluates to false are skipped; do not emit EXECUTE_COMMAND for them
- When constructing slash commands from hook command names, replace dots (`.`) with hyphens (`-`). For example, `speckit.git.commit` → `/speckit-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently
