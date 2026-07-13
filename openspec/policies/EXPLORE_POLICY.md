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
    output_section: "WORKLOG Findings"
```
