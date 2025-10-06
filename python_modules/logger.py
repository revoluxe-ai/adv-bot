import logging

from app import settings


class SimpleStringFormatter(logging.Formatter):
    def format(self, record) -> str:
        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        # Формат: ВРЕМЯ - УРОВЕНЬ - ИМЯ ЛОГГЕРА: НОМЕР СТРОКИ
        result = f"{log_time} - {record.levelname} - {record.name}:{record.lineno} - {record.getMessage()}"
        if record.exc_info:
            result += f"\n{self.formatException(record.exc_info)}"
        return result


def _normalize_log_level(value: str) -> int:
    """Убирает кавычки и пробелы, приводит к верхнему регистру и конвертирует в числовой уровень.
    Возвращает logging.ERROR по умолчанию при неизвестном значении."""
    if not isinstance(value, str):
        try:
            return int(value)
        except Exception:
            return logging.ERROR

    level = value.strip().strip('"').strip("'").upper()
    # logging.getLevelName возвращает число для известных имён уровней
    numeric = logging.getLevelName(level)
    if isinstance(numeric, int):
        return numeric
    # Попробуем преобразовать как число
    try:
        return int(level)
    except Exception:
        return logging.ERROR


def setup_logging() -> None:
    """Настройка логирования"""
    try:
        logger = logging.getLogger()
        raw_level = settings.LOG_LEVEL
        logger_level = _normalize_log_level(raw_level)
        # Устанавливаем уровень для root-логгера
        logger.setLevel(logger_level)

        # Удаляем все существующие обработчики
        logger.handlers.clear()

        # Добавляем обработчик для вывода в stdout с нужным форматом
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(SimpleStringFormatter())
        # Устанавливаем уровень обработчика тоже, чтобы он не пропускал сообщения ниже уровня
        stream_handler.setLevel(logger_level)
        logger.addHandler(stream_handler)

        logging.log(logger_level, "Логирование настроено успешно!")
    except Exception as e:
        # В явном исключении используем logging.error — если конфиг уже сломан, по крайней мере увидим ошибку
        logging.error(f"Ошибка при настройке логирования: {str(e)}")
