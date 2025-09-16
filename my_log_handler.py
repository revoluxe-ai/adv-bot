import logging





class ScriptHandler(logging.Handler):
    def emit(self, record):
        log_message = self.format(record)
        # Выполнение скрипта
        # print(f"Запуск скрипта из логгера: {log_message}")
        # Тут можно добавить вызов любого скрипта
        # execute_script(log_message)