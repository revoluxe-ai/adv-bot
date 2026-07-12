---
name: openspec-verify-change
description: Verify an OpenSpec change against specs, tasks, and architecture decisions. Use when the user wants to validate implementation correctness and placement before archive.
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: Requires openspec CLI.
metadata:
  author: openspec
  version: "1.0"
  generatedBy: "1.6.0"
---

Verify an OpenSpec change after or during implementation.

**Store selection:** If the user names a store (a store is a standalone OpenSpec repo registered on this machine) or the work lives in one, run `openspec store list --json` to discover registered store ids, then pass `--store <id>` on the commands that read or write specs and changes (`new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`). Other commands do not take the flag. Hints printed by commands already carry the flag; keep it on follow-ups. Without a store, commands act on the nearest local `openspec/` root.

**Architecture Decision Lookup:** Verification must check implementation placement against `openspec/decisions/**/*.md` and any proposed decisions in the change `contextFiles.decisions` / `artifactPaths.decisions.existingOutputPaths`, not only behavior and tests. When proposed decisions exist, use `openspec instructions decisions --change "<name>" --json` so `rules.decisions` are applied. Passing tests are not sufficient when placement violates a decision.

**Input**: Optionally specify a change name. If omitted, infer from conversation only when unambiguous; otherwise prompt for selection.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - If ambiguous, run `openspec list --json` and prompt the user to choose

   Always announce: "Verifying change: <name>" and how to override.

2. **Resolve change context**

   Run:
   ```bash
   openspec status --change "<name>" --json
   ```

   Parse `schemaName`, `changeRoot`, `artifactPaths`, and `actionContext`. Use concrete paths from `artifactPaths.<id>.existingOutputPaths`; do not assume artifact names beyond what status reports.

3. **Read planning artifacts**

   Read proposal, design, specs, tasks, optional decisions, and any other existing artifacts reported by status. Extract:
   - Required observable behavior
   - Completed and remaining tasks
   - Declared architecture decision references
   - Ownership and placement claims

4. **Perform Architecture Decision Lookup**

   - Search and read `openspec/decisions/**/*.md`.
   - Read existing proposed decisions from `contextFiles.decisions` or `artifactPaths.decisions.existingOutputPaths`, if any.
   - Output `Architecture Decisions Found` with relevant decision paths and statuses.
   - If the change touches ownership, layering, write paths, or domain invariants and no relevant decision exists, output `Architecture Decision Missing`.
   - If proposed decisions exist, get `openspec instructions decisions --change "<name>" --json` and apply `rules.decisions`.
   - Compare implementation placement against accepted/proposed decisions.

5. **Verify implementation**

   Inspect the implemented code paths, local diff, and tests relevant to the change. Check:
   - Behavior matches the specs and proposal
   - Tasks are accurately checked off
   - Implementation layer matches cited architecture decisions
   - No forbidden layer owns logic reserved for another layer
   - Tests prove behavior without hiding placement violations

6. **Run relevant checks**

   Run targeted tests or validation commands appropriate for the changed files. Use the change artifacts' validation plan when present. If checks cannot run, report that explicitly.

**Output**

Always include:

```text
Behavior matches spec: yes/no
Implementation matches architecture decisions: yes/no
Placement violations: <none or list>
```

Then summarize:
- Change name and schema
- Decisions checked by path
- Tests/checks run
- Remaining blockers or `NO_GO` reason

**Guardrails**
- Verification is read-only unless the user explicitly asks to fix findings.
- Do not mark verification successful when placement violates an accepted decision.
- Do not treat passing tests as sufficient architecture proof.
- Use exact file/function references for placement findings.
