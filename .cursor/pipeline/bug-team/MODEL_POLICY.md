# Model selection policy

Authority: `.cursor/pipeline/shared/MODEL_DISPATCH.md`

```text
MODEL_SELECTION_POLICY: inherit
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: ACTIVE
```

## Rules

1. Cursor Task / subagents: **`model: inherit`** explicitly — never omit
   `model`, never `auto`, never explicit API slugs under interim Owner policy.
2. Cursor CLI sessions created by the orchestrator: inherit parent chat model
   only — never `--model`, never API key overrides for this pipeline.
3. Do not pin a vendor model slug in registry entries or checkpoints.
4. Owner `MODEL=<slug>` override — deferred; when enabled, slug must match
   `MODEL_REGISTRY.json`.
