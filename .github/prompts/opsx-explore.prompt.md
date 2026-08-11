---
description: Enter explore mode - think through ideas, investigate problems, clarify requirements
---

Enter explore mode. Think deeply. Visualize freely. Follow the conversation wherever it goes.

**IMPORTANT: Explore mode is for thinking, not implementing.** You may read files, search code, and investigate the codebase, but you must NEVER write code or implement features. If the user asks you to implement something, remind them to exit explore mode first and create a change proposal. You MAY create OpenSpec artifacts (proposals, designs, specs) if the user asks—that's capturing thinking, not implementing.

**This is a stance with a mandatory context pass.** Exploration stays read-only and adaptive, but this project requires config/WORKLOG loading and final evidence separation when you summarize findings.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** When the exploration touches ownership, layering, write paths, or domain invariants, search `openspec/decisions/**/*.md` before recommending placement. Output `Architecture Decisions Found` with relevant paths and statuses. If none are relevant but the topic needs architecture placement, output `Architecture Decision Missing` and explain what decision should be proposed before implementation.

**Project config, policy, and WORKLOG:** At the start of exploration, read:
- `openspec/config.yaml` for shared OpenSpec context and `rules.explore`
- `openspec/policies/EXPLORE_POLICY.md` for Explore command policy

Apply `rules.explore` from config and the `explore` policy from `EXPLORE_POLICY.md`.

If `explore.worklog.enabled=true` and `explore.worklog.read_if_exists=true`, check `explore.worklog.path`. When the file exists, read it before the final output. When it does not exist and `explore.worklog.missing_is_not_blocker=true`, explicitly write: `WORKLOG not found, continuing without it.`

Treat WORKLOG as raw notes, not source of truth. Do not modify `DOTO/WORKLOG.md`. Extract useful context beyond TODOs:
- Worklog-derived candidate tasks
- Worklog-derived known bugs / drift
- Worklog-derived affected file hints
- Worklog-derived validation hints
- Worklog-derived open questions
- Worklog-derived prior agent findings

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
9. Do not modify WORKLOG.
10. If input contains `EVOLUTION_HANDOFF` / `OWNER_INTENT`: treat `OWNER_INTENT`
    as the fixed semantic target. Map Owner terms onto runtime/code under
    separate findings — never replace `OWNER_INTENT`.
11. If Owner↔runtime mapping is ambiguous: emit `UNRESOLVED` /
    `CANDIDATE_MAPPING` and clarify; do **not** rewrite `OWNER_INTENT`.

**OWNER_INTENT authority (when present):**
`explore(OWNER_INTENT, repository)` MUST NOT return a different `OWNER_INTENT`
only because repository evidence supports another technical reading.

**Required final output format:**

When input includes `OWNER_INTENT`, emit this pasteable block **before** the
narrative sections. Copy `OWNER_INTENT` **verbatim**.

```text
EXPLORE_HANDOFF
OWNER_INTENT:
<verbatim copy from EVOLUTION_HANDOFF / input — do not reinterpret>
CURRENT_INCREMENT: <passthrough if present>
IN_SCOPE:
- <passthrough if present>
OUT_OF_SCOPE:
- <passthrough if present>
REPOSITORY_FINDINGS:
- <confirmed file/path/behavior facts>
RUNTIME_MAPPING:
- <Owner/UI term → candidate code/runtime path>
UNRESOLVED:
- <ambiguities / contradictions; empty if none>
CANDIDATE_MAPPING:
- <optional alternate mappings that need Owner confirmation>
```

If `OWNER_INTENT` is absent, skip `EXPLORE_HANDOFF` (backward compatible).

## Short Decision
Короткий вывод по исследованию. When `OWNER_INTENT` is present, stay
consistent with it; technical reframes go under evidence/mapping/unresolved.

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

## Next Action
Что делать дальше.

**Input**: The argument after `/opsx:explore` is whatever the user wants to think about. Could be:
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

- "This feels solid enough to start a change. Want me to create a proposal?"
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
   - "This changes scope. Update the proposal?"

4. **The user decides** - Offer and move on. Don't pressure. Don't auto-capture.

---

## What You Don't Have To Do

- Follow a script
- Ask the same questions every time
- Produce a specific artifact
- Reach a conclusion
- Stay on topic if a tangent is valuable
- Be brief (this is thinking time)

---

## Ending Discovery

There's no required ending. Discovery might:

- **Flow into a proposal**: "Ready to start? I can create a change proposal."
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
- **Don't rewrite OWNER_INTENT** - When present, pass it through verbatim in
  `EXPLORE_HANDOFF`; put code/runtime mappings under findings/mapping/unresolved
- **Don't replace Owner meaning with a plausible code story** without explicit
  Owner correction
- **Do visualize** - A good diagram is worth many paragraphs
- **Do explore the codebase** - Ground discussions in reality
- **Do question assumptions** - Including the user's and your own
