# /opsx-learn-from-bug

Purpose: turn a reviewed bug/finding into a small, human-approved Learning Patch for the OpenSpec/Cursor workflow base.

This command has two modes:

- default mode: PLAN ONLY / READ-ONLY
- GO mode: apply only an explicitly approved Learning Patch

Never treat this command as permission to change product code, product specs, active OpenSpec changes, CI, DB, infra, secrets, or unrelated docs.

## Input

The user should provide a Bug Learning Packet.

Required input:

- Bug/finding text:
  - original bugbot / verify / review / user finding
  - symptom
  - affected workflow or module
- Final classification:
  - confirmed bug / false diagnosis / spec drift / sibling bug
  - fix_now / no_fix / needs_base_update
- Correct invariant:
  - 1–3 lines describing what the agent should have understood
- Why it was missed:
  - wrong command reasoning?
  - missing artifact quality rule?
  - missing template field?
  - missing verify check?
  - missing project/domain context?
  - existing rule ignored?
- Existing base evidence:
  - relevant `.cursor/commands/*.md`
  - relevant `openspec/config.yaml` context
  - relevant `openspec/config.yaml` artifact rules
  - relevant `openspec/schemas/**/templates/*.md`
  - relevant verify / classify / bug-hunt command
- Patch limits:
  - max files touched: 2 by default
  - max added chars: 700 by default
  - max new bullets: 3
  - no optimization
  - no unrelated cleanup

If required input is missing, do not guess. Return `needs_human_decision`.

## Allowed target files

In PLAN mode, read-only inspection may include:

- `.cursor/commands/*.md`
- `.cursor/rules/**/*.md`
- `.cursor/rules/**/*.mdc`
- `openspec/config.yaml`
- `openspec/schemas/**/templates/*.md`
- `tools/openspec/openspec_guard.yaml`
- `tools/openspec/openspec_guard.py`

In GO mode, edits are allowed only to explicitly approved target files from this list:

- `.cursor/commands/*.md`
- `.cursor/rules/**/*.md`
- `.cursor/rules/**/*.mdc`
- `openspec/config.yaml`
- `openspec/schemas/**/templates/*.md`

Forbidden files and actions:

- product code
- `openspec/specs/**`
- `openspec/changes/**`
- `.github/**`
- README / AGENTS / CODEX / CLAUDE / broad docs
- CI/CD
- DB / migrations / infra / secrets
- commit / push / deploy
- artifact optimization unless explicitly requested as a separate task

## Core model

Use this model to decide where knowledge belongs:

- Command = procedure of thinking / decision-making.
- Artifact rule = quality criterion for an artifact.
- Template = required output structure / required fields.
- Verify command = post-fact check that the result satisfies the rule.
- Context = compact project/domain model that helps multiple commands and artifacts interpret rules correctly.

Do not duplicate the same sentence in multiple places. If two layers need the same idea, write each layer in its own role:

- Command: forces the agent to check X before deciding.
- Rule: forbids accepting an artifact unless X is represented.
- Template: provides a field where X must be written.
- Verify: checks X after implementation/review.
- Context: explains the domain model that makes X meaningful across workflows.

## Routing rules

Use this decision table.

Case 1: wrong command reasoning

Condition:
- The agent made a bad classification, bad workflow decision, or wrong apply/verify decision.

Target:
- the relevant `.cursor/commands/opsx-*.md`.

Example:
- Bug classifier treated setup-stage missing restore as a confirmed bug without proving a stored snapshot was reachable.

Patch type:
- add one decision check to the command.

Case 2: missing artifact quality criterion

Condition:
- The artifact existed, but it did not have a rule that made weak output unacceptable.

Target:
- `openspec/config.yaml` per-artifact rule, such as `rules.design`, `rules.tasks`, `rules.proposal`, or equivalent existing structure.

Patch type:
- add one atomic MUST / MUST NOT rule.

Case 3: missing required output field

Condition:
- The needed knowledge did not appear because the artifact template had no place for it.

Target:
- `openspec/schemas/**/templates/*.md`.

Patch type:
- add one small field/section to the template.

Case 4: verify missed it

Condition:
- The artifact/rule existed, but the review/verify workflow did not check it.

Target:
- `.cursor/commands/opsx-verify.md` or the specific verify-like command.

Patch type:
- add one verification check.

Case 5: missing project/domain context

Condition:
- The agent had the right local rule or command structure, but missed the broader domain model needed to interpret it.
- The same model would help multiple commands or artifact types.
- The knowledge is stable project/domain context, not a one-off bug lesson.

Target:
- `openspec/config.yaml` context section or equivalent existing project-context structure.

Patch type:
- add or replace one compact context line.

Examples of valid context:
- Stateful WB Sky features often use lifecycle baselines: setup creates the baseline, active protects it, exit clears or archives it.
- WB Sky campaign-state transitions are behavior boundaries; setup, active protection, and exit must not be treated as equivalent states.

Examples of invalid context:
- a specific bugbot finding;
- a specific regression test;
- a specific file path;
- a command-only decision rule;
- a long case narrative;
- a rule that belongs in `rules.design`, `opsx-classify-bug`, or `opsx-verify`.

Case 6: both command and rule already exist, but the bug still passed

Do not automatically add more text.

First diagnose:

- Was the command too vague?
- Was the rule too generic?
- Was there no template field for the rule to land in?
- Did verify fail to check it?
- Was the missing piece actually domain context?
- Was the prompt bundle too large and the agent ignored lower-priority context?

Then propose either:

- strengthen one existing command check;
- strengthen one existing artifact rule;
- replace a weak line with a sharper one;
- add a missing template field;
- add a verify check;
- add a small context line only if the missing model is cross-workflow.

Net growth should be <= 300 chars unless explicitly justified.

## Context rules

Context is the last broad layer, not a dumping ground.

MUST consider context only when at least one is true:

- the same missed model appears in 2+ workflows;
- the same missed model affects 2+ artifact types;
- local command/rule/template text would become duplicated without a shared context line;
- the missing knowledge is stable WB Sky domain or architecture context.

MUST NOT add context for:

- a one-off bug;
- a specific implementation path;
- a temporary workaround;
- a specific test case;
- a command-only procedure;
- a quality criterion that belongs in artifact rules;
- a required field that belongs in a template.

Context addition budget:

- max 250 added chars;
- max 1 new bullet;
- prefer replacing or merging with existing nearby context;
- if similar context already exists, strengthen it instead of adding a new line;
- if context would require more than 250 chars, return `needs_human_decision`.

Relationship between rules and context:

- Rules do not automatically flow into context.
- Context may be created only as a compact abstraction of repeated local rules or repeated agent failures.
- If a local rule is only useful for one command or one artifact type, keep it local.
- If a local rule becomes repeated across commands/artifacts, propose a context line and simplify future local wording.

## Learning Patch size budget

A Learning Patch is the minimum base update after one bug.

Default hard limits:

- one missed invariant only;
- max 2 target files;
- max 700 added chars;
- max 3 new bullets;
- no unrelated cleanup;
- no broad rewrite;
- no new command unless the user explicitly requested this command creation task.

Context exception:

- max 3 target files only if the user explicitly approves a context addition together with local command/rule/template changes;
- max 900 added chars total;
- context part max 250 chars;
- must explain why two files are insufficient.

Size classification:

- <= 500 added chars: OK
- 501–900 added chars: WARN, justify why needed
- > 900 added chars: STOP, propose separate optimization or redesign task

If the patch exceeds the limit, return `needs_human_decision`.

## PLAN mode

Default mode is PLAN ONLY / READ-ONLY.

Steps:

1. Parse the Bug Learning Packet.
2. Identify the missed invariant.
3. Inspect only relevant workflow-base files.
4. Determine whether the miss is:
   - wrong command reasoning;
   - missing artifact rule;
   - missing template field;
   - missing verify check;
   - missing project/domain context;
   - existing rule ignored;
   - not enough evidence.
5. Check whether a relevant rule/check/field/context line already exists.
6. Decide the smallest valid Learning Patch.
7. Estimate files touched and added chars.
8. Do not edit files.

Output format:

Verdict:
- learn_patch / no_change / needs_human_decision

Checked:
- command files:
- context:
- artifact rules:
- templates:
- verify workflow:
- guard config:

Diagnosis:
- missed invariant:
- wrong command reasoning:
- missing artifact rule:
- missing template field:
- missing verify check:
- missing context:
- existing rule ignored:

Existing base evidence:
- command:
- context:
- rule:
- template:
- verify:

Routing decision:
- command target:
- rule target:
- template target:
- verify target:
- context target:
- why these targets:
- why not more:

Proposed Learning Patch:
- target files:
- exact additions:
- replacements, if any:
- added chars estimate:
- context chars estimate:
- why not more:

GO packet:
- approved target files:
- exact additions:
- max files touched:
- max added chars:
- forbidden files:
- verification commands:

Risks:
- risk:
- mitigation:

Stop conditions:
- condition:

## GO mode

GO mode is active only when the user explicitly invokes:

- `/opsx-learn-from-bug:GO`
- `/opsx-learn-from-bug GO`

GO mode must apply only an approved Learning Patch from the previous PLAN output.

Before editing:

1. Re-read the approved target files.
2. Confirm target lines are still relevant.
3. Confirm max files touched <= 2 unless the approved patch explicitly uses the context exception.
4. Confirm estimated added chars <= 700 unless the approved patch explicitly uses the context exception.
5. Confirm context addition, if any, is <= 250 chars and max 1 bullet.
6. Confirm no forbidden files are needed.
7. If any condition fails, stop.

Allowed GO behavior:

- apply only the approved additions/replacements;
- keep edits minimal;
- preserve existing structure and style;
- do not optimize neighboring text;
- do not rewrite unrelated sections.

After editing, run:

- `poetry run python tools/openspec/openspec_guard.py --strict`
- `git diff --check`

If tests or guard commands are unavailable, report exactly what is missing.

GO output format:

Verdict:
- applied / blocked / needs_human_decision

Changed files:
- file:

Patch summary:
- missed invariant:
- command update:
- context update:
- rule update:
- template update:
- verify update:
- added chars:
- context chars:

Verification:
- guard:
- diff check:

Diff summary:
- file:
- lines changed:

Risks:
- risk:

Stop conditions triggered:
- condition:

## Required behavior

MUST keep the patch scoped to one missed invariant.

MUST prefer exact, enforceable wording over explanatory prose.

MUST use MUST / MUST NOT / SHOULD only for artifact rules.

MUST write command additions as decision checks, not artifact-quality rules.

MUST write template additions as fields/sections, not long instructions.

MUST write context additions as compact stable project/domain model, not commands or rules.

MUST NOT add the same sentence to command, context, and config rules.

MUST NOT turn one bug into broad context unless the missing model is cross-workflow.

MUST NOT update product specs or active changes.

MUST NOT optimize current oversized files during this command.

MUST NOT continue if the right target is unclear.

## Example routing

Bug learning:

- Finding: setup-stage missing restore was classified as confirmed bug.
- Correct invariant: restore requires a stored non-empty snapshot; setup creates the snapshot; active hold protects it.
- Broader model: stateful WB Sky features may have lifecycle baselines.

Patch:

- command update:
  - target: `.cursor/commands/opsx-classify-bug.md`
  - addition: Require proof of non-empty snapshot/baseline reachability before classifying setup-stage missing restore/check as confirmed bug.

- artifact rule or template update:
  - target: `openspec/config.yaml` rules.design or `openspec/schemas/**/templates/design.md`
  - addition: Stateful snapshot/baseline design MUST define setup stage, baseline creation point, active protection phase, cleanup/exit behavior, and forbidden re-entry transitions.

- context update:
  - target: `openspec/config.yaml` context
  - addition only if repeated across workflows: Stateful WB Sky features often use lifecycle baselines: setup creates baseline, active protects it, exit clears or archives it.

Only apply context if the missing lifecycle-baseline model is useful outside this one bug. If this is one isolated finding, keep the patch local to command/rule/template.
