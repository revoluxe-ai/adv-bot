# Рефакторинг Cost Resolver - Итоговая сводка

## Проблема
Трёхкратное дублирование бизнес-логики выбора между `target_pay_for_order` и `max_pay_for_order` на основе выполнения плана, с различающейся обработкой ошибок.

## Решение
Создана общая утилита в `app/shared/domains/wb/utils/cost_resolver.py` с двумя функциями, консолидирующими общую логику.

## Финальная структура файлов

### Утилита
```
app/shared/domains/wb/utils/cost_resolver.py
```
- `resolve_target_cost_from_context(ctx: PipelineContext) -> float | None`
- `resolve_target_cost_from_summary(summary: PlanFactSummary | None) -> float | None`

### Тесты
```
tests/app/shared/domains/wb/utils/test_cost_resolver.py
tests/app/shared/domains/wb/utils/__init__.py
tests/app/shared/domains/wb/__init__.py
tests/app/shared/domains/__init__.py
tests/app/shared/__init__.py
```

### Изменённые файлы (импорты обновлены)
1. `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/executors/white_list_executor/white_list_add_executor.py`
   - Убран метод `_resolve_target_cost()`
   - Импорт: `from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost_from_context`

2. `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/executors/white_list_executor/white_list_remove_executor.py`
   - Убран метод `_get_target_pay_for_order()`
   - Импорт: `from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost_from_context`

3. `app/modules/shop_runner/service_manager/services/auto_adv_active_control/auto_adv_active_control_service.py`
   - Убран метод `_resolve_target_cost()`
   - Импорт: `from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost_from_summary`

### Удалённые файлы
- `app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/utils/` (вся директория)
- `tests/app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/utils/` (вся директория)

## Результаты тестирования

✅ **40 тестов прошли успешно:**
- 18 тестов `cost_resolver` (новые)
- 6 тестов `white_list_remove_executor`
- 7 тестов `auto_adv_active_control`
- 9 тестов `adv_control_system`

## Преимущества размещения в shared

1. **Доменная принадлежность**: Утилита находится в `app/shared/domains/wb/` рядом с другими WB-утилитами (`balance_source.py`)
2. **Переиспользуемость**: Доступна для всех модулей без циклических зависимостей
3. **Единообразие**: Следует структуре проекта для shared-утилит
4. **Обнаружимость**: Легко найти среди других WB domain utilities

## Команды для проверки

```powershell
# Проверка тестов утилиты
poetry run pytest tests/app/shared/domains/wb/utils/test_cost_resolver.py -v

# Проверка всех затронутых тестов
poetry run pytest tests/app/shared/domains/wb/utils/ tests/app/modules/shop_runner/service_manager/test_auto_adv_active_control.py tests/app/modules/shop_runner/service_manager/old_modules/setting_auto_updater_v2/adv_control_system/ -v

# Проверка white_list тестов
poetry run pytest tests/ -k "white_list" -v
```

## См. также

- [REFACTORING_COST_RESOLVER.md](REFACTORING_COST_RESOLVER.md) - детальная документация рефакторинга
