import os
import asyncio
import logging
import sys
import dotenv

dotenv.load_dotenv()  # ранняя загрузка .env

_debug_enabled = os.getenv("PREDICT_CTR_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
_level = logging.DEBUG if _debug_enabled else logging.INFO

# Принудительная ручная конфигурация логгера
root = logging.getLogger()
for h in list(root.handlers):
    root.removeHandler(h)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
root.addHandler(handler)
root.setLevel(_level)

logger = logging.getLogger("run")
logger.info("Инициализация логирования (level=%s debug=%s)", logging.getLevelName(_level), _debug_enabled)

from app.server import run_server_async  # noqa: E402


async def run() -> None:
    logger.info("Запуск run() -> server loop")
    await run_server_async()
    logger.info("Server loop завершён")


if __name__ == '__main__':
    logger.debug('__main__ entry, debug=%s', _debug_enabled)
    asyncio.run(run())
