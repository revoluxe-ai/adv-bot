import os





class ScriptControl:
    def __init__(self):
        self.pid_file = 'script_pid.txt'

    def __enter__(self):
        if os.path.exists(self.pid_file):
            Exception('Процесс уже запущен!')
        pid = os.getpid()
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Удаление файла с PID
        os.remove(self.pid_file)

