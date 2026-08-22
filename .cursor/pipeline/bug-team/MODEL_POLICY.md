# Model selection policy (Candidate)

```text
MODEL_SELECTION_POLICY: auto
IMPLEMENTATION_STATUS: IMPLEMENTED_NOT_VALIDATED
RUNTIME_STATUS: NOT_ACTIVE
```

## Rules

1. Cursor Task / subagents: **model inherit only** — never pass explicit
   model IDs (Claude, GPT, Sonnet, etc.).
2. Cursor CLI sessions created by the orchestrator: Cursor Auto / default
   only — never `--model`, never API key overrides for this pipeline.
3. An Auto-routed effective backend name is not a policy violation.
4. Do not pin a vendor model in registry entries or checkpoints.
