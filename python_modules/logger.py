import json
import logging
import logging.config
import textwrap
import platform

system_name = platform.system()
print(system_name)
logging_setup_done = False  # Флаг для проверки, было ли уже выполнено настройка логгирования

class CustomFormatter(logging.Formatter):
    """Логгирование с цветным выводом в зависимости от уровня сообщений."""
    grey = "\x1b[38;21m"
    blue = "\x1b[34m"  # Синий цвет
    white = "\x1b[37m"  # Белый цвет
    red = "\x1b[31m"  # Красный цвет
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
        log_fmt = self.FORMATS.get(record.levelno, self.format)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        formatted = formatter.format(record)
        wrapped = textwrap.fill(formatted, width=100)  # Перенос строк
        return wrapped

def setup_logging():
    global logging_setup_done

    if logging_setup_done:
        return

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if system_name == 'Linux':
        from systemd.journal import JournalHandler
        journal_handler = JournalHandler()
        journal_handler.setLevel(logging.DEBUG)
        formatter = CustomFormatter(fmt="%(name)s - %(asctime)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s",
                                    datefmt="%Y-%m-%d %H:%M:%S")
        journal_handler.setFormatter(formatter)
        logger.addHandler(journal_handler)
    else:
        def setup_logging_from_file(path_to_config_file):
            with open(path_to_config_file, 'r') as file:
                config = json.load(file)
            logging.config.dictConfig(config)

        path_to_logging_config = 'logging_config.json'
        setup_logging_from_file(path_to_logging_config)

    logging_setup_done = True
