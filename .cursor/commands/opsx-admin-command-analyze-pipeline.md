# /opsx-admin-command-analyze-pipeline

## Purpose

Analyze and improve the OpenSpec/OPSX pipeline from a human-centered
perspective.

The goal is not to minimize the number of commands.

The goal is to create a pipeline that is:

-   understandable;
-   predictable;
-   controllable by a person;
-   safe during changes;
-   usable by a new developer without historical context.

This command analyzes process design, not production code.

## Not the operator navigator

This command builds an **ephemeral** `CURRENT_GRAPH` for analysis and
improvement proposals only. It is always `READ_ONLY` and never persists a
traversal map.

Day-to-day navigation of the **as-is** not-admin pipeline (including known
flaws), and materialization of the approved graph via `UPDATE` / `UPDATE GO`,
belongs exclusively to `/opsx-pipeline`.

Do not treat this command’s chat graph as the durable operator map.

------------------------------------------------------------------------

# Core evaluation question

Ask:

> Could a new developer understand and safely operate this pipeline
> after one week, without studying the history of how it was created?

If not, identify the source of uncertainty.

------------------------------------------------------------------------

# Modes

## PIPELINE_ANALYSIS

Build the current pipeline model.

Analyze:

-   commands;
-   states;
-   transitions;
-   gates;
-   artifacts;
-   ownership;
-   human decision points.

## IMPROVEMENT_PROPOSAL

Create improvement options.

Do not change files.

Show:

-   current behavior;
-   problem;
-   proposed behavior;
-   human impact;
-   risks.

## REGRESSION_PIPELINE_REVIEW

Check whether a pipeline change reduced clarity, safety, or
predictability.

------------------------------------------------------------------------

# Safety boundary

Always start:

``` text
READ_ONLY
```

Never:

-   edit files;
-   create patches;
-   change commands;
-   change decisions;
-   modify tasks;
-   commit;
-   push;
-   run implementation.

Analysis is not approval.

------------------------------------------------------------------------

# Tool I/O contract (mandatory — hang prevention)

Follow `.cursor/commands/opsx-execution-preflight.md` **Read / tool I/O budgets**
and `.cursor/commands/opsx-source-resolution.md`.

- Prefer Grep / filename inventory over full-file Read.
- Parallel Read: max **2**; never open the full `opsx-*.md` set in one turn.
- Large process files: section Read (`limit`/`offset` ≤ 120) or Grep ± context.
- Build the pipeline graph from inventory + targeted hits, not from dumping
  every command body into context.
- Do not preload `opsx-learn-from-bug.md` / `opsx-admin-command-design-command.md` /
  `opsx-fix-bug.md` unless Grep shows they are required for the active mode.
- Cap substantive section-Reads per run at **8** for PIPELINE_ANALYSIS /
  REGRESSION_PIPELINE_REVIEW; IMPROVEMENT_PROPOSAL uses only files already
  evidenced as problem loci.
- Read stall/timeout → stop stacking Reads; return `BLOCKED` / `EVIDENCE_GAP`
  rather than hanging.

------------------------------------------------------------------------

# Human-centered pipeline criteria

## 1. Process clarity

Evaluate whether a person can quickly understand:

-   current position;
-   next step;
-   purpose of the step;
-   expected result;
-   decision owner;
-   recovery path after failure.

Defect example:

A user must read many files and remember hidden history to know the next
command.

------------------------------------------------------------------------

## 2. Cognitive load

Detect when the pipeline requires a person to:

-   remember hidden dependencies;
-   manually discover command order;
-   guess the next command;
-   understand internal identifiers instead of meaningful states.

A good pipeline explains:

``` text
what is happening
why it is happening
what happens next
```

------------------------------------------------------------------------

## 3. Explicit states

Every important stage should define:

``` text
INPUT:
ACTION:
OUTPUT:
SUCCESS_CRITERIA:
NEXT_STEP:
OWNER:
```

Avoid:

-   implicit agreements;
-   hidden transitions;
-   chat history dependencies.

------------------------------------------------------------------------

## 4. Change safety

Check whether a person understands:

-   analysis vs modification;
-   safe vs dangerous operations;
-   approval points;
-   possible impact.

Dangerous operations must be visibly separated.

------------------------------------------------------------------------

## 5. Command UX

Evaluate commands as interfaces.

Bad:

``` text
Run several commands.
Read multiple files.
Guess the next action.
```

Good:

``` text
Run command.
Receive status.
Choose next allowed action.
```

------------------------------------------------------------------------

## 6. Error UX

Errors must explain:

-   what failed;
-   why it failed;
-   where it failed;
-   what to check;
-   what action resolves it.

Bad:

``` text
FAILED
```

Good:

``` text
VERIFY_BLOCKED

Reason:
missing decision approval

Check:
openspec/decisions/...

Next:
run /opsx-propose
```

------------------------------------------------------------------------

## 7. Human-first, not AI-only

Evaluate usability for:

-   developer;
-   new team member;
-   reviewer;
-   future maintainer.

A pipeline optimized only for agents is a design defect.

------------------------------------------------------------------------

# Pipeline graph extraction

For each command in the inventory, fill the template below from **filename +
Grep hits + at most one bounded section Read** when a field is still unknown.
Unopened commands: mark fields `NOT_OPENED_BUDGET` — do not invent.

Build:

## States

Examples:

-   change_created;
-   specification_ready;
-   decision_resolved;
-   implementation_done;
-   verification_passed;
-   archive_ready.

## Commands

For each command:

``` text
command:

purpose:

input_state:

output_state:

artifact_created:

artifact_consumed:

decision_required:

human_action:

next_step:
```

## Transitions

Represent:

``` text
state
 |
command
 |
state
```

------------------------------------------------------------------------

# Pipeline defects

Find:

## Hidden transition

A command depends on undocumented previous actions.

## Ambiguous next step

A user cannot determine what command/action comes next.

## State without owner

A lifecycle state exists but nobody owns the decision.

## Multiple competing paths

Two workflows reach the same state differently without clear rules.

## Gate bypass

A safety check exists but another path skips it.

## Invisible dependency

A command requires knowledge not visible in its output.

## Excessive cognitive load

The workflow is technically correct but requires too much memory/search.

## Human recovery failure

After an error, the user cannot understand how to continue safely.

------------------------------------------------------------------------

# Improvement principles

When proposing changes, optimize for:

## Reduced uncertainty

Prefer:

-   explicit states;
-   visible next actions;
-   clear ownership;
-   fewer hidden assumptions.

## Not just fewer commands

Do not remove commands only to reduce count.

A longer pipeline can be better if it is clearer.

## Stable mental model

The user should be able to predict:

-   what command does;
-   what appears after it;
-   what decision is required.

------------------------------------------------------------------------

# Improvement proposal format

``` text
PIPELINE_IMPROVEMENT_PROPOSAL:

CURRENT_FLOW:

PROBLEM:

HUMAN_IMPACT:

PROPOSED_FLOW:

BEHAVIOR_CHANGE:

COGNITIVE_LOAD_CHANGE:
lower | same | higher

RISK:

FILES_AFFECTED:

OWNER_DECISION_REQUIRED:
```

------------------------------------------------------------------------

# Final output

Return:

``` text
STATUS:
PIPELINE_ANALYSIS_COMPLETE | BLOCKED

MODE:

PIPELINE_SUMMARY:

CURRENT_GRAPH:

HUMAN_USABILITY_SCORE:

PROBLEMS_FOUND:

IMPROVEMENT_OPTIONS:

RECOMMENDED_OPTION:

REASON:

REGRESSION_RISKS:

NEXT_ACTION:
```

------------------------------------------------------------------------

# Self-review

Before returning:

-   Do not optimize only for AI execution.
-   Do not reduce complexity without considering clarity.
-   Do not invent states without evidence.
-   Do not propose changes without explaining human impact.
-   Keep analysis separate from implementation.
