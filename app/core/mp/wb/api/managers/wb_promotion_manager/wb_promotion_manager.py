import typing
import logging

from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager

logger = logging.getLogger(__name__)


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers.promotion import PromotionManager


class WBModifier:
    def __init__(self, promotion_manager: "PromotionManager") -> None:
        self._promotion_manager: "PromotionManager" = promotion_manager

    async def set_minus_phrases_for_adv(
        self,
            adv_id: int,
            nmid: int,
            phrases: list[str],
            update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager
    ) -> None:
        # TODO: WB походу сделал так, что можно ставить отдельно на каждый nmid внутри фразы РК. Надо адаптировать к этому бот
        try:
            await self._promotion_manager.set_minus_phrases(adv_id, nm_id=nmid, phrases=phrases)
        except Exception as e:
            logger.error('Ошибка обновления минус-фраз: %s', exc_info=True)
            raise e
        await update_redis_timestamp_manager.set_one(adv_id=adv_id)
        return None
