---
name: /opsx-worklog-normalize
id: opsx-worklog-normalize
category: Workflow
description: "Normalize DOTO/WORKLOG.md into an explore-readable, lossless structure"
---

Normalize `DOTO/WORKLOG.md` so `/opsx:explore` can read it without drowning in raw notes.

This command is allowed to edit only WORKLOG-related files after explicit `GO`.

Default mode is **PLAN ONLY**.

## Purpose

The user keeps dumping raw notes into `DOTO/WORKLOG.md` chaotically. That is accepted behavior.

Your job is not to judge the note style. Your job is to make the file useful for future `/opsx:explore` runs without losing any information.

## Hard rule

**Lossless normalization is mandatory.**

You MUST NOT delete, rewrite away, silently merge, or discard any original worklog content.

Every original note must remain recoverable either:

1. verbatim in the rewritten `DOTO/WORKLOG.md`, or
2. verbatim in a timestamped raw backup file under `DOTO/worklog_archive/`.

If you cannot prove losslessness, stop and report `BLOCKED: lossless check failed`.

## Modes

### PLAN mode

Triggered when the user runs:

```text
/opsx:worklog-normalize
```

In PLAN mode:

- read files only;
- do not edit anything;
- classify the current worklog;
- propose the normalized structure;
- show risks;
- show exact files that would be changed in GO mode.

### GO mode

Triggered only when the user runs:

```text
/opsx:worklog-normalize GO
```

In GO mode you may write only:

- `DOTO/WORKLOG.md`
- `DOTO/worklog_archive/<timestamp>_WORKLOG_RAW.md`

You MUST NOT edit:

- production code;
- OpenSpec change artifacts;
- `openspec/config.yaml`;
- `.cursor/commands/opsx-explore.md`;
- tests;
- migrations;
- CI;
- Docker/Kubernetes/infra;
- secrets;
- git history.

No commit, push, merge, rebase, deploy, DB migration, service restart, or destructive filesystem operation.

## Required input files

Read:

- `DOTO/WORKLOG.md`
- `openspec/config.yaml`
- `openspec/policies/EXPLORE_POLICY.md`
- `.cursor/commands/opsx-explore.md`

If some optional policy/command file is missing, report it, but continue if `DOTO/WORKLOG.md` exists.

If `DOTO/WORKLOG.md` is missing, stop with:

```text
BLOCKED: DOTO/WORKLOG.md not found.
```

## Required analysis

Parse the current `DOTO/WORKLOG.md` into these buckets:

1. `NOW`
   - active work;
   - WIP;
   - current debug;
   - things that can block today.

2. `NEXT`
   - near-term product/code tasks;
   - tasks likely to become OpenSpec changes.

3. `BUGS_AND_DRIFT`
   - suspected bugs;
   - confirmed bugs;
   - production drift;
   - spec/code mismatch;
   - flaky or failing checks.

4. `DECISIONS`
   - durable decisions;
   - explicit “do not do now” decisions;
   - tradeoff notes.

5. `OPENSPEC_PROCESS`
   - OpenSpec customization;
   - command/rule/guard/template work;
   - agent workflow issues;
   - worklog/explore/verify/archive process notes.

6. `PRODUCT_AND_BUSINESS`
   - partner program;
   - promo;
   - onboarding;
   - pricing;
   - customer-facing text;
   - lead generation.

7. `INFRA_AND_DEVOPS`
   - Harbor;
   - Docker;
   - Kubernetes;
   - CI/CD;
   - backups;
   - monitoring;
   - repositories.

8. `REFACTOR_AND_TECH_DEBT`
   - DI;
   - DTO;
   - central services;
   - old branches/stash;
   - tests cleanup;
   - legacy removal.

9. `PARKING_LOT`
   - interesting but not current;
   - low priority;
   - vague ideas;
   - personal learning/tooling that does not affect current WB Sky work.

10. `UNCLASSIFIED_RAW`
   - anything uncertain;
   - anything that does not fit;
   - anything you are tempted to delete.

When unsure, put the item into `UNCLASSIFIED_RAW`, not into a guessed bucket.

## Normalized WORKLOG format

Rewrite `DOTO/WORKLOG.md` using exactly this structure:

```markdown
# WORKLOG

Purpose: raw operational memory for WB Sky. This file is intentionally imperfect.
Rule: do not treat worklog notes as source of truth. Explore must verify against repo/OpenSpec evidence.

Last normalized: <YYYY-MM-DD HH:MM local>
Raw backup: DOTO/worklog_archive/<timestamp>_WORKLOG_RAW.md

## NOW

### WIP <= 2
- [ ] ...

### Active Debug
- [ ] ...

## NEXT

### P1
- [ ] ...

### P2
- [ ] ...

### Later
- [ ] ...

## BUGS_AND_DRIFT

### Confirmed / likely bugs
- [ ] ...

### Needs classification
- [ ] ...

### Drift / mismatch
- [ ] ...

## DECISIONS

- Decision:
  - Context:
  - Current decision:
  - Why:
  - Revisit when:

## OPENSPEC_PROCESS

### Commands / rules / guards
- [ ] ...

### Workflow debt
- [ ] ...

### Agent handoff notes
- [ ] ...

## PRODUCT_AND_BUSINESS

- [ ] ...

## INFRA_AND_DEVOPS

- [ ] ...

## REFACTOR_AND_TECH_DEBT

- [ ] ...

## PARKING_LOT

- [ ] ...

## UNCLASSIFIED_RAW

Keep anything here if classification is uncertain.

- ...

## DONE

Keep only recent or meaningful done items here. Do not delete older done items unless they are preserved in the raw backup.

- ...

## NORMALIZATION_NOTES

- Normalized by: /opsx:worklog-normalize
- Lossless raw backup:
- Items moved:
- Items left unclassified:
- Duplicates detected:
- Follow-up recommended:
```

## Classification rules

Use conservative classification.

- A note mentioning `bug`, `падает`, `ошибка`, `drift`, `не работает`, `стрельнем в ногу`, `root cause`, `regression`, `pyright`, `mypy`, `skip-тесты` belongs in `BUGS_AND_DRIFT` unless clearly process-only.
- A note mentioning OpenSpec, `opsx`, command, rule, guard, config, worklog, explore, verify, archive, prompt, agent, Cursor, Codex belongs in `OPENSPEC_PROCESS`.
- A note mentioning Harbor, Docker, Kubernetes, CI/CD, backup, repository, prod, monitoring, worker crash belongs in `INFRA_AND_DEVOPS`.
- A note mentioning DI, DTO, refactor, legacy, centralize, tests cleanup, branch/stash belongs in `REFACTOR_AND_TECH_DEBT`.
- A note mentioning clients, partners, promo, article, pricing, offer, onboarding, lead, Telegram distribution belongs in `PRODUCT_AND_BUSINESS`.
- A note with immediate language like `срочно`, `TODAY`, `WIP`, `debug`, current branch, current exact case belongs in `NOW`.
- A note with explicit future priority `P1`, `P2`, `NEXT` belongs in `NEXT`.
- A decision block must stay in `DECISIONS`, preserving its reasoning.

Do not over-normalize language. Preserve domain terms and original Russian phrasing where useful.

## Duplicate handling

You MAY group obvious duplicates, but only if the original meaning is preserved.

For duplicates, write:

```markdown
- [ ] <normalized task>
  - duplicates/originals:
    - "<original line 1>"
    - "<original line 2>"
```

Never drop duplicate originals unless the raw backup exists and the final report names the backup path.

## GO mode required steps

In GO mode:

1. Read `DOTO/WORKLOG.md`.
2. Create directory `DOTO/worklog_archive/` if missing.
3. Create exact raw backup:
   - path: `DOTO/worklog_archive/<YYYYMMDD_HHMMSS>_WORKLOG_RAW.md`
   - content: exact original `DOTO/WORKLOG.md`
4. Rewrite `DOTO/WORKLOG.md` into the normalized structure.
5. Run a lossless sanity check:
   - backup file exists;
   - backup file byte/content length equals original pre-edit content length;
   - backup file content equals original pre-edit content exactly;
   - normalized file contains the backup path;
   - normalized file has `UNCLASSIFIED_RAW`;
   - no bucket required by this command is missing.
6. Run `git diff -- DOTO/WORKLOG.md DOTO/worklog_archive/`.
7. Report final result.

If any check fails, restore `DOTO/WORKLOG.md` from the backup and report:

```text
BLOCKED: lossless check failed, WORKLOG restored from backup.
```

## Do not do

- Do not convert raw worklog into OpenSpec specs.
- Do not create OpenSpec changes from worklog items.
- Do not edit `/opsx:explore` from this command.
- Do not delete vague notes.
- Do not mark worklog-derived claims as confirmed.
- Do not infer repo facts from worklog text.
- Do not “clean up” by throwing away old items.
- Do not create tasks for every line.
- Do not expand scope into implementation.

## Required final output in PLAN mode

```text
Verdict: plan_only

Checked:
- WORKLOG:
- explore command:
- config/policy:
- missing files:

Diagnosis:
- current worklog shape:
- why explore struggles:
- highest-risk sections:

Proposed normalized buckets:
- NOW:
- NEXT:
- BUGS_AND_DRIFT:
- DECISIONS:
- OPENSPEC_PROCESS:
- PRODUCT_AND_BUSINESS:
- INFRA_AND_DEVOPS:
- REFACTOR_AND_TECH_DEBT:
- PARKING_LOT:
- UNCLASSIFIED_RAW:

Would change:
- DOTO/WORKLOG.md
- DOTO/worklog_archive/<timestamp>_WORKLOG_RAW.md

Would not change:
- production code
- OpenSpec change artifacts
- opsx-explore command
- git history

Risks:
- ...

Next action:
Run `/opsx:worklog-normalize GO` if you want the rewrite.
```

## Required final output in GO mode

```text
Verdict: applied / blocked

Changed:
- DOTO/WORKLOG.md
- DOTO/worklog_archive/<timestamp>_WORKLOG_RAW.md

Lossless check:
- raw backup exists:
- raw backup exact match:
- backup path recorded in WORKLOG:
- required buckets present:
- unclassified bucket present:

Summary:
- moved to NOW:
- moved to NEXT:
- moved to BUGS_AND_DRIFT:
- moved to DECISIONS:
- moved to OPENSPEC_PROCESS:
- moved to PRODUCT_AND_BUSINESS:
- moved to INFRA_AND_DEVOPS:
- moved to REFACTOR_AND_TECH_DEBT:
- moved to PARKING_LOT:
- left unclassified:

Diff:
- summarize `git diff -- DOTO/WORKLOG.md DOTO/worklog_archive/`

Risks:
- Worklog remains raw notes, not repo evidence.
- Explore must still verify worklog-derived claims against repo/OpenSpec files.

Next action:
Use `/opsx:explore <topic>` after normalization.
```
