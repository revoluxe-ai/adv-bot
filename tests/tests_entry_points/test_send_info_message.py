from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Предполагаем, что в run_send_info_message_to_users_process.py есть функция main или класс MessageSender
# Адаптируйте импорт под реальную структуру модуля
try:
    from run_send_info_message_to_users_process import MessageSender

    class_based = True
except ImportError:
    from run_send_info_message_to_users_process import main

    class_based = False


@pytest.mark.asyncio
async def test_message_sender_initialization():
    """
    Тест проверяет, что класс или функция MessageSender инициализируется корректно
    """
    if class_based:
        # Для класса MessageSender

        # Мокируем зависимости
        with (
            patch(
                "run_send_info_message_to_users_process.get_config"
            ) as mock_get_config,
            patch(
                "run_send_info_message_to_users_process.setup_logging"
            ) as mock_setup_logging,
            patch(
                "run_send_info_message_to_users_process.init_db_connection"
            ) as mock_init_db,
        ):
            # Настраиваем мок-конфиг
            mock_get_config.return_value = {
                "db_connection": "test_connection_string",
                "bot_token": "test_token",
                "log_level": "INFO",
            }

            # Создаем экземпляр MessageSender
            sender = MessageSender()

            # Проверяем, что зависимости были вызваны
            mock_get_config.assert_called_once()
            mock_setup_logging.assert_called_once()
            mock_init_db.assert_called_once()

            # Проверяем, что атрибуты настроены правильно
            assert hasattr(sender, "config"), (
                "У объекта MessageSender должен быть атрибут config"
            )
    else:
        # Для функции main

        # Мокируем функции инициализации
        with (
            patch(
                "run_send_info_message_to_users_process.setup_logging"
            ) as mock_setup_logging,
            patch(
                "run_send_info_message_to_users_process.load_config"
            ) as mock_load_config,
            patch("run_send_info_message_to_users_process.init_db") as mock_init_db,
        ):
            # Настраиваем мок-функции
            mock_load_config.return_value = {
                "db_connection": "test_connection_string",
                "bot_token": "test_token",
                "log_level": "INFO",
            }
            mock_init_db.return_value = MagicMock()

            # Блокируем реальное выполнение
            with patch("asyncio.run"):
                # Импортируем модуль

                # Проверяем, что функции инициализации были вызваны
                mock_setup_logging.assert_called_once()
                mock_load_config.assert_called_once()
                mock_init_db.assert_called_once()


@pytest.mark.asyncio
async def test_message_sender_run_processes_messages():
    """
    Тест проверяет, что метод run обрабатывает сообщения корректно
    """
    if class_based:
        # Для класса MessageSender

        # Создаем экземпляр MessageSender
        sender = MessageSender()

        # Мокируем методы, которые должны вызываться из run
        sender.get_pending_messages = AsyncMock(
            return_value=[
                {"user_id": 123, "message": "Test message 1"},
                {"user_id": 456, "message": "Test message 2"},
            ]
        )
        sender.send_message = AsyncMock()
        sender.mark_message_as_sent = AsyncMock()

        # Вызываем тестируемый метод
        await sender.run()

        # Проверяем, что метод получения сообщений был вызван
        sender.get_pending_messages.assert_called_once()

        # Проверяем, что метод отправки сообщения был вызван для каждого сообщения
        assert sender.send_message.call_count == 2, (
            "Метод send_message должен вызываться для каждого сообщения"
        )

        # Проверяем, что метод пометки сообщения был вызван для каждого сообщения
        assert sender.mark_message_as_sent.call_count == 2, (
            "Метод mark_message_as_sent должен вызываться для каждого сообщения"
        )
    else:
        # Для функции main

        # Мокируем функции
        with (
            patch(
                "run_send_info_message_to_users_process.get_pending_messages",
                new_callable=AsyncMock,
            ) as mock_get_messages,
            patch(
                "run_send_info_message_to_users_process.send_message",
                new_callable=AsyncMock,
            ) as mock_send_message,
            patch(
                "run_send_info_message_to_users_process.mark_message_as_sent",
                new_callable=AsyncMock,
            ) as mock_mark_sent,
        ):
            # Настраиваем мок-функции
            mock_get_messages.return_value = [
                {"user_id": 123, "message": "Test message 1"},
                {"user_id": 456, "message": "Test message 2"},
            ]

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция получения сообщений была вызвана
            mock_get_messages.assert_called_once()

            # Проверяем, что функция отправки сообщения была вызвана для каждого сообщения
            assert mock_send_message.call_count == 2, (
                "Функция send_message должна вызываться для каждого сообщения"
            )

            # Проверяем, что функция пометки сообщения была вызвана для каждого сообщения
            assert mock_mark_sent.call_count == 2, (
                "Функция mark_message_as_sent должна вызываться для каждого сообщения"
            )


@pytest.mark.asyncio
async def test_message_sender_handles_errors():
    """
    Тест проверяет, что MessageSender корректно обрабатывает ошибки при отправке сообщений
    """
    if class_based:
        # Для класса MessageSender

        # Создаем экземпляр MessageSender
        sender = MessageSender()

        # Мокируем методы
        sender.get_pending_messages = AsyncMock(
            return_value=[
                {"user_id": 123, "message": "Test message 1"},
                {"user_id": 456, "message": "Test message 2"},
            ]
        )
        # Метод send_message вызывает исключение для второго сообщения
        sender.send_message = AsyncMock(side_effect=[None, Exception("Test error")])
        sender.mark_message_as_sent = AsyncMock()
        sender.mark_message_as_failed = AsyncMock()

        # Вызываем тестируемый метод
        await sender.run()

        # Проверяем, что метод отправки сообщения был вызван для каждого сообщения
        assert sender.send_message.call_count == 2, (
            "Метод send_message должен вызываться для каждого сообщения"
        )

        # Проверяем, что метод пометки сообщения как отправленного был вызван для первого сообщения
        sender.mark_message_as_sent.assert_called_once_with(
            {"user_id": 123, "message": "Test message 1"}
        )

        # Проверяем, что метод пометки сообщения как не отправленного был вызван для второго сообщения
        sender.mark_message_as_failed.assert_called_once_with(
            {"user_id": 456, "message": "Test message 2"}, "Test error"
        )
    else:
        # Для функции main

        # Мокируем функции
        with (
            patch(
                "run_send_info_message_to_users_process.get_pending_messages",
                new_callable=AsyncMock,
            ) as mock_get_messages,
            patch(
                "run_send_info_message_to_users_process.send_message",
                new_callable=AsyncMock,
            ) as mock_send_message,
            patch(
                "run_send_info_message_to_users_process.mark_message_as_sent",
                new_callable=AsyncMock,
            ) as mock_mark_sent,
            patch(
                "run_send_info_message_to_users_process.mark_message_as_failed",
                new_callable=AsyncMock,
            ) as mock_mark_failed,
            patch("run_send_info_message_to_users_process.log_error") as mock_log_error,
        ):
            # Настраиваем мок-функции
            mock_get_messages.return_value = [
                {"user_id": 123, "message": "Test message 1"},
                {"user_id": 456, "message": "Test message 2"},
            ]
            # Функция send_message вызывает исключение для второго сообщения
            mock_send_message.side_effect = [None, Exception("Test error")]

            # Вызываем тестируемую функцию
            await main()

            # Проверяем, что функция отправки сообщения была вызвана для каждого сообщения
            assert mock_send_message.call_count == 2, (
                "Функция send_message должна вызываться для каждого сообщения"
            )

            # Проверяем, что функция логирования ошибки была вызвана
            mock_log_error.assert_called_once()

            # Проверяем, что функция пометки сообщения как не отправленного была вызвана
            mock_mark_failed.assert_called_once()
