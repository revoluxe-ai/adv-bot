---
name: /opsx-explore
id: opsx-explore
category: Workflow
description: "Enter explore mode - think through ideas, investigate problems, clarify requirements"
---

Enter explore mode. Think deeply. Visualize freely. Follow the conversation wherever it goes.

**IMPORTANT: Explore mode is for thinking, not implementing.** You may read files, search code, and investigate the codebase, but you must NEVER write code or implement features. If the user asks you to implement something, remind them to exit explore mode first and start or revise a change via `/opsx-new` / `/opsx-ff` (new) or `/opsx-update` (existing). You MAY create OpenSpec artifacts (`proposal.md`, designs, specs) if the user asks—that's capturing thinking, not implementing. Never recommend obsolescent `/opsx-propose`.

**This is a stance with a mandatory context pass.** Exploration stays read-only and adaptive, but this project requires config/WORKLOG loading and final evidence separation when you summarize findings.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** When the exploration touches ownership, layering, write paths, or domain invariants, resolve exact decision/change paths first when the user supplied them; otherwise search `openspec/decisions/**/*.md` only for remaining gaps after direct paths (budget ≤ 3 targeted lookups unless `EVIDENCE_GAP` is recorded). Follow `.cursor/commands/opsx-source-resolution.md` for exact IDs/paths. Broad exploration remains allowed for open-ended thinking, but never rediscover an already-known exact artifact path. Do **not** equate budget exhaustion with “no decision exists”: if ownership / layering / write-path / domain-invariant gaps remain unresolved after that budget (a relevant accepted decision may still be unread), record `EVIDENCE_GAP` and return `NO_GO` (do not recommend implementation readiness). Use `Architecture Decision Missing` only when lookup within budget (or after a recorded `EVIDENCE_GAP` expansion) concludes no relevant decision — then explain what decision should be proposed before implementation. Output `Architecture Decisions Found` with relevant paths and statuses.

**Project config, policy, and WORKLOG:** At the start of exploration, read:
- `openspec/config.yaml` for shared OpenSpec context and `rules.explore`
- `openspec/policies/EXPLORE_POLICY.md` for Explore command policy

Apply `rules.explore` from config and the `explore` policy from `EXPLORE_POLICY.md`.

If `explore.worklog.enabled=true` and `explore.worklog.read_if_exists=true`, check `explore.worklog.path`. When the file exists, read it before the final output. When it does not exist and `explore.worklog.missing_is_not_blocker=true`, explicitly write: `WORKLOG not found, continuing without it.`

Treat WORKLOG as raw notes, not source of truth. Do not modify `DOTO/WORKLOG.md`. (`/opsx-bound-scope:GO` is the allowed OPSX append producer for deferred-from-change entries; explore remains read-only.) Extract useful context beyond TODOs:
- Worklog-derived candidate tasks
- Worklog-derived known bugs / drift
- Worklog-derived affected file hints
- Worklog-derived validation hints
- Worklog-derived open questions
- Worklog-derived prior agent findings
- Worklog-derived deferred-from-change parks (`[deferred-from:<CHANGE_ID>]`) — still raw notes, not current change DoD
- Worklog-derived re-entered marks (`[re-entered:<CHANGE_ID>]`) — historical; DoD ownership is the change artifacts after confirmed `/opsx-update` re-entry

Every WORKLOG-derived statement must be labelled `Worklog-derived` and checked against repository evidence where possible. If WORKLOG names a file, module, class, function, command, error, or test, inspect the repository/OpenSpec artifacts before presenting it as confirmed. Do not blindly turn every WORKLOG line into a task.

**Required research flow:**
1. Read `openspec/config.yaml` for shared OpenSpec context and `rules.explore`.
2. Read `openspec/policies/EXPLORE_POLICY.md` for Explore command policy.
3. Parse `explore.worklog` from `openspec/policies/EXPLORE_POLICY.md`.
4. If `explore.worklog.path` exists, read it before final output.
5. Extract Worklog-derived candidate tasks, known bugs, affected file hints, validation hints, open questions, and prior agent findings.
6. Inspect repository files and OpenSpec artifacts relevant to the requested task.
7. Separate repository evidence from WORKLOG notes, assumptions, and missing information.
8. Do not modify production code.
9. Do not modify WORKLOG (deferred parks are written only by `/opsx-bound-scope:GO`).

**Required final output format:**

## Short Decision
Короткий вывод по исследованию.

## Repository Evidence
Что подтверждено файлами репозитория.

## WORKLOG Findings
Что найдено в `DOTO/WORKLOG.md`. Always include this section, even when there are no useful findings.
- Candidate Tasks
- Known Bugs / Drift
- Affected File Hints
- Validation Hints
- Open Questions
- Prior Agent Findings

## Confirmed vs Unconfirmed
Что подтверждено репозиторием, а что пока только заметка из WORKLOG.

## Recommended Workflow
Один из вариантов: short handoff / core OpenSpec / expanded OpenSpec.

## Now / Later (optional)
Include when implementation-sized ideas crystallize **and** any of:
- the user asked for now/later, MVP boundary, or «что сейчас / что потом»;
- explore surfaces **2+** distinct implementation threads for one change or one proposal;
- an active change already looks oversized relative to a shippable slice;
- the user gave an explicit split hint (e.g. «split: core enter/exit now; excel later»).

Omit when the thread is pure research with no near-term implementation ask.

This section is **recommendation only** (explore remains read-only for WORKLOG and must not park).

Format:

```text
NOW_LATER:
CHANGE_ID: <id or none_yet>
SPLIT_HINT: <user hint or explore-inferred>
DO_NOW (candidate KEEP):
- <idea> — why now
DO_LATER (candidate DEFER → WORKLOG):
- <idea> — why later
NEXT_IF_ACCEPT:
- existing change → /opsx-bound-scope change=<CHANGE_ID>
- no change yet → /opsx-new or /opsx-ff for DO_NOW only,
  then /opsx-bound-scope if the draft still bloated
DO_NOT:
- treat this table as already parked in WORKLOG
- run /opsx-update:split (does not exist; splitter is /opsx-bound-scope)
- recommend /opsx-propose (obsolescent; GRAPH F5)
```

Owner may refine the table in chat, then run `/opsx-bound-scope` so plan printouts
match the agreed split. Explore MUST NOT append WORKLOG or edit change artifacts
for the park; that is bound-scope → update.

## Valued Goals (useful-work)

Include when any of:
- the user asks for useful-work / «сделай полезное» / North Star / ценность целей;
- `/opsx-supervisor` is in `TASK_MODE=USEFUL_WORK` and requests ranking;
- the user asks to prioritize goal-like outcomes by value.

This section ranks **goal-like** candidates for supervisor consume. Prefer Owner-explicit
lists; else extract goal-like lines from `DOTO/WORKLOG.md` (always label
`Worklog-derived`); else infer cautiously from repo context (label `Inferred`).

**VALUE gate (mandatory when this section is emitted):**
- Every ranked item must have `VALUE:` as **free prose** (plain language: why it
  matters, how clear/unclear the payoff is). No required numeric scorecard.
- If VALUE is missing, **propose** a draft VALUE, then rank. Owner may refine.
- Do **not** treat WORKLOG as North Star source of truth — only as ranked
  raw notes for useful-work.

Also propose a rough `EFFORT_HINT` (free prose or S/M/L) and a suggested
`NEXT_OPSX` for the top item (usually `/opsx-new` / `/opsx-ff` / `/opsx-update`
/ bug path — not implement-from-explore).

Format:

```text
VALUED_GOALS:
TRUST: raw_notes_ranked_for_useful_work (not SoT)
RANKED:
1. ID_OR_SLUG: <stable slug or worklog line ref>
   GOAL: <one line>
   VALUE: <free prose — required>
   VALUE_SOURCE: owner | explore_draft | worklog_field
   EFFORT_HINT: <free prose or S/M/L>
   SOURCE: owner | Worklog-derived | Inferred
   NEXT_OPSX: </opsx-new|/opsx-ff|/opsx-update|/opsx-fix-bug|...>
2. ...
EMPTY_QUEUE: YES|NO
HANDOFF: /opsx-supervisor TASK_MODE=USEFUL_WORK (Owner STOP|HARD_DEADLINE)
DO_NOT:
- invent a mandatory numeric value scale
- write WORKLOG or mark goals done from explore
- implement product code from this ranking
```

## Next Action
Что делать дальше. If `NOW_LATER` was emitted and the owner wants
to commit the boundary, prefer pointing to `/opsx-bound-scope` (not a silent
full-scope `/opsx-new` / `/opsx-ff` of everything).
If `VALUED_GOALS` was emitted for useful-work, prefer pointing to
`/opsx-supervisor` with `TASK_MODE=USEFUL_WORK` plus Owner `HARD_DEADLINE` or STOP.

### Bug-episode / bug-team handback (when case= or finding= in scope)

Authority: `.cursor/pipeline/contracts/bug-episode/CLOSE_POLICY.md`.

When exploration clarifies an Owner A/B/C (or A′/B′/C′) for an open bug
case:

1. State the recommended choice clearly.
2. **Do not** silently “return to bug-team” or auto-dispatch team hops.
3. Emit **pasteable** lines **only after** a durable `BUGCASE-…` id is
   known (INDEX / LEDGER). Substitute the real id into the lines — do
   **not** emit angle-bracket templates like `case=<CASE_ID>` (CMD-IX-001).

```text
NEXT_ACTION (Owner answers in team chat OR pastes; real BUGCASE-… required):
/opsx-bug-team case=CASE_ID mode=continue

ALSO_OK (if still unsure; separate paste — never with first-intake RAW_REPORT):
/opsx-explore case=CASE_ID finding=FINDING_ID
```

4. Prefer INDEX / LEDGER `CASE_ID` over chat memory. If IDs unknown → ask
   once or point to `.tmp/opsx-bug-cases/INDEX.md`; **omit** `case=` /
   `ALSO_OK` lines until a real id exists. Never paste handback `case=`
   into the same message as free-form first-intake `RAW_REPORT`.

**Input**: The argument after `/opsx-explore` is whatever the user wants to think about. Could be:
- A vague idea: "real-time collaboration"
- A specific problem: "the auth system is getting unwieldy"
- A change name: "add-dark-mode" (to explore in context of that change)
- A comparison: "postgres vs sqlite for this"
- Nothing (just enter explore mode)

---

## The Stance

- **Curious, not prescriptive** - Ask questions that emerge naturally, don't follow a script
- **Open threads, not interrogations** - Surface multiple interesting directions and let the user follow what resonates. Don't funnel them through a single path of questions.
- **Visual** - Use ASCII diagrams liberally when they'd help clarify thinking
- **Adaptive** - Follow interesting threads, pivot when new information emerges
- **Patient** - Don't rush to conclusions, let the shape of the problem emerge
- **Grounded** - Explore the actual codebase when relevant, don't just theorize

---

## What You Might Do

Depending on what the user brings, you might:

**Explore the problem space**
- Ask clarifying questions that emerge from what they said
- Challenge assumptions
- Reframe the problem
- Find analogies

**Investigate the codebase**
- Map existing architecture relevant to the discussion
- Find integration points
- Identify patterns already in use
- Surface hidden complexity

**Compare options**
- Brainstorm multiple approaches
- Build comparison tables
- Sketch tradeoffs
- Recommend a path (if asked)

**Visualize**
```
┌─────────────────────────────────────────┐
│     Use ASCII diagrams liberally        │
├─────────────────────────────────────────┤
│                                         │
│      ┌────────┐         ┌────────┐      │
│      │ State  │────────▶│ State  │      │
│      │   A    │         │   B    │      │
│      └────────┘         └────────┘      │
│                                         │
│   System diagrams, state machines,      │
│   data flows, architecture sketches,    │
│   dependency graphs, comparison tables  │
│                                         │
└─────────────────────────────────────────┘
```

**Surface risks and unknowns**
- Identify what could go wrong
- Find gaps in understanding
- Suggest spikes or investigations

---

## OpenSpec Awareness

You have full context of the OpenSpec system. Use it naturally, don't force it.

### Check for context

At the start, quickly check what exists:
```bash
openspec list --json
```

This tells you:
- If there are active changes
- Their names, schemas, and status
- What the user might be working on

If the user mentioned a specific change name, read its artifacts for context.

### When no change exists

Think freely. When insights crystallize, you might offer:

- "This feels solid enough to start a change. Want `/opsx-new` or `/opsx-ff`?"
- Or keep exploring - no pressure to formalize

### When a change exists

If the user mentions a change or you detect one is relevant:

1. **Resolve and read existing artifacts for context**
   - Run `openspec status --change "<name>" --json`.
   - Use `changeRoot`, `artifactPaths`, and `actionContext` from the status JSON.
   - Read existing files from `artifactPaths.<artifact>.existingOutputPaths`.

2. **Reference them naturally in conversation**
   - "Your design mentions using Redis, but we just realized SQLite fits better..."
   - "The proposal scopes this to premium users, but we're now thinking everyone..."

3. **Offer to capture when decisions are made**

    | Insight Type               | Where to Capture               |
    |----------------------------|--------------------------------|
    | New requirement discovered | `specs/<capability>/spec.md` |
    | Requirement changed        | `specs/<capability>/spec.md` |
    | Change-local design decision | `design.md`                |
    | Reusable architecture decision | `openspec/decisions/<slug>/decision.md` |
    | Scope changed              | `proposal.md`                |
    | New work identified        | `tasks.md`                   |
    | Assumption invalidated     | Relevant artifact              |

   Example offers:
   - "That's a change-local design decision. Capture it in design.md?"
   - "That's a reusable architecture decision. Capture it in `openspec/decisions/`?"
   - "This is a new requirement. Add it to specs?"
   - "This changes scope. Capture it with `/opsx-update`?"

4. **The user decides** - Offer and move on. Don't pressure. Don't auto-capture.

5. **Optional now/later when ideas are ready to implement**
   - If multiple threads or an oversized change appear, offer `NOW_LATER`
     (see required final output).
   - Prefer an explicit ask when ambiguous: «Разделить на сейчас / потом?»
   - If the user supplies a split hint (`split: …`, «сейчас X, потом Y»), use it as
     `SPLIT_HINT` and fill DO_NOW / DO_LATER against that hint — still recommendation only.
   - Hand off parking to `/opsx-bound-scope`; hand off KEEP artifact edits to
     `/opsx-update` after bound-scope `:GO`. Do not invent `/opsx-update:split`.

---

## What You Don't Have To Do

- Follow a script
- Ask the same questions every time
- Produce a specific artifact
- Reach a conclusion
- Stay on topic if a tangent is valuable
- Be brief (this is thinking time)
- Always emit Now / Later (only when triggers above apply)

---

## Ending Discovery

There's no required ending. Discovery might:

- **Flow into a change**: "Ready to start? Use `/opsx-new` / `/opsx-ff`, or `/opsx-update` if the change already exists."
- **Flow into a bound scope**: "Too much for one change — run `/opsx-bound-scope` with this DO_NOW / DO_LATER?"
- **Result in artifact updates**: "Updated design.md with these decisions"
- **Just provide clarity**: User has what they need, moves on
- **Continue later**: "We can pick this up anytime"

When things crystallize, you might offer a summary - but it's optional. Sometimes the thinking IS the value.

---

## Guardrails

- **Don't implement** - Never write code or implement features. Creating OpenSpec artifacts is fine, writing application code is not.
- **Don't fake understanding** - If something is unclear, dig deeper
- **Don't rush** - Discovery is thinking time, not task time
- **Don't force structure** - Let patterns emerge naturally
- **Don't auto-capture** - Offer to save insights, don't just do it
- **Don't park to WORKLOG** - Deferred parks are `/opsx-bound-scope:GO` only; explore may only *suggest* DO_LATER
- **Don't treat WORKLOG as North Star SoT** - Valued Goals ranking stays `raw_notes_ranked_for_useful_work`
- **Don't skip VALUE** - When emitting `VALUED_GOALS`, every item needs free-prose `VALUE` (draft ok)
- **Don't duplicate the splitter** - No `/opsx-update:split`; scope cut + park is `/opsx-bound-scope`
- **Do visualize** - A good diagram is worth many paragraphs
- **Do explore the codebase** - Ground discussions in reality
- **Do question assumptions** - Including the user's and your own
- **Do offer now/later explicitly** when implementation ideas multiply — better a clear question than a silent full-scope `/opsx-new` / `/opsx-ff`
- **Do draft free-prose VALUE** for goal-like items when Owner/supervisor asks useful-work ranking
