STATUS:
FIX_PLAN_READY

DEFECTS_TO_FIX:

1.
DEFECT:
Decision lookup conflict

FILES:
- .cursor/rules/architecture-decisions.mdc
- .cursor/commands/opsx-apply.md
- .cursor/commands/opsx-verify.md

CURRENT_BEHAVIOR:
Agent получает две инструкции:
1. искать все openspec/decisions/**
2. использовать bounded context-first lookup

PROPOSED_BEHAVIOR:
Agent сначала использует:
- artifact paths;
- declared decisions;
- bounded fallback lookup.

Если нужное решение не найдено:
EVIDENCE_GAP.

USER_IMPACT:
Меньше лишнего контекста, предсказуемый decision resolution.

RISK:
LOW


2.
DEFECT:
Archive bypasses verify gate

FILES:
- .cursor/commands/opsx-archive.md

CURRENT_BEHAVIOR:
Archive может выполниться без verify GO.

PROPOSED_BEHAVIOR:
Archive требует:
- same change identity;
- verify verdict;
- Archive ready=yes.

RISK:
MEDIUM


SUMMARY:
Files to modify:
3

Files not touched:
production code
openspec decisions
tasks