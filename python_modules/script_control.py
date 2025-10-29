import os
from typing import Any, Type
from types import TracebackType


class ScriptControl:
    def __init__(self) -> None:
        self.pid_file = "script_pid.txt"

    def __enter__(self) -> Any:
        if os.path.exists(self.pid_file):
            raise Exception("Процесс уже запущен!")
        pid = os.getpid()
        with open(self.pid_file, "w") as f:
            f.write(str(pid))

    def __exit__(self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        # Удаление файла с PID
        os.remove(self.pid_file)
