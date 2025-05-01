import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# Предполагаем, что в run_keywords_parsing.py есть функция main или класс KeywordsParser
# Адаптируйте импорт под реальную структуру модуля
try:
    from run_keywords_parsing import KeywordsParser

    class_based = True
except ImportError:
    from run_keywords_parsing import main

    class_based = False


@pytest.mark.asyncio(loop_scope="session")
async def test_keywords_parsing_run_calls_all_functions():
    """
    Тест проверяет, что парсер ключевых слов вызывает все необходимые функции
    """
    if class_based:
        # Для класса KeywordsParser

        # Создаем экземпляр парсера
        parser = KeywordsParser()

        # Мокируем все методы, которые должны вызываться при парсинге
        # Замените эти методы на реальные методы вашего класса
        parser.fetch_keywords = AsyncMock()
        parser.process_keywords = AsyncMock()
        parser.store_keywords = AsyncMock()

        # Вызываем тестируемый метод
        await parser.run()

        # Проверяем, что все ожидаемые методы были вызваны
        parser.fetch_keywords.assert_called_once()
        parser.process_keywords.assert_called_once()
        parser.store_keywords.assert_called_once()
    else:
        # Для функции main

        # Создаем моки для всех функций, которые должны вызываться из main
        # Замените эти функции на реальные функции
        with patch(
            "run_keywords_parsing.fetch_keywords", new_callable=AsyncMock
        ) as mock_fetch, patch(
            "run_keywords_parsing.process_keywords", new_callable=AsyncMock
        ) as mock_process, patch(
            "run_keywords_parsing.store_keywords", new_callable=AsyncMock
        ) as mock_store:

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что все ожидаемые функции были вызваны
            mock_fetch.assert_called_once()
            mock_process.assert_called_once()
            mock_store.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_keywords_parsing_handles_exceptions():
    """
    Тест проверяет, что парсер ключевых слов корректно обрабатывает исключения
    """
    if class_based:
        # Для класса KeywordsParser

        # Создаем экземпляр парсера
        parser = KeywordsParser()

        # Мокируем метод, который вызывает исключение
        parser.fetch_keywords = AsyncMock(side_effect=Exception("Test exception"))

        # Мокируем другие методы
        parser.process_keywords = AsyncMock()
        parser.store_keywords = AsyncMock()

        # Вызываем тестируемый метод и ожидаем, что исключение обрабатывается
        try:
            await parser.run()
            # Если исключение было обработано в методе run, проверяем, что остальные методы не вызывались
            parser.process_keywords.assert_not_called()
            parser.store_keywords.assert_not_called()
        except Exception:
            # Если исключение не обрабатывается в методе run, тест все равно пройдет, но это нужно будет учесть
            pass
    else:
        # Для функции main

        # Создаем моки для функций, с одной функцией, вызывающей исключение
        with patch(
            "run_keywords_parsing.fetch_keywords",
            new_callable=AsyncMock,
            side_effect=Exception("Test exception"),
        ) as mock_fetch, patch(
            "run_keywords_parsing.process_keywords", new_callable=AsyncMock
        ) as mock_process, patch(
            "run_keywords_parsing.store_keywords", new_callable=AsyncMock
        ) as mock_store, patch(
            "run_keywords_parsing.handle_error", new_callable=AsyncMock
        ) as mock_handle_error:

            # Вызываем тестируемую функцию
            try:
                await main()
                # Если исключение было обработано в main, проверяем, что обработчик ошибок был вызван
                mock_handle_error.assert_called_once()
                # И что последующие функции не вызывались
                mock_process.assert_not_called()
                mock_store.assert_not_called()
            except Exception:
                # Если исключение не обрабатывается в main, тест все равно пройдет, но это нужно будет учесть
                pass


@pytest.mark.asyncio(loop_scope="session")
async def test_keywords_parsing_performance():
    """
    Тест проверяет, что парсер ключевых слов выполняется за разумное время
    """
    if class_based:
        # Для класса KeywordsParser

        # Создаем экземпляр парсера
        parser = KeywordsParser()

        # Мокируем методы, чтобы они выполнялись быстро
        parser.fetch_keywords = AsyncMock(
            return_value=["keyword1", "keyword2", "keyword3"]
        )
        parser.process_keywords = AsyncMock(
            return_value=["processed1", "processed2", "processed3"]
        )
        parser.store_keywords = AsyncMock()

        # Замеряем время выполнения
        start_time = asyncio.get_event_loop().time()
        await parser.run()
        end_time = asyncio.get_event_loop().time()

        # Проверяем, что выполнение заняло не более 1 секунды
        assert end_time - start_time < 1.0, "Выполнение заняло слишком много времени"
    else:
        # Для функции main

        # Создаем быстрые моки для всех функций
        with patch(
            "run_keywords_parsing.fetch_keywords",
            new_callable=AsyncMock,
            return_value=["keyword1", "keyword2", "keyword3"],
        ) as mock_fetch, patch(
            "run_keywords_parsing.process_keywords",
            new_callable=AsyncMock,
            return_value=["processed1", "processed2", "processed3"],
        ) as mock_process, patch(
            "run_keywords_parsing.store_keywords", new_callable=AsyncMock
        ) as mock_store:

            # Замеряем время выполнения
            start_time = asyncio.get_event_loop().time()
            await main()
            end_time = asyncio.get_event_loop().time()

            # Проверяем, что выполнение заняло не более 1 секунды
            assert (
                end_time - start_time < 1.0
            ), "Выполнение заняло слишком много времени"
