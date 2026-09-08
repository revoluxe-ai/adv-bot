# LESSON_GATE schema

Policy SoT: `.cursor/pipeline/ORCHESTRATION_MVP.md` §6.

## Class-level lesson allowed only when

```text
FANIN_READY
AND FANIN_PATH = .opsx/runs/bug-cases/<ROOT>/results/FANIN.md exists
AND coverage assessed (invariant coverage known)
AND FIXED branches contain RED/GO/FIX/GREEN evidence linkage
AND input ≠ root-only anecdote without branch rollup
```

When those hold:

```text
LESSON_GATE_PASS
CLASS_STATUS: may close or promote per Owner FINAL
CLASS_LEVEL_GO_WRITE: allowed only with Owner FINAL PROMOTE_CLASS_LESSON
```

## Otherwise (mandatory fail-closed)

```text
LESSON_CANDIDATE_ONLY
CLASS_STATUS: OPEN
CLASS_LEVEL_GO_WRITE: FORBIDDEN
```

Root patch or a single finding alone cannot create a confirmed class-level
lesson.

## Owner FINAL (after FANIN_READY)

```text
PROMOTE_CLASS_LESSON
KEEP_LESSON_CANDIDATE_ONLY
CLOSE_EPISODE_NO_CLASS_LESSON
SPLIT_NEW_EPISODE
```

Finding-local notes without class promotion may skip FANIN; they must not
claim a confirmed class lesson or class-rule GO write.
