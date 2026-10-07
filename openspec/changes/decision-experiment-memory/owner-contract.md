# Owner Contract

## Что хотим получить

Transport-independent память WB Sky о **семантике решений** и **фактических
экспериментах**: наблюдение, гипотеза, preregistered plan, intervention linkage,
validity, результаты и outcome. Две сущности с **независимыми** идентичностями:

- `DecisionMemoryRecord` (`decision_id`)
- `ExperimentRecordV1` (`experiment_id`, `decision_id` FK)

Кардинальность: одно решение → **0..N** экспериментов (ретест, switchback,
follow-up). V1 API **может** ограничить создание одним экспериментом на решение,
но контракт хранения **не** запрещает 1:N.

Отдельно фиксируются:

- **experiment_design** — как производится доказательство (causal/observational design);
- **treatment_mode** — применяется ли LIVE-вмешательство в прод (`LIVE` | `SHADOW`).

Запись решения/эксперимента **никогда** не является разрешением на production write.
Apply Authority остаётся единственным write gate.

## Зачем

AI-контур должен отвечать: что решили, на каких evidence, какой ChangeSet,
был ли apply, что ожидали, что измерили, succeeded/failed/inconclusive/invalid.
Settings history отвечает «что изменилось в настройках»; Apply audit — «что
выполнили»; attribution — «экономические факты». Этот change — «почему и какой
смысл/результат эксперимента».

## Что должно остаться неизменным

- PostgreSQL — authority текущих настроек; CH `campaign_settings_history` — timeline
  settings (`snapshot_id`, `state_hash`).
- `wb_sky_control_plane` — ChangeSet dry-run; link only, not owner memory.
- `keyword_decisions` / `bid_decision_log` — bid telemetry, **не** decision memory.
- Product `card_ab_hold` epoch — отдельный продукт; только optional cross-ref.

## Чего сейчас не делаем

Нет миграций, production write, deploy, MCP transport, копирования authoritative
payloads (только IDs/digests/refs). Нет промоушена ADR в registry до Owner GO.
Нет блокировки Slice A на появление ApplyReceipt — только optional
`ApplyEvidenceRef`.

## Как поймём, что получилось

**Planning (этот пакет):** согласованные `owner-contract.md`, `design.md`, delta
spec, proposed ADR, `tasks.md`, scenario-coverage plan + receipt, `check-openspec`
PASS.

**После implementation (отдельные GO):** Slice A unit-тесты инвариантов без PG;
позже Slice B+ персистенция и ingest.

## Решения Owner (planning)

- Independent `decision_id` / `experiment_id`; **MUST NOT** equate them.
- SHADOW — `treatment_mode`, не `experiment_design`.
- `execution_state` и `outcome` — ортогональные оси.
- Without authoritative Apply evidence: no `APPLY_CONFIRMED`; no factual LIVE
  `effective_from`; no valid LIVE exposure claims.
