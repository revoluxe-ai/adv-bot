# Owner Contract

## Что хотим получить

Единый версионированный пакет изменений настроек кампании `ChangeSetV1`
(канонический тип в `app/modules/wb_sky_control_plane/models/changeset.py` после
явного adoption checkpoint), привязанный к ресурсам через `CampaignResourceRef` и
реестр `cmp_*`. Пакет несёт `state_token` поколения снимка, опциональные
семантические предусловия `expected_current_value` на уровне поля, и ограниченный
набор типизированных операций (в локальном WIP уже есть, например,
`SetBudgetPolicyOperation`; полный перечень — в том же `changeset.py` на момент
adoption). Проверка и dry-run независимы от транспорта (JSON, будущий API, MCP).
На выходе только статусы dry-run `NO_OP`, `OK` или `REJECTED` и детерминированный
список `SemanticDiffEntryV1`. Записи в Wildberries, PostgreSQL, ClickHouse или
Excel этот инкремент не выполняет.

**ADOPTION_DECISION:** change `campaign-settings-changeset-contract` принимает и
расширяет доказанную основу `wb_sky_control_plane` **только после** явного локального
preservation checkpoint, который привязывает точные owned paths к этому change.
Локальный незакоммиченный WIP на HOME-PC **ещё не принадлежит** PR
[#449](https://github.com/revoluxe-ai/adv-bot/pull/449); исторический OpenSpec-owner
этого дерева был UNKNOWN.

## Зачем

Реестр `campaign_settings_contract` уже классифицирует поля, но намерение изменить
настройки не является единым контрактом. Локальный WIP control plane уже содержит
`ChangeSetV1` и `validate_changeset` — второй параллельный контракт в
`campaign_settings_contract` недопустим. Модель может сформулировать намерение;
решение о записи остаётся за WB Sky после детерминированной проверки. AI не является
write authority.

## Что должно остаться неизменным

Текущие настройки по-прежнему читаются из PostgreSQL. `campaign_settings_contract`
остаётся реестром полей (`FieldPolicy`, `normalize_value`), а не владельцем
ChangeSet. История в ClickHouse и Excel — проекции реестра, не протокол управления.
Существующие пути записи из бота, Excel и shop-runner в этом planning change не
переписываются. Рекламная логика ставок и жизненный цикл кампаний в проде не
меняются.

## Чего сейчас не делаем

Не пишем в WB API, PostgreSQL settings, ClickHouse. Нет apply, согласования,
журнала change events, post-check, MCP, публичного API, Telegram UI, переделки
Excel, полного AI Package, durable idempotency store, distributed locks. Не
используем MIXED-адаптер
`app/core/mp/wb/api/adapter/promotion_client/campaigns_info_v2/adapter.py`.
Не коммитим и не «присваиваем» PR #449 локальный dirty WIP без checkpoint
`LOCAL_FOUNDATION_ADOPTION_REQUIRED`.

## Как поймём, что получилось

После adoption и реализации (вне этого planning-only PR): валидная операция из
существующего bounded набора даёт `OK` и `SemanticDiffEntryV1` с old/requested/
normalized; идентичный после нормализации снимок даёт `NO_OP`. Неподдерживаемая
мутация, неизвестная/неподдерживаемая capability (fail closed поверх tri-state),
устаревший или отсутствующий `state_token`, расхождение `expected_current_value` с
поколением `state_token`, дубликат `operation_id`, конфликт `changeset_id`, смесь
годных и негодных операций — атомарный `REJECTED` всего ChangeSet. Повторный dry-run
с тем же `changeset_id` и тем же canonical body детерминированно воспроизводит
прежний `NO_OP` или `OK` без durable store. Ни один forbidden adapter не вызывается.

## Решения Owner

- **REUSE_DECISION:** `EXTEND_EXISTING` — один `ChangeSetV1` в `wb_sky_control_plane`,
  не второй тип и не owner в `campaign_settings_contract`.
- **IMPLEMENTATION_BLOCKER:** `LOCAL_FOUNDATION_ADOPTION_REQUIRED` (preservation
  checkpoint перед любым product кодом).
- Модель создаёт только намерение; WB Sky владеет решением о записи.
- Контракт transport-independent; Excel не канонический протокол управления.
- Сложные межполевые инварианты — именованные domain validators, не только JSON
  Schema и не только строка registry.
- Нормализация зарегистрированных settings-полей — reuse `campaign_settings_contract.normalize_value`;
  ChangeSet и dry-run остаются в control plane.
- Сверка WIP: `/cursor/stores/bc-18f0b34a-df7b-4a06-b47a-7bfd4a10a089/docs/changeset-local-wip-reconciliation.md`
  (ранее CONFLICT → replan на EXTEND_EXISTING).
