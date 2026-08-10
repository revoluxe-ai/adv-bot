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

## Not the process consult desk

Relationship questions, ownership ambiguity, and triage of “an admin/pipeline
command behaved oddly” before knowing whether to fix, redesign, or design a
new command belong to `/opsx-admin-command-consult`.

Use this command when the human already wants pipeline redesign / usability
analysis / improvement options — not as a general OPSX meta front-door.

------------------------------------------------------------------------

# TOPIC_INTENT gate (mandatory — before Modes / transcript search)

**Defect class:** sticky prior-turn topic hijacks a new Owner ask
(CMD-ANALYZE-PIPELINE-TOPIC-STICKY-001).

Before any transcript search, chat-history framing, `CURRENT_GRAPH` build, or
`IMPROVEMENT_PROPOSAL`, resolve exactly one:

```text
TOPIC_INTENT: PRODUCT_BRIEF | PROCESS_PIPELINE | AMBIGUOUS
```

Rules:

1. Decide from the **current** user message first. Prior turns are hints only;
   they MUST NOT become the default topic.
2. Forbidden: treat «обучение» / learning / promote / DEFERRED from an earlier
   turn as the topic of a new ask that never names learning/process.
3. If `AMBIGUOUS` (e.g. bare «задача», «найди чаты где я объяснял») → ask
   **one** narrow question and stop; do not answer yet:

   ```text
   PRODUCT_BRIEF (продуктовая постановка / North Star / evolution)
   или PROCESS_PIPELINE (команды, gates, обучение process, UX пайплайна)?
   ```

4. `PRODUCT_BRIEF` → this command MUST NOT reframe as learning/promote
   analysis. Locate Owner product briefs / cite durable product SoT
   (`openspec/evolution/**` when applicable) or emit `WRONG_SURFACE` with
   pasteable next: `/opsx-evolution` or `/opsx-explore`. Learning is out of
   scope unless Owner explicitly names it in the current message.

5. `PROCESS_PIPELINE` → proceed with Modes below (process design only). Do
   not rewrite product domain specs as the primary answer.

Emit `TOPIC_INTENT:` in the first status block of every run.

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
-   risks;
-   `REMEDY_CLASS` (required — see Class vs local remedy).

## Class vs local remedy (mandatory)

Every `IMPROVEMENT_OPTION` MUST declare exactly one:

| `REMEDY_CLASS` | Meaning |
|---|---|
| `LOCAL_SYMPTOM` | Narrow patch to one command/gate symptom; does not create DONE |
| `CLASS_KERNEL` | Recurring class failure (ownership, DONE authority, lifecycle meaning, durable handoff) |
| `AUTHORITY_ALREADY_EXISTS` | Durable contract already covers the class; need enforce/hand-off, not a new parallel gate |

When evidence shows a class/kernel gap (especially DONE = procedural greenness
vs Owner meaning / lifecycle / side-effect proof):

1. Prefer citing exact durable paths already in-repo. Default authority for
   product DONE meaning:
   `.cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md`
   (MEANING_LOCK ∧ LIFECYCLE_COVERAGE ∧ SIDE_EFFECT_PROOF).
2. `RECOMMENDED_OPTION` MUST be `CLASS_KERNEL` or `AUTHORITY_ALREADY_EXISTS`
   when such evidence is present — not a menu of new soft gates.
3. `NEXT_ACTION` / `CLASS_HANDOFF` MUST prefer:
   - `/opsx-admin-command-promote-process-lesson` (transferable process class),
     and/or
   - `/opsx-admin-command-design-command` with `EXTEND_EXISTING` on the cited
     authority — not inventing a parallel local gate bundle as the primary fix.
4. **Forbidden as primary recommendation** when class gap is evidenced:
   inventing soft-gate option bundles that duplicate Product Acceptance pillars
   (extra MEANING / LIFECYCLE / SIDE_EFFECT checklists sold as new DONE gates).
5. `LOCAL_SYMPTOM` options may appear only as **secondary**, explicitly labeled
   non-kernel, and MUST NOT claim they create archive-eligible DONE.

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
run /opsx-update   # existing change
# or /opsx-new | /opsx-ff when no change exists
# never /opsx-propose (obsolescent; GRAPH F5)
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

REMEDY_CLASS:
LOCAL_SYMPTOM | CLASS_KERNEL | AUTHORITY_ALREADY_EXISTS

CURRENT_FLOW:

PROBLEM:

HUMAN_IMPACT:

PROPOSED_FLOW:

BEHAVIOR_CHANGE:

COGNITIVE_LOAD_CHANGE:
lower | same | higher

RISK:

FILES_AFFECTED:

DURABLE_AUTHORITY_CITED:
(exact path(s); required for CLASS_KERNEL and AUTHORITY_ALREADY_EXISTS;
 prefer .cursor/pipeline/contracts/PRODUCT_ACCEPTANCE.md when DONE/meaning)

CLASS_HANDOFF:
/opsx-admin-command-promote-process-lesson
| /opsx-admin-command-design-command EXTEND_EXISTING
| none (LOCAL_SYMPTOM secondary only)

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
(each option MUST include REMEDY_CLASS)

REMEDY_CLASS_SUMMARY:
LOCAL_SYMPTOM: N
CLASS_KERNEL: N
AUTHORITY_ALREADY_EXISTS: N

DURABLE_AUTHORITY_CITED:
(exact path(s) for class/authority options; or none)

CLASS_HANDOFF:
(command + target authority; or none if only LOCAL_SYMPTOM)

RECOMMENDED_OPTION:

REASON:

REGRESSION_RISKS:

NEXT_ACTION:
(when class/authority evidenced: promote-process-lesson and/or
 design-command EXTEND_EXISTING — not a primary local soft-gate menu)
```

------------------------------------------------------------------------

# Self-review

Before returning:

-   `TOPIC_INTENT` resolved from the current user message and emitted;
    AMBIGUOUS did not get a full answer; PRODUCT_BRIEF was not answered as
    learning/promote; sticky prior-turn «обучение» was not used as default.
-   Do not optimize only for AI execution.
-   Do not reduce complexity without considering clarity.
-   Do not invent states without evidence.
-   Do not propose changes without explaining human impact.
-   Keep analysis separate from implementation.
-   Every IMPROVEMENT_OPTION has REMEDY_CLASS.
-   Class/authority evidence ⇒ RECOMMENDED_OPTION is not a new parallel soft-gate
    bundle; DURABLE_AUTHORITY_CITED and CLASS_HANDOFF are filled.
-   LOCAL_SYMPTOM options do not claim they create DONE.
