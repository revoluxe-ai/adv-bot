# Отчет: точки входа process_payment_for_advs

Цель документа: зафиксировать все точки входа, которые приводят к вызову функции `process_payment_for_advs` внутри проекта, а также связанные контексты запуска.

Краткое резюме
- Основной запуск осуществляется через orchestrator-подход: `updater.py` координирует несколько фоновых процессов, один из которых — `run_main_coroutines`.
- В `wb_adv_updater/runner.py` в функции `main_loop` запускаются задачи через `asyncio.gather`, включая `process_payment_for_advs`.
- Самая функция находится в `app/modules/wb_adv_updater/wb_manager.py` и вызывается в рамках цикла инициализации, циклов и проверок условий доступа/остатков.

Стратегия запуска (путь вызова)
- updater.py
  - содержит список `run_own_process_list`, который включает `run_main_coroutines`.
  - `updater.py` запускает эти процессы через multiprocessing; итоговый набор запускается в `main()` и через цикл поддерживает работу сервиса.
- wb_adv_updater/runner.py
  - `main_loop(client_session)` агрегирует задачи:
    - `process_payment_for_advs()` — главная логика обработки платежей.
    - другие поддерживающие задачи: обновление в redis, в графе и т.д.
  - Пример кода:
    ```python
    async def main_loop(client_session):
        await asyncio.gather(
            process_payment_for_advs(),
            run_update_vectors_in_redis(),
            run_vector_update_in_neo4j(),
            update_wb_config_data(client_session),
        )
    ```
- wb_manager.py
  - Определение `process_payment_for_advs()` и вспомогательных функций: проверки платежей за дату, расчётов цен и списаний.

Замечания
- В текущем коде явного `if __name__ == "__main__"` для вызова `process_payment_for_advs` нет; входы реализованы через orchestrator-подход, как описано выше.

Примечание по безопасности/надежности
- Запуск фоновых задач реализован через отдельные процессы/координацию, что может влиять на отладку и логирование. Рассмотрите добавление флагов управления и обработчика ошибок.



