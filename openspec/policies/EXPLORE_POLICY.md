# Explore Command Policy

This file owns custom `/opsx-explore` command policy. Shared OpenSpec context and `rules.explore` stay in `openspec/config.yaml`.

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
  valued_goals:
    enabled: true
    # North-star-like outcomes encoded as WORKLOG / chat goal candidates.
    # WORKLOG trust_level stays raw_notes — NOT product SoT and NOT tasks.md.
    source_priority:
      - "owner_explicit_north_star_or_goal_list"
      - "worklog_goal_like_lines"
      - "explore_inferred_from_repo_context"
    trust_level: "raw_notes_ranked_for_useful_work"
    value_gate:
      required: true
      style: "free_prose"
      # No numeric scorecard. Agent may draft VALUE; Owner may refine.
      missing_value_behavior: "propose_free_prose_value_then_rank"
    output_section: "Valued Goals (useful-work)"
    triggers:
      - "user_asked_useful_work_or_north_star"
      - "supervisor_TASK_MODE_USEFUL_WORK"
      - "user_asked_value_or_priority_of_goals"
    consumer: "/opsx-supervisor"
    consumer_mode: "USEFUL_WORK"
    # explore ranks only; does not mark goals done and does not write WORKLOG.
    do_not:
      - "treat_worklog_as_north_star_source_of_truth"
      - "invent_numeric_value_scale_as_required_contract"
      - "skip_value_gate_when_section_emitted"
```
