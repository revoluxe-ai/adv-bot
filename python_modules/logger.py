import logging

class SimpleStringFormatter(logging.Formatter):
    def format(self, record) -> str:
        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        # Формат: ВРЕМЯ - УРОВЕНЬ - ИМЯ ЛОГГЕРА: НОМЕР СТРОКИ
        result = f"{log_time} - {record.levelname} - {record.name}:{record.lineno} - {record.getMessage()}"
        if record.exc_info:
            result += f"\n{self.formatException(record.exc_info)}"
        return result


def setup_logging(settings=None) -> None:
    if not settings:
        from app import settings
    """Настройка логирования"""
    try:
        logger = logging.getLogger()
        logger_level = settings.LOG_LEVEL
        logger.setLevel(logger_level)

        # Удаляем все существующие обработчики
        logger.handlers.clear()

        # Добавляем обработчик для вывода в stdout с нужным форматом
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(SimpleStringFormatter())
        logger.addHandler(stream_handler)

        logging.info("Логирование настроено успешно!")
    except Exception as e:
        logging.error(f"Ошибка при настройке логирования: {str(e)}")
