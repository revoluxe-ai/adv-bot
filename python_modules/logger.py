import logging
import os
import datetime
import platform
import logging

class SimpleStringFormatter(logging.Formatter):
    def format(self, record):
        # Включаем текущее время в формат
        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        result = f"{log_time} - {record.levelname} - {record.name} - {record.getMessage()} ({record.pathname}:{record.lineno})"
        if record.exc_info:
            result += f"\n{self.formatException(record.exc_info)}"
        return result

def setup_logging():
    """Настройка логирования"""
    try:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # Удаляем все существующие обработчики
        logger.handlers.clear()

        # Добавляем обработчик для вывода в stdout с нужным форматом
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(SimpleStringFormatter())
        logger.addHandler(stream_handler)

        logging.info("Логирование настроено успешно!")
    except Exception as e:
        logging.error(f"Ошибка при настройке логирования: {str(e)}")