---
cursor:
  subagentId: "bc-f097b4ce-6fbc-5233-aef6-016d73934877"
---

# OPSX command-only rules — PR handoff

**Branch:** `cursor/opsx-command-only-rules` (from `origin/stage`)  
**Commit:** `ed30fba84`

## Pull request

https://github.com/revoluxe-ai/adv-bot/pull/455 (draft → `stage`)

## Files touched

| Path | Action |
|------|--------|
| `.cursor/rules/opsx-single-active-command.mdc` | Added (port from tiriel-game OPSX spine) |
| `.cursor/rules/opsx-command-only-execution.mdc` | Added (command-only enforcement) |

## Notes

- Stored directly under `.cursor/rules/` like `architecture-decisions.mdc` (alwaysApply); skipped `cursor_rules_temp/` staging per task and existing alwaysApply pattern.
- No `app/**` or test changes.
