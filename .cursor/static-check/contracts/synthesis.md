# Orchestrator synthesis contract

After fan-in:

1. Normalize findings from all packets.
2. Merge intersections (same path+symbol / same test node across tools) into one problem group with `seen_in`.
3. Rank: environment/config → collection → multi-tool typing → typing → multi-seen pytest → other pytest → other.
4. Budget: ≤12 problem groups, ≤4 evidence lines/group, ~80 lines / ~3500 chars body; set TRUNCATED + OMITTED_GROUPS; keep full counters.
5. One NEXT_ACTION: typing → `/opsx-fix-types`; pytest → `/opsx-test-triage`; env → recover step; PASS → continue (optional `/opsx-verify` hint only, never archive GO).
