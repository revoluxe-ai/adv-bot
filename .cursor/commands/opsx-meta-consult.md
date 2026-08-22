---
component_id: opsx.commands.meta_consult
component_version: 0.4.0
ownership: EMBEDDED_SHARED
runtime_class: ACTIVE
source_commit: a71601dba3b9f5cd0076ea7185bdbbe56eaf2e3f
source_path: .cursor/commands/opsx-meta-consult.md
source_blob_sha: 9e0fecda685f3438e055fef4d45a1030a9a12fcf
embedded_canonical_sha256: 70e8b9db43f8b3c3cd876375c4ee13938665556931980e1cb6e9b63e92a77287
upstream_snapshot: .opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-consult.md
required_adapters: ["opsx-lite"]
local_modification_note: "Projectize 2026-08-07: vue-npm dropped; poetry-python adapter; OPSX-WB-META-SURFACE-01"
local_override_policy: TARGET_OVERRIDE_HIGHEST_PRIORITY
contract_id: OPSX-WB-META-SURFACE-01
newline_normalization: none
---

# TARGET OVERRIDE — HIGHEST PRIORITY

**Contract:** `OPSX-WB-META-SURFACE-01`  
**Runtime class:** `ACTIVE`  
**Precedence:** This override wins over the canonical source body for target paths, capabilities, safety stops, and authority.

### Target authority paths

- Changes: `openspec/changes/**`
- Policies: `openspec/policies/**`
- Decisions: `openspec/decisions/**`
- Schemas/templates: `openspec/schemas/**`
- Activation/provenance: `.opsx/registry/**`
- Frozen upstream: `.opsx/upstream/a71601dba3b9/`
- Adapter: `.opsx/adapters/poetry-python/README.md`
- Quality gates: `.opsx/project/quality-gates.md`

### Hard target bans

- Do not install dependencies / modify `package.json` or lockfile.
- Do not access production / Kubernetes / secrets.
- Do not push, open PR, rebase, force, or deploy.
- Do not activate WB/product domain assumptions from the source body.
- Replace Poetry/pytest/pyright/kubectl execution with capability checks; missing capability => unavailable or FAIL_CLOSED, never PASS-by-absence.
- Mandatory declared executable checks: per `.opsx/project/quality-gates.md` (poetry-python). `npm run build` is UNAVAILABLE / not applicable (vue-npm dropped; no root build script).
- Smoke/acceptance/lint/typecheck/frontend tests: UNAVAILABLE unless adapter says otherwise.

### Projectization gate

Read `.opsx/projectization.yaml` before any write.
If `status` != `COMPLETE` or `normal_commands_enabled` is false:

```text
STATUS: FAIL_CLOSED
REASON: OPSX_PROJECTIZATION_REQUIRED
NEXT_COMMAND: /opsx-projectize
```

Exempt: `/opsx-projectize` and `/opsx-projectize:GO`.

### ACTIVE allow

Owner unblocked this former-DEFERRED command (2026-08-03): execute canonical source-body semantics **after** remapping paths to target authority above.

Hard bans still apply. Missing Poetry/pytest/pyright/kubectl (and other undeclared source capabilities) => UNAVAILABLE or FAIL_CLOSED — never PASS-by-absence. Do not invent missing adapters or import source product dumps. File/process operations only on target authority paths.

# BEGIN CANONICAL SOURCE BODY
---
name: /opsx-meta-consult
id: opsx-meta-consult
category: Workflow
description: "READ_ONLY process desk: discuss OPSX command relationships, triage misbehavior, route to one pasteable admin/not-admin next step"
argument-hint: "[process question / incident note / command relationship]"
---

# /opsx-meta-consult

READ_ONLY **process consult desk** over OpenSpec/OPSX process surfaces.

Use when the human does not yet know which specialized command to run:
relationship questions (e.g. `/opsx-pipeline` vs
`/opsx-meta-analyze-pipeline`), odd behavior of an admin/pipeline
command, ownership ambiguity, or “where does this process question belong?”

This command **discusses, classifies, and routes**. It does not redesign the
pipeline, fix contracts, design new commands, navigate day-to-day work, or
commit.

Follow `.cursor/commands/opsx-source-resolution.md` and
`.cursor/commands/opsx-execution-preflight.md` (including Read / tool I/O
budgets).

## Purpose

Reduce front-door uncertainty for process questions:

1. Answer ownership / relationship questions from **current** contracts when
   evidence is sufficient.
2. Classify signals (misbehavior, gap, wrong branch, needs redesign, …).
3. Emit exactly one pasteable `NEXT_ACTION` to the owning command — or `none`
   when the answer is complete in this turn.

## When to use

- Unclear which process/admin command applies.
- Need to discuss how two OPSX commands relate (authority, graph, handoff).
- An admin or pipeline command “behaved wrongly” and triage is needed before
  fix / analyze / design.
- Ambiguous process ownership or bypass concern (discuss only; do not APPLY).

## When not to use

- Known day-to-day next not-admin step → `/opsx-pipeline` (NAVIGATE)
- Known pipeline redesign / human-usability improvement pass →
  `/opsx-meta-analyze-pipeline`
- Confirmed command-contract defect ready to plan/apply →
  `/opsx-meta-fix-command-defects`
- Demonstrated need to design a new command →
  `/opsx-meta-design-command`
- Process lesson after FIXED Bugbot/fix packet →
  `/opsx-meta-promote-process-lesson`
- Commit process surfaces → `/opsx-meta-commit`
- Product idea / OpenSpec feature thinking → `/opsx-explore`
- Oversized change TZ / cut scope + park remainder to WORKLOG → `/opsx-bound-scope`
- Product bug → `/opsx-fix-bug` / bug-hunt path

## Authority boundary (mandatory)

- Always `READ_ONLY`. Never write files in any mode (v1).
- Does **not** own `.cursor/pipeline/GRAPH.md` materialization
  (`/opsx-pipeline` UPDATE GO only).
- Does **not** own pipeline redesign proposals
  (`/opsx-meta-analyze-pipeline`).
- Does **not** own NEW vs IMPROVE adjudication for new commands
  (`/opsx-meta-design-command`).
- Does **not** APPLY contract fixes (`/opsx-meta-fix-command-defects`).
- Does **not** override verify / archive / sync / commit / approval gates.
- Does **not** treat chat answers as a second lifecycle authority.
- Recommendation / route strength is advisory for navigation targets;
  downstream commands keep their own GO gates.

## User input

```text
$ARGUMENTS
```

Argument optional. Empty invoke is valid if the latest user message already
states the process question or incident.

## Modes

| Input | Mode | Writes |
|---|---|---|
| default (any text; `GO` ignored for writes) | `READ_ONLY` | never |

If the user includes `GO`: still no writes. Explain that APPLY lives on the
routed command (`fix-command-defects`, `design-command`, `pipeline UPDATE GO`,
`admin-commit`), not here.

## Topic classes (exactly one)

| TOPIC_CLASS | Meaning | Typical NEXT_ACTION |
|---|---|---|
| `relationship_clarified` | Ownership/handoff answered in-place | `none` or `/opsx-pipeline` if operator still needs navigate |
| `misbehavior_triage` | Command behaved oddly; classify cause | fix-defects / analyze / design / none |
| `route_fix_defects` | Confirmed or likely contract defect | `/opsx-meta-fix-command-defects` |
| `route_analyze_pipeline` | Redesign / usability of pipeline | `/opsx-meta-analyze-pipeline` |
| `route_design_command` | Possible new command / coherent packet | `/opsx-meta-design-command` |
| `route_promote_lesson` | Transferable process lesson after FIXED | `/opsx-meta-promote-process-lesson` |
| `route_pipeline_navigate` | As-is next not-admin step | `/opsx-pipeline` |
| `route_pipeline_update` | Shared graph stale / missing | `/opsx-pipeline UPDATE` |
| `route_admin_commit` | Process files changed, need commit | `/opsx-meta-commit` |
| `wrong_branch` | Typing or product logic | `/opsx-fix-types` / static-check or `/opsx-fix-bug` |
| `needs_evidence` | Missing fact blocks safe route | one narrow question; `NEXT_ACTION: none` until answered |

## Canonical relationship cheat-sheet (must keep consistent)

When asked about `/opsx-pipeline` vs `/opsx-meta-analyze-pipeline`:

| | `/opsx-pipeline` | `/opsx-meta-analyze-pipeline` |
|---|---|---|
| Role | Navigate **as-is** not-admin pipeline | Analyze / improve process **design** |
| Graph | Durable `.cursor/pipeline/GRAPH.md` | Ephemeral chat `CURRENT_GRAPH` |
| Writes | Only `UPDATE GO` → GRAPH + META | Never |
| Strength | Advisory navigation | Improvement proposals (not approval) |
| Bridge | May consume analyze draft as **evidence** for UPDATE only | Draft is not the operator map until UPDATE GO |

Do not invent alternate durable graph locations.

## Steps (READ_ONLY)

1. Parse the human question / incident from `$ARGUMENTS` or latest message.
2. Wrong-branch check: typing → `wrong_branch` + fix-types/static-check;
   product logic bug → `wrong_branch` + fix-bug path. Stop.
3. Identify cited commands / paths. Grep-first; parallel Read max **2**;
   section Read ≤ 120 lines. Cap substantive section-Reads at **5** per run
   unless `EVIDENCE_GAP` is recorded.
4. Do **not** preload `opsx-learn-from-bug.md`, full command-set dumps, or
   unrelated large siblings unless cited as required for the topic.
5. Answer relationship / ownership from opened contracts when possible.
6. Choose exactly one `TOPIC_CLASS`.
7. Emit output contract with one pasteable `NEXT_ACTION`.
8. Never edit files. Never execute the routed command in the same turn unless
   the user separately invoked it.

## I/O budgets

- Prefer Grep + filename inventory over full-file Read.
- Parallel Read max **2**.
- Large process files: section Read or Grep ± context.
- Read stall/timeout → stop stacking; return `BLOCKED_NEEDS_EVIDENCE` /
  `EVIDENCE_GAP` rather than hanging.
- GRAPH.md / META.md: exact-path Read only when navigation freshness or
  pipeline↔analyze relationship needs the shared materialization.

## Output contract (every run)

```text
STATUS:
MODE: READ_ONLY
WHAT_HAPPENED:
WHY:
TOPIC_CLASS:
ANSWER_SUMMARY:
CITED_COMMANDS:
EVIDENCE_REFS:
OWNER_DECISION_REQUIRED:
NEXT_ACTION:
DO_NOT_DO_YET:
```

### STATUS values

```text
CONSULTED
ROUTED
ANSWERED_IN_PLACE
WRONG_BRANCH
BLOCKED_NEEDS_EVIDENCE
```

### Field meaning

- `WHAT_HAPPENED` — what this consult did (discuss / classify / route)
- `WHY` — basis for the class and route
- `TOPIC_CLASS` — exactly one from the table above
- `ANSWER_SUMMARY` — short human-readable answer (relationships, triage)
- `CITED_COMMANDS` — `/opsx-*` names involved
- `EVIDENCE_REFS` — exact paths read or Grep hits used
- `OWNER_DECISION_REQUIRED` — `none` or the exact decision still on the owner
- `NEXT_ACTION` — one pasteable command, or `none`
- `DO_NOT_DO_YET` — actions that would bypass a downstream gate or invent writes

## Failure / recovery

| Condition | STATUS | NEXT_ACTION |
|---|---|---|
| Missing fact | `BLOCKED_NEEDS_EVIDENCE` | `none` + one question |
| Typing / product branch | `WRONG_BRANCH` | fix-types / fix-bug (as appropriate) |
| Relationship answered fully | `ANSWERED_IN_PLACE` | `none` (or pipeline if still needed) |
| Clear specialized next step | `ROUTED` | that command |
| Discussed without full route | `CONSULTED` | best single next step or `none` |

## Anti-patterns (reject)

- Writing GRAPH.md, command files, rules, or commits from this command
- Treating consult output as GO for fix/design/pipeline UPDATE
- Running full `/opsx-meta-analyze-pipeline` redesign inside consult
- Substituting for `/opsx-pipeline` day-to-day navigation
- Using `/opsx-explore` policies/WORKLOG as process authority
- Inventing a second durable pipeline map
- Multiple competing NEXT_ACTION lines
- Silent APPLY of contract “fixes” suggested during discussion

## Self-review checklist

Before returning:

- [ ] Mode is READ_ONLY; no files written
- [ ] Exactly one TOPIC_CLASS
- [ ] Exactly one NEXT_ACTION (or `none`)
- [ ] Authority boundaries respected (no graph/redesign/design/fix ownership steal)
- [ ] Wrong-branch redirects used when not process
- [ ] I/O budgets respected
- [ ] Human can see what happened, why, and what to paste next
# END CANONICAL SOURCE BODY

# TARGET ADAPTATION NOTES

- upstream_snapshot: `.opsx/upstream/a71601dba3b9/.cursor/commands/opsx-admin-command-consult.md`
- runtime_class: `ACTIVE`
- active_name: `/opsx-meta-consult`
- openspec_store: `openspec/changes/**` (not source multi-store / not `.opsx/changes` SoT)
- quality: poetry-python gates per `.opsx/project/quality-gates.md` when in scope; `npm run build` UNAVAILABLE; smoke/frontend UNAVAILABLE
- unresolved_source_sections: any Poetry/pytest/pyright/kubectl/WB-domain steps in the body are blocked by TARGET OVERRIDE until adapters exist
- manual_review: `.opsx/project/manual_review.md`
- route_remap: user-facing slash commands MUST emit `/opsx-meta-*`.
  Historical `/opsx-admin-command-*` names appear only in `upstream_snapshot`
  provenance. Foreign OPSX / central reuse →
  `/opsx-meta-import-command`. Orientation → `/opsx-meta`.
- orientation: emit `ORIENTATION_HINT` with `NEXT_META: /opsx-meta`
