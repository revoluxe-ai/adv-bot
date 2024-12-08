import docker
import time
from python_modules.logger import setup_logging
import logging


setup_logging()

logging = logging.getLogger(__name__)

class PriorityManager:
    def __init__(self):
        self.client = docker.from_env()
        self.bot = self.client.containers.get('wb_bot')
        self.backend = self.client.containers.get('adv_wb_bot_backend')
        self.activity_threshold = 30  # Процент нагрузки на CPU, при котором бот считается активным
        self.check_interval = 0.5  # Интервал проверки активности

    def calculate_cpu_usage(self, stats):
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        num_cores = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])

        if system_delta > 0 and num_cores > 0:
            cpu_percentage = (cpu_delta / system_delta) * num_cores * 100
        else:
            cpu_percentage = 0
        return cpu_percentage

    def check_activity(self):
        try:
            stats = self.bot.stats(stream=False)
            cpu_usage = self.calculate_cpu_usage(stats)
            return cpu_usage > self.activity_threshold
        except Exception as e:
            logger.error(f"Error checking activity: {e}", exc_info=True)
            return False

    def run(self):
        while True:
            try:
                if self.check_activity():
                    # Бот активен
                    self.bot.update(cpu_shares=8192)  # ~85% CPU
                    self.backend.update(cpu_shares=1024)  # ~10% CPU
                else:
                    # Бот неактивен
                    self.bot.update(cpu_shares=1024)  # ~10% CPU
                    self.backend.update(cpu_shares=8192)  # ~85% CPU
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in run loop: {e}")
                time.sleep(5)



if __name__ == "__main__":
    manager = PriorityManager()
    manager.run()