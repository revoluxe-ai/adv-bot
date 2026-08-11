# Explore Command Policy

This file owns custom `/opsx-explore` command policy. Shared OpenSpec context and `rules.explore` stay in `openspec/config.yaml`.

Behavioral SoT for research steps and `EXPLORE_HANDOFF` shape:
`.cursor/commands/opsx-explore.md`.

## OpenSpec history as explore context (when `OWNER_INTENT` present)

Targeted only (no broad archive scan), keyed from `OWNER_INTENT` / capability /
UI terms / related specs / known IDs / found runtime entities:

1. current `openspec/specs/**` — acting contract;
2. Accepted `openspec/decisions/**` — keep ADL budgets from the command;
3. relevant `openspec/changes/archive/**` — **historical evidence only**, not SoT;
4. then current code/tests.

On conflict: current main spec > archived change. Contract vs repository
behavior must surface as explicit drift (`CONTRACT_VS_REPO`), not a silent
pick. Archive / OpenSpec interpretation must not rewrite `OWNER_INTENT`.

```yaml
explore:
  language: ru
  worklog:
    enabled: true
    path: "DOTO/WORKLOG.md"
    read_if_exists: true
    missing_is_not_blocker: true
    trust_level: "raw_notes"
    purpose:
      - "research_context"
      - "candidate_tasks"
      - "known_bugs"
      - "open_questions"
      - "affected_files_hints"
      - "validation_hints"
      - "prior_agent_findings"
      - "deferred_from_change_parks"
    output_section: "WORKLOG Findings"
    # /opsx-explore MUST NOT write this file.
    # Allowed OPSX append producer for deferred-from-<CHANGE_ID> parks:
    #   /opsx-bound-scope:GO  (append-only; still raw_notes, not tasks.md SoT)
    # Allowed OPSX narrow annotate on confirmed re-entry into a change:
    #   /opsx-update after REENTER_CONFIRMED → mark [re-entered:<CHANGE_ID>]
    writers:
      append_deferred_from_change: "/opsx-bound-scope"
      annotate_reentered_from_change: "/opsx-update"
  now_later:
    enabled: true
    required: false
    output_section: "Now / Later (optional)"
    triggers:
      - "user_asked_now_later_or_mvp_boundary"
      - "two_plus_implementation_threads"
      - "active_change_looks_oversized"
      - "user_supplied_split_hint"
    handoff_command: "/opsx-bound-scope"
    # explore suggests only; does not park and does not own /opsx-update:split
```
