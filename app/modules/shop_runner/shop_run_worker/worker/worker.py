import asyncio
import logging

from aiohttp import ClientSession

from ..consts import default_tll
from ..redis_manager import RedisShopManager
from ...run_process_func import run_shop_task

logger = logging.getLogger(__name__)

from typing import Callable


class ShopWorker:
    def __init__(self, session: ClientSession):
        self._tasks = {}
        self._client_session = session

    def _on_shop_task_done(
        self, shop_id: str, redis_manager: RedisShopManager
    ) -> Callable[[asyncio.Task[None]], object]:
        def callback(task: asyncio.Task[None]) -> object:
            if exc := task.exception():
                logger.exception(
                    f"Задача магазина {shop_id} завершилась с ошибкой: {exc}"
                )
            asyncio.create_task(self._cleanup_shop(shop_id, redis_manager))
            return None  # важно вернуть object (в данном случае None)

        return callback

    async def _cleanup_shop(
        self, shop_id: str, redis_manager: RedisShopManager
    ) -> None:
        await redis_manager.remove_shops([shop_id])
        logger.debug(f"Магазин {shop_id} удалён из активных после завершения задачи")

    async def update_active_shop_update_tasks_run(self) -> None:
        tasks = self._tasks
        redis_manager = RedisShopManager(default_tll)

        while True:
            new_free_shop_id = await redis_manager.get_next_free_shop_id()
            if not new_free_shop_id:
                await asyncio.sleep(5)
                continue

            if new_free_shop_id not in tasks:
                task: asyncio.Task[None] = asyncio.create_task(
                    run_shop_task(new_free_shop_id, self._client_session)
                )
                task.add_done_callback(
                    self._on_shop_task_done(new_free_shop_id, redis_manager)
                )
                tasks[new_free_shop_id] = task
                logger.debug(f"Процесс обновления магазина {new_free_shop_id} запущен")
            else:
                shop_id = new_free_shop_id
                await redis_manager.renew_shop_ttl(shop_id)
                task = tasks[shop_id]
                if task.done():
                    if exc := task.exception():
                        logger.exception(
                            f"Не обработанная ошибка выполнения задачи магазина: {exc}"
                        )
                    del tasks[shop_id]
            await asyncio.sleep(1)
