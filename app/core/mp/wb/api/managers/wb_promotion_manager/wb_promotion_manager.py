import asyncio
import typing
from collections.abc import Awaitable
if typing.TYPE_CHECKING:
   from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
import logging


logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import PromotionManager


class WBModifier:
    def __init__(self, promotion_manager: "PromotionManager") -> None:
        self._promotion_manager: "PromotionManager" = promotion_manager

    async def set_minus_phrases_for_adv(
        self, complex_adv: "ComplexAdv", phrases: list[str]
    ) -> None:
        # TODO: WB походу сделал так, что можно ставить отдельно на каждый nmid внутри фразы РК. Надо адаптировать к этому бот
        nmid = complex_adv.main_nmid
        update_tasks: list[Awaitable[None]] = []
        # if adv_id := complex_adv.auto_adv_id:
        #     task: Awaitable[None] = self._promotion_manager.set_minus_phrases(
        #     adv_id, nmid, phrases
        # )
        #     update_tasks.append(task)
        if adv_id := complex_adv.search_adv.adv_id:
            task: Awaitable[None] = self._promotion_manager.set_minus_phrases(
                adv_id, nmid, phrases
            )
            update_tasks.append(task)

        results: list[None | BaseException] = await asyncio.gather(*update_tasks,
                                                               return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(result)

