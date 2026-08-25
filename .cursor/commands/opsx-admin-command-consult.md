---
name: /opsx-admin-command-consult
id: opsx-admin-command-consult
category: Workflow
description: "READ_ONLY process desk: discuss OPSX command relationships, triage misbehavior, route to one pasteable admin/not-admin next step"
argument-hint: "[process question / incident note / command relationship]"
---

# /opsx-admin-command-consult

READ_ONLY **process consult desk** over OpenSpec/OPSX process surfaces.

Use when the human does not yet know which specialized command to run:
relationship questions (e.g. `/opsx-pipeline` vs
`/opsx-admin-command-analyze-pipeline`), odd behavior of an admin/pipeline
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
  `/opsx-admin-command-analyze-pipeline`
- Confirmed command-contract defect ready to plan/apply →
  `/opsx-admin-command-fix-command-defects`
- Demonstrated need to design a new command →
  `/opsx-admin-command-design-command`
- Process lesson after FIXED Bugbot/fix packet →
  `/opsx-admin-command-promote-process-lesson`
- Commit process surfaces → `/opsx-admin-command-commit`
- Portable zip of all OPSX trees → `/opsx-admin-command-export-bundle`
- Product idea / OpenSpec feature thinking → `/opsx-explore`
- Oversized change TZ / cut scope + park remainder to WORKLOG → `/opsx-bound-scope`
- Product bug → `/opsx-fix-bug` / bug-hunt path

## Authority boundary (mandatory)

- Always `READ_ONLY`. Never write files in any mode (v1).
- Does **not** own `.cursor/pipeline/GRAPH.md` materialization
  (`/opsx-pipeline` UPDATE GO only).
- Does **not** own pipeline redesign proposals
  (`/opsx-admin-command-analyze-pipeline`).
- Does **not** own NEW vs IMPROVE adjudication for new commands
  (`/opsx-admin-command-design-command`).
- Does **not** APPLY contract fixes (`/opsx-admin-command-fix-command-defects`).
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
| `route_fix_defects` | Confirmed or likely contract defect | `/opsx-admin-command-fix-command-defects` |
| `route_analyze_pipeline` | Redesign / usability of pipeline | `/opsx-admin-command-analyze-pipeline` |
| `route_design_command` | Possible new command / coherent packet | `/opsx-admin-command-design-command` |
| `route_promote_lesson` | Transferable process lesson after FIXED | `/opsx-admin-command-promote-process-lesson` |
| `route_pipeline_navigate` | As-is next not-admin step | `/opsx-pipeline` |
| `route_pipeline_update` | Shared graph stale / missing | `/opsx-pipeline UPDATE` |
| `route_admin_commit` | Process files changed, need commit | `/opsx-admin-command-commit` |
| `route_export_bundle` | Need portable zip of all OPSX trees | `/opsx-admin-command-export-bundle` |
| `wrong_branch` | Typing or product logic | `/opsx-fix-types` / static-check or `/opsx-fix-bug` |
| `needs_evidence` | Missing fact blocks safe route | one narrow question; `NEXT_ACTION: none` until answered |

## Canonical relationship cheat-sheet (must keep consistent)

When asked about `/opsx-pipeline` vs `/opsx-admin-command-analyze-pipeline`:

| | `/opsx-pipeline` | `/opsx-admin-command-analyze-pipeline` |
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
- Running full `/opsx-admin-command-analyze-pipeline` redesign inside consult
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
- [ ] Human can see what happened, why, and what to paste next- Human asks how to prepare client/distribution materials after a completed
  change → route to `/opsx-distribute-brief` (not redesign; not create-pr).
- Known completed-change client/CS brief → `/opsx-distribute-brief`
  `/opsx-meta-fix-command-defects`
- Commit process surfaces → `/opsx-meta-commit`
  (`/opsx-admin-command-commit` = obsolete alias/redirect only)
- Unmerged / merge|rebase conflicts on process surfaces →
  `/opsx-admin-command-resolve-conflicts`
- Does **not** APPLY contract fixes (`/opsx-meta-fix-command-defects`).
`meta-commit`, `resolve-conflicts`), not here.
| `route_fix_defects` | Confirmed or likely contract defect | `/opsx-meta-fix-command-defects` |
| `route_admin_commit` | Process files changed, need commit | `/opsx-meta-commit` |
| `route_resolve_conflicts` | Unmerged paths / merge\|rebase on process surfaces | `/opsx-admin-command-resolve-conflicts` |
When asked about process-surface **git conflicts** vs **commits**:
| | `/opsx-admin-command-resolve-conflicts` | `/opsx-meta-commit` |
| Role | Resolve unmerged process paths; finish merge/rebase continue | Semantic local commits on a **non-conflicted** process tree |
| Writes | Only with `GO` (resolved files + continue/abort) | Only with `GO` (stage + commit) |
| Refuse | Product-only / mixed-scope without split | Merge/rebase / unmerged paths (redirect to resolve) |
`/opsx-admin-command-commit` is an obsolete thin redirect to `/opsx-meta-commit`
(and conflicted-tree → resolve-conflicts); not a second commit SoT.
Prevention (advisory): avoid editing the same process file on two long-lived
branches; serialize shared contracts before consumers.
