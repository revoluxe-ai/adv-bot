## Why

WB Sky AI control plane уже умеет собирать evidence (AI Package), фиксировать
канонические снимки настроек (`campaign-settings-history`), валидировать
`ChangeSetV1` в read-only dry-run (`wb_sky_control_plane`), и вести отдельные
продуктовые эксперименты (A/B Hold). Нет принятого контракта, который связывает
**семантику решения** (наблюдение, гипотеза, rationale, ожидаемый эффект) с
**исполнением** (ChangeSet / dry-run / будущий Apply) и **исходом** (детерминированная
оценка по метрикам).

Без этого слоя внешние агенты не могут надёжно отвечать на вопросы о прошлых
решениях и повторяют гипотезы.

## What Changes

- **Intent:** зафиксировать canonical domain contract `decision-experiment-memory`
  для WB Sky — planning only в этом change.
- Ввести `DecisionRecord`, `ExperimentRecord`, и **first-class immutable
  `ExperimentPlan`** (revision + digest + freeze), не заменяя plan плоским
  `evaluation_contract`.
- Разделить **execution_state** и **outcome**; модель assignment / apply /
  exposure с `effective_from` и `observation_start`.
- Методология: design types, counterfactual, validity, versioned metrics, windows,
  intervention signature, factual vs interpretation, provenance, post-hoc, causal
  evidence levels, `experiment_memory_index` для AI Package.
- Учесть **attribution-facts-contract** как known future evidence dependency
  (PR #456 / branch slice-a; не hard-dep Slice A).
- Proposed architecture decision для ownership и placement (PostgreSQL metadata,
  read-only export path согласован с `ai-package-v1-exporter-ownership`).

### Scope

In scope: OpenSpec artifacts (proposal, design, spec, proposed decision, tasks),
repository evidence classification, implementation slice plan.

Out of scope: код, Alembic/DDL, production writes, MCP, Apply Authority implementation,
attribution-facts change, shop-wide collection, campaign-settings-history internals.

### Current Behavior

- `ChangeSetMetadataV1` уже несёт optional `decision_id` / `experiment_id` как audit
  hints, исключённые из `semantic_digest` — но нет persistence или semantic record.
- Dry-run возвращает `DryRunResultV1` без обязательной durable receipt store в PG.
- Apply receipt / Apply Authority — не закоммичены как product spec (evidence gap).
- A/B Hold — отдельный durable lifecycle (`card-ab-hold-mode`); не generalized
  decision memory.

### Desired Behavior

- Каждое осмысленное AI/human/system решение MAY быть записано как `DecisionRecord`
  с evidence references (immutable IDs/digests), без копирования authoritative payloads.
- Опциональный `ExperimentRecord` добавляет evaluation contract и outcome; terminal
  outcomes детерминированы по метрикам, не по свободному тексту LLM.
- Reader port позволяет запросы «recent», «observing», «similar», «failed/rejected»
  transport-independent.
- Execution truth остаётся у Apply Authority; decision memory только ссылается.

## Capabilities

### New Capabilities

- `decision-experiment-memory`: canonical decision semantics, experiment evaluation
  contract, reader port, AI Package future hooks.

### Modified Capabilities

- `campaign-settings-changeset-contract`: уточнение связи metadata `decision_id` /
  `experiment_id` с persisted memory (reference only; follow-up slice C).

## Impact

Новый модульный namespace (план): `app/modules/decision_experiment_memory/`
(PostgreSQL append-friendly tables, read ports). Потребители: будущий Apply ingest,
AI Package collector slice F, control-plane metadata при создании ChangeSet.

Риски: дублирование settings history или Apply audit — снижаются жёсткими boundary
rules в proposed decision. Риск преждевременной реализации до Apply receipt schema —
снижается slice B dependency.

Rollback idea: planning-only change — откат = не принимать spec/decision; runtime
не затронут.
