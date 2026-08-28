# Model dispatch policy (OPSX process surfaces)

```text
POLICY_ID: OPSX_MODEL_DISPATCH_INHERIT_V1
STATUS: ACTIVE
INTERIM_OWNER_POLICY: inherit-only
MODEL_REGISTRY_PATH: .cursor/pipeline/shared/MODEL_REGISTRY.json
SYNC_COMMAND: /opsx-meta-sync-models
```

## Interim rule (Owner «пока»)

Every Cursor **Task** / subagent hop launched by OPSX orchestrators MUST pass
**explicit** `model: inherit` (parent chat agent model).

Forbidden until Owner enables slug override:

- omitting `model` (silent platform Auto);
- `model: auto` or `MODEL=auto`;
- default mini / fast / premium slug fallbacks (`gpt-5.4-mini-high`, etc.);
- silent upgrade to faster tier (`composer-2.5` → `composer-2.5-fast`).

## Task tool shape (mandatory)

```text
Tool: Task
arguments:
  description: "<short title>"
  subagent_type: <from registry or generalPurpose>
  model: inherit
  prompt: |
    ...
    MODEL_SELECTION_POLICY: inherit
```

## Pseudo tokens (registry)

| Token | Meaning |
|---|---|
| `inherit` | Parent chat model — **default for all orchestrators** |
| `auto` | Platform Auto — **not used** under interim policy |

API slugs (`composer-2.5`, `gpt-5.3-codex`, …) live in
`MODEL_REGISTRY.json`. Owner `MODEL=<slug>` override is **deferred**; when
enabled, slugs must match registry exactly (no fuzzy display names).

## Orchestrator dispatch envelope

```text
MODEL_MODE: INHERIT
REQUESTED_MODEL: inherit
MODEL_SELECTION_REASON: OPSX_MODEL_DISPATCH_INHERIT_V1
```

## Consumers

- `/opsx-supervisor` §7 / §15
- `/opsx-commit-all`
- `/opsx-bug-team` + bug-team pipeline (`TASK_DISPATCH`, `REGISTRY`, workers)
- Future: `/opsx-static-check` SERIAL workers (separate fix-defects packet)

## Violations

| Observation | Verdict |
|---|---|
| `model` omitted on Task | `POLICY_VIOLATION` |
| `model: auto` or `MODEL=auto` | `POLICY_VIOLATION` |
| explicit premium / MAX slug without Owner override gate | `POLICY_VIOLATION` |
| `model: inherit` with `MODEL_MODE=INHERIT` | compliant |
