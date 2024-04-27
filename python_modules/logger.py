import json
import logging
import logging.config
import textwrap


class CustomFormatter(logging.Formatter):

    """Логгирование с цветным выводом в зависимости от уровня сообщений."""

    # Коды ANSI для окрашивания текста
    grey = "\x1b[38;21m"
    blue = "\x1b[34m"  # Обновлено для синего цвета
    white = "\x1b[37m"  # Обновлено для белого цвета
    red = "\x1b[31m"  # Обновлено для красного цвета
    reset = "\x1b[0m"  # Сброс цвета текста
    format = "%(name)s - %(asctime)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: white + format + reset,
        logging.WARNING: grey + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + format + reset
    }



    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        formatted = formatter.format(record)
        # Применяем перенос строк к сообщению, если оно слишком длинное
        wrapped = textwrap.fill(formatted, width=100)  # Перенос строк, если длина сообщения больше 100 символов
        return wrapped

def setup_logging():

    def setup_logging_from_file(path_to_config_file):
        with open(path_to_config_file, 'r') as file:
            config = json.load(file)
        logging.config.dictConfig(config)

    # Путь к файлу конфигурации
    path_to_logging_config = 'logging_config.json'

    # Вызов функции настройки логгирования
    setup_logging_from_file(path_to_logging_config)

