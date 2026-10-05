# SHOP_WIDE_COMMON_SALES_IMPLEMENTATION_REPORT

Дата: 2026-10-05, Europe/Moscow. Итог: **локальная реализация готова к merge review**.

| Поле | Результат |
|---|---|
| CHANGE | `shop-wide-common-sales-collection` |
| WORKTREE | `C:\Users\vkita\my_code\meta-repo\shop-wide-common-sales-collection` |
| BRANCH | `shop-wide-common-sales-collection` |
| HEAD / BASE_HEAD | `62c8d48b15498997b84357e015b0e688f44fd37b` |
| CAMPAIGN_CHANGE_RECONCILIATION | YES — отдельная docs-only runner task `0100-R2` |
| ALL_SHOP_NMID_SOURCE | Existing `ProductsManager.get_cards_list`; пагинация текущих non-trash карточек |
| EXISTING_ROUTE | E: один снимок `get_complex_advs(only_bot_active=False, load_extras=False)`, уникальные `main_nmid`; E вне A сохраняется |
| UNCOVERED_ROUTE | U = A − E; пересечение E/U пустое на каждом tick |
| COMMON_COLLECTOR_REUSE | Один общий batch engine; existing funnel adapter, limiter, batch 20 и DTO |
| WB_COMMON_STAT_WRITER | Existing `ClickHouseCommonStatManager.insert` → `default_db.wb_common_stat`; version semantics сохранены |
| OPSX_VERIFY | PASS, mode=impl; независимый reviewer, task `0260` |
| SCENARIO_AUDIT | PASS, 33/33 сценария |
| MERGE_READINESS | READY — implementation merge; merge/archive/deploy не выполнялись |
| STORE_DRR_DENOMINATOR_READY | NO — source currency `unknown`; финансовая готовность не сертифицирована |
| STORE_DRR_NUMERATOR_READY | NO — `BLOCKED_BY_CAMPAIGN_COVERAGE` |
| STORE_DRR_READY | NO |
| HISTORY_BACKFILL | DEFERRED |

## Реализация

В существующей shop-runner coroutine `update_common_sale_stat` работает один координатор. В начале tick он фиксирует семидневное окно MSK и пишет provisional STARTED **до** обращений к источникам. Затем получает A и один снимок E, вычисляет U и собирает полные E/U через общий collector. Пересечение маршрутов исключено; старые CH rows не подавляют регулярное обновление.

Ответы проверяются по точному batch и окну. Missing не превращается в zero; invalid и конфликтующие дубликаты отклоняются. Coverage COMPLETE и freshness зависят от успешно записанных пар A × 7 дат. Ошибка CH не обновляет freshness. Успешный legacy E вне A сохраняет campaign freshness, но не увеличивает shop coverage.

Пагинация ограничена, проверяет cursor progress и отличает valid empty от unknown/malformed. Обычный partial/failure Content не отменяет сбор legacy E. Auth/cancellation сохраняют существующую политику остановки. Supervisor для 19 подтверждённых loader-path coroutines позволяет shop TaskGroup продолжать работу при отсутствии кампаний; прочие stop/auth/cancellation не поглощаются.

`update_last_week_stats(complex_advs) -> set[int]` сохраняет legacy fail-fast контракт. Новая explicit-NMID primitive использует тот же private engine и existing writer. Новые таблицы и WB adapters не создавались.

## FILES_CHANGED

Изменён production code:

- `app/modules/shop_runner/service_manager/manager.py`
- `app/modules/shop_runner/service_manager/services/common_sale_stat_updater/common_sale_stat_updater.py`
- `app/modules/shop_runner/wb_shop.py`

Добавлены восемь файлов в `app/modules/shop_runner/service_manager/services/shop_wide_common_sales/`: `__init__.py`, `collect_types.py`, `coordinator.py`, `coverage_evidence.py`, `fact_validator.py`, `legacy_assigned_nmids.py`, `shop_assortment_reader.py`, `taskgroup_no_ad_supervisor.py`.

Также изменены strict config и existing updater tests; добавлены coordinator tests, CH integration tests и OpenSpec артефакты. В campaign worktree изменена только ownership documentation. Unrelated stage не stash/reset/clean.

## TESTS / PYRIGHT

| Проверка | Результат |
|---|---|
| Coordinator + updater unit suites | 72 passed |
| Targeted `tests/test_wb_shop_run_coroutines.py` | 2 passed |
| Task-owned CH integration | 2 passed: production writer, existing freshness reader, argMax read-latest, fractional sums |
| Full `poetry run pyright-strict --outputjson` из feature worktree | 755 файлов, 0 errors, 0 warnings |
| Committed HEAD в одинаковой готовой среде | 743 файла, 0 errors, 0 warnings |
| `git diff --check` / OpenSpec strict | PASS |

Итого: **76 selected tests passed**. Дополнительный legacy `tests/tests_entry_points/test_wb_shop_run_coroutines.py` имеет 2 падения и на HEAD, и на current; fake TaskGroup не выполняет новые wrapper factories, secondary failure list отличается. Полный repository test suite зелёным не объявляется; независимый reviewer отметил это как non-blocking limitation данного implementation merge.

Canonical gate выполнен после подключения существующего готового venv; новые dependencies не устанавливались, sibling venv не изменялся. Предыдущие 17255/4860 type-метки не являются текущим verdict.

## SHOP_WIDE_COVERAGE_PROOF / DUPLICATE_ROUTE_PROOF

Синтетическая приёмка: A=500, E=120, U=380, union=500, intersection=0; 25 funnel batch calls, включая 6 для E и 19 для U. Проверены оба перехода ownership, partial universe, missing dates, source failure, CH failure и no-campaign TaskGroup survival. Это проверка implementation semantics; live WB shop сбор не запускался.

## MANAGEMENT_WRITE_GUARD

Collect path не создаёт `AdvSetting`, не меняет `bot_active`, не выполняет WB advertising writes и не пишет `full_adv_wb_stat`. Независимая сертификация использует production boundary/code trace и coordinator seams. Dedicated S13 test признан reviewer’ом placebo; PASS этого сценария не основан на нём.

## Независимые receipts

В feature change:

- `scenario-coverage/SCENARIO_TEST_COVERAGE_REPORT.md` — VERDICT=PASS, 33/33.
- `scenario-coverage/certify.receipt.json`
- `scenario-coverage/verify-impl.receipt.md`
- `scenario-coverage/exec.receipt.json` и raw log manifest.

Reviewer task: `WB-SKY-COMMON-SALES-SCENARIO-CERTIFY-20261005-0260`; agent отличается от implementation author.
CERTIFY_EVIDENCE_ID: `SCPV1-shop-wide-common-sales-20261005-certify-0260`.
EXEC_EVIDENCE_ID: `SCPV1-shop-wide-common-sales-20261005-evidence-close`.
Report SHA256: `d145f7816dd556176f29b375db820f2b49c9803c4f480ec6dffc0cd9794e6bf0`.
WORKTREE_FINGERPRINT: `7ccebe8a8c0d5455d39d28f406ca7031b1d7a9b54c3c3734d45964a795d48c8c`.

## BLOCKERS / NEXT_ACTION

Blockers для implementation merge: **нет по независимому verdict**.

Release constraints: currency unknown; advertising numerator blocked; prod CH DDL live не проверена; live WB не запускался. Сегодняшние факты provisional и обновляются следующими ticks. Historical backfill отложен.

Изменения остаются локальными и незакоммиченными на указанной branch. Следующий этап — отдельный merge/release цикл. Тестовый CH контейнер остановлен после проверок; повторный destructive-local запуск требует снова подготовленного отдельного endpoint.
