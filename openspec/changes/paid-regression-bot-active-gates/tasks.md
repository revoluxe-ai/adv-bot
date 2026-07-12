## 1. Инфраструктура тестов

- [x] 1.1 Добавить в `pytest.ini` маркеры `paid_regression` и `bot_active_gates` с кратким описанием
- [x] 1.2 Создать `tests/paid_regression/` и `tests/bot_active_gates/` с `__init__.py` (пустые или module docstring)
- [x] 1.3 Написать `tests/paid_regression/README.md`: назначение, команда запуска, критерий «paid не сломан»
- [x] 1.4 Написать `tests/bot_active_gates/README.md`: четыре P0 категории ACT, xfail для RECORD, команда запуска
- [x] 1.5 Создать `tests/bot_active_gates/conftest.py`: фабрики `ComplexAdv` / `AdvSetting` с `bot_active=False` и **включёнными** auto-flags; `WBApi` через корневую `access_mock`
- [x] 1.6 Создать `tests/paid_regression/conftest.py`: фабрики с `bot_active=True`; переиспользовать `helpers.py` из gate-suite
- [x] 1.7 Добавить `tests/paid_regression/CURATED.md` — список существующих тестов (billing, balance_manager, shop_menu tariff, toggle_cabinet_active)

## 2. Матрица RECORD / ACT

- [x] 2.1 Создать `tests/bot_active_gates/RECORD_ACT_MATRIX.md` (или `docs/shop_runner_record_act_matrix.md`) — таблица всех корутин из `WBShop.run()` с классификацией RECORD vs ACT
- [x] 2.2 Сверить матрицу с `tests/test_wb_shop_run_coroutines.py` — все методы из списка `methods` покрыты
- [x] 2.3 Отметить в матрице P0 ACT (4 категории пользователя + cluster bids, minus phrases, cpm bidder)

## 3. Bot-active ACT gates (P0 — MUST be GREEN now)

- [x] 3.1 `test_no_common_bid_when_inactive.py`: `update_common_bid_in_search_adv` — non-vacuous inactive gate: `get_complex_advs` returns inactive adv, `get_wb_advs_dto` returns non-empty search DTO/input, resolver returns current bids that would reach `UpdateCommotBidInSearchAdvsManager.update_common_bid_in_search_adv`; assert manager / WB modifier not called only after the write path is otherwise reachable
- [x] 3.2 `test_no_target_place_when_inactive.py`: `update_individual_keyword_target_places` — mock `KeywordTargetPlaceUpdater` / WB path not called
- [x] 3.3 `test_no_whitelist_top_key_when_inactive.py`: `update_top_key_in_advs` — `FirstKeyUpdater.top_key_auto_update` not called
- [x] 3.4 `test_no_whitelist_trimmer_when_inactive.py`: `white_list_tail_trimmer` — `WhiteListTrimmer.trim` not called
- [x] 3.5 `test_no_shelf_bid_when_inactive.py`: `auto_shelf_bid_control` — `_set_target_bid` / `_persist_state_then_set_bid` not called (паттерн из `test_auto_shelf_bid_control_manager.py`)
- [x] 3.6 `test_no_cluster_bids_when_inactive.py`: `update_cluster_bids` — `update_cluster_bids_manager.update_cluster_bids` not invoked with inactive adv
- [x] 3.7 `test_no_minus_phrases_when_inactive.py`: `update_minus_phrases_in_advs` — minus manager not called
- [x] 3.8 `test_no_cpm_bid_when_inactive.py`: `update_cpm_bid` — `run_bidder_process_for_adv` not called
- [x] 3.9 Все gate-тесты: `@pytest.mark.unit`, `@pytest.mark.bot_active_gates`, `@pytest.mark.asyncio`

## 4. Bot-active ACT gates (P1 — v3 / auto-updater)

- [x] 4.1 `test_no_adv_settings_auto_update_when_inactive.py`: `adv_settings_auto_update` — `process_adv_v3` / `AdvControlSystem.process_adv` not scheduled for inactive adv
- [x] 4.2 `test_no_delete_wl_by_ctr_when_inactive.py`: `delete_keywords_from_wl_by_mean_auto_ctr` — handler not called (уже есть filter `adv.bot_active` в manager)

## 5. RECORD gates (target — xfail until loader refactor)

- [x] 5.1 `test_keyword_stamp_runs_when_inactive.py`: `update_keywords_stamp` — stamp manager **should** be called (mark `@pytest.mark.xfail(reason="loader refactor pending")`)
- [x] 5.2 `test_common_sale_stat_runs_when_inactive.py`: `update_common_sale_stat` — updater invoked for inactive adv (xfail)
- [x] 5.3 Документировать в README критерий снятия xfail: follow-up change на `_get_active_advs`

## 6. Paid regression suite (P0)

- [x] 6.1 `test_turn_bot_on_requires_balance.py`: unit на handler turn-on — insufficient balance → `bot_active` stays False; mock `sm` как callable (`MagicMock(side_effect=lambda **_: _session_cm(session))`)
- [x] 6.2 `test_turn_bot_on_sets_active.py`: sufficient balance → `bot_active=True`, commit; тот же паттерн `sm` + `AdvSettingMenu` → `AsyncMock()`
- [x] 6.3 `test_turn_bot_off_sets_inactive.py`: `turn_adv_off` / `off_all` → `bot_active=False`; `turn_adv_off` — factory с read/write session
- [x] 6.4 `test_paid_common_bid_runs_when_active.py`: inverse gate — active adv → manager update path called (mock success)
- [x] 6.5 `test_paid_shelf_bid_runs_when_active.py`: inverse — active + enabled → setter path reachable (extend existing shelf manager tests pattern)
- [x] 6.6 `test_pricer_counts_only_bot_active.py`: patch `fetch_bot_active_advs` → `[]`, assert `get_tariff_details(...).count == 0`
- [x] 6.7 Все paid regression: `@pytest.mark.unit` (или integration где нужна PG), `@pytest.mark.paid_regression`

## 7. Валидация и документация

- [x] 7.1 Прогнать `poetry run pytest tests/bot_active_gates -m bot_active_gates -v` — P0 gates GREEN (xfail только RECORD) после исправления non-vacuous common-bid gate
- [x] 7.2 Прогнать `poetry run pytest tests/paid_regression -m paid_regression -v` — all GREEN
- [x] 7.3 Прогнать curated adjunct: `poetry run pytest tests/modules/billing tests/modules/balance_manager/test_handlers_comprehensive.py -m unit -q`
- [x] 7.4 Добавить в `AGENTS.md` или `tests/paid_regression/README.md` секцию «Pre-merge для free-веток» с двумя командами
- [x] 7.5 `git diff --check` на изменённые файлы

## Implementation notes (post-apply)

Зафиксировано после первого прогона suite — типичные ошибки mock-конфига:

| Ошибка | Симптом | Исправление |
|--------|---------|-------------|
| `sm` = context manager instance | `AsyncContextDecorator.__call__() got unexpected keyword argument 'read_only'` | `MagicMock(side_effect=lambda **_: _session_cm(session))` |
| WBApi без tokens | падение в `WBApi.__init__` | фикстура `access_mock` из `tests/conftest.py` |
| patch в `manager.py` | mock не перехватывает lazy import | patch в модуле-источнике dependency |
| shelf gate | false positive «setter not called» | проверять `run_tasks(handlers=[])` или len handlers |
| common-bid gate с `get_wb_advs_dto=[]` | false positive «manager not called» из-за раннего выхода до paid gate | вернуть непустой DTO/search input и resolver result, чтобы отсутствие `bot_active` gate привело к вызову write manager |

## 8. Follow-up (out of scope этого change — зафиксировать в design)

- [ ] 8.1 Создать отдельный change proposal: refactor `_get_active_advs` → RECORD all non-done + `is_paid_actions_enabled()` helper
- [ ] 8.2 После loader refactor: снять xfail с RECORD gate-тестов (task в том change)
- [ ] 8.3 Free UI bot + handler access guards (отдельный proposal)
