# Evolution planning lane

Authoritative command: `.cursor/commands/opsx-evolution.md`  
Policy: `openspec/policies/EVOLUTION_POLICY.md`  
Registry: `openspec/evolution/**`

## Role lane (capability / star work)

```text
evolution (STAR_ROUTE → OWNER_PICK → COPY_BLOCK with OWNER_INTENT)
  → explore (repository evidence; OWNER_INTENT passthrough)
  → Owner Copy → new chat → Owner types /opsx-new | /opsx-ff | /opsx-update
```

Pre-evolution deep research via `/opsx-explore` remains allowed; it does not
replace evolution ownership of `OWNER_INTENT`.

- `/opsx-evolution` **owns** the post-pick **COPY_BLOCK** (canonical-key paste
  SoT for the owed increment), including mandatory `OWNER_INTENT` (Owner
  wording / product meaning). No `/opsx-*` / bait sections
  (`VALIDATION*`, `ALREADY_DELIVERED`, deploy-devops prose, …) inside the
  fence; Owner chooses the next command in the new chat.
- Canonical COPY_BLOCK keys are scope + semantic SoT for explore/new/ff/update
  — do **not** re-read the North Star card or import non-canonical paste
  sections to invent Future Increments or broaden KEEP. Do **not** let
  repository inference rewrite `OWNER_INTENT`. Deploy hints ≠ change DoD.
- `/opsx-explore` after a handoff may add repository findings/mapping but
  MUST pass `OWNER_INTENT` through unchanged; it is **not** the
  primary «start ff here» door (`PERSIST_VIA: /opsx-evolution`).
- No durable on-disk handoff file is required; cross-chat = Copy/paste.
- Exception: STANDALONE / NOT_APPLICABLE local bug, refactor, or maintenance
  may point to ff/new without a North Star — label explicitly.

A North Star card never authorizes implementation and Future Increments never
become current DoD.

Stars may form a unidirectional `DEPENDS_ON` DAG (value chain on MAP/handoff).
Prerequisite gaps default to **soft WARN**, not a hard stop on new/ff.
