import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# Предполагаем, что в updater.py есть основной класс Updater
from updater import Updater


@pytest.mark.asyncio
async def test_updater_run_calls_all_coroutines():
    """
    Тест проверяет, что метод run класса Updater вызывает все необходимые корутины
    """
    # Создаем экземпляр Updater
    updater = Updater()

    # Мокируем все методы, которые должны вызываться из run
    # Замените эти методы на реальные, которые вызываются в run
    updater.update_method1 = AsyncMock()
    updater.update_method2 = AsyncMock()
    updater.update_method3 = AsyncMock()
    updater.update_method4 = AsyncMock()

    # Подменяем asyncio.gather, чтобы проверить, какие корутины были переданы

    async def mock_gather(*args, **kwargs):
        # Создаем задачи для каждой корутины, но не запускаем их
        return [arg for arg in args]

    # Применяем наш мок-метод
    with patch("asyncio.gather", side_effect=mock_gather):
        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что все ожидаемые корутины были вызваны
        updater.update_method1.assert_called_once()
        updater.update_method2.assert_called_once()
        updater.update_method3.assert_called_once()
        updater.update_method4.assert_called_once()


@pytest.mark.asyncio
async def test_updater_run_gathers_correct_number_of_coroutines():
    """
    Тест проверяет, что метод run класса Updater передает правильное количество
    корутин в asyncio.gather
    """
    # Создаем экземпляр Updater
    updater = Updater()

    # Мокируем все методы, которые должны вызываться из run
    updater.update_method1 = AsyncMock()
    updater.update_method2 = AsyncMock()
    updater.update_method3 = AsyncMock()
    updater.update_method4 = AsyncMock()

    # Мокируем asyncio.gather для проверки количества аргументов
    with patch("asyncio.gather") as mock_gather:
        # Настраиваем mock_gather, чтобы он возвращал корутину
        mock_gather.return_value = asyncio.create_task(asyncio.sleep(0))

        # Вызываем тестируемый метод
        await updater.run()

        # Проверяем, что gather был вызван ровно один раз
        mock_gather.assert_called_once()

        # Получаем все аргументы, с которыми был вызван gather
        call_args = mock_gather.call_args[0]

        # Проверяем, что gather был вызван с ожидаемым количеством аргументов
        # Замените число 4 на реальное количество методов в updater.run
        expected_count = 4
        assert (
            len(call_args) == expected_count
        ), f"asyncio.gather должен быть вызван с {expected_count} аргументами, получено {len(call_args)}"

        # Проверяем, что все методы были вызваны по одному разу
        updater.update_method1.assert_called_once()
        updater.update_method2.assert_called_once()
        updater.update_method3.assert_called_once()
        updater.update_method4.assert_called_once()


@pytest.mark.asyncio
async def test_updater_run_coroutines_without_errors_for_one_minute():
    """
    Тест проверяет, что все корутины из метода run класса Updater
    запускаются без ошибок в течение минуты.
    """
    # Создаем экземпляр Updater
    updater = Updater()

    # Имитация корутины, которая будет работать бесконечно
    async def mock_infinite_run(*args, **kwargs):
        try:
            # Имитируем работу бесконечной корутины
            while True:
                await asyncio.sleep(0.1)
        except Exception as e:
            # Если возникает исключение, перехватываем его и выводим
            pytest.fail(f"Корутина вызвала исключение: {e}")

    # Мокируем все методы, которые должны вызываться из run
    updater.update_method1 = AsyncMock(side_effect=mock_infinite_run)
    updater.update_method2 = AsyncMock(side_effect=mock_infinite_run)
    updater.update_method3 = AsyncMock(side_effect=mock_infinite_run)
    updater.update_method4 = AsyncMock(side_effect=mock_infinite_run)

    # Запускаем run и ждем минуту
    task = asyncio.create_task(updater.run())

    # Подождем 60 секунд (минуту)
    try:
        await asyncio.wait_for(task, timeout=60.0)
    except TimeoutError:
        # Тайм-аут ожидаем, так как корутины должны работать бесконечно
        pass

    # Проверяем, что задача не завершилась с исключением
    if task.done() and not task.cancelled():
        # Если задача завершилась и не была отменена, проверяем наличие исключения
        try:
            task.result()
        except Exception as e:
            pytest.fail(f"Корутина завершилась с исключением: {e}")

    # Отменяем задачу, так как она бесконечна
    task.cancel()

    # Подождем отмену задачи
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except (TimeoutError, asyncio.CancelledError):
        # Мы ожидаем, что задача будет отменена
        pass
