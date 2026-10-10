# Owner Contract

## Что хотим получить

Канонический **доменный фундамент** памяти решений и экспериментов WB Sky (Slice A):
семантика WHY / EXPECT / протокол / outcome metadata / interpretation linkage —
без production persistence и без write authority.

## Зачем

Единый transport-independent контракт для будущих persistence, ingest, evaluator и
AI export slices.

## Что должно остаться неизменным

- `campaign-settings-history` — authority настроек.
- ChangeSetV1 — authority intent.
- Apply Authority — validation (`DryRunReceiptV1`) и execution (`ApplyEvidenceV1`);
  память хранит только `DryRunReceiptRef` / `ApplyEvidenceRef`.
- attribution-facts — отдельный authority; память — optional ref.
- AI Package export — read-only в будущем slice; не в этом archive.

## Что доставлено (foundation)

- Модуль `app/modules/decision_experiment_memory/` + unit tests.
- Test-only `InMemoryDecisionMemoryRepository` (не production tier).

## Что не доставлено (future changes)

- PG / Alembic, Apply/exposure ingest, evaluator, post-hoc runtime, `decision_memory_v1`.

## Как поймём, что получилось

- PR #460 merged; `FOUNDATION_CERTIFICATION.md`; change archived Option A.
- Main spec содержит только foundation semantics.
- Evolution doc фиксирует границы B–F.

## Решения Owner

- Planning accepted (PR #457).
- Slice A merged (PR #460).
- **Option A foundation-only archive** (2026-10-09).
