import logging
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    KeywordStatus,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

logger = logging.getLogger(__name__)


class MinusPhraseManager:
    def __init__(self, wb_api_manager_hub: WBManagerHub):
        self._wb_api = wb_api_manager_hub

    async def update_minus_phrases(self, complex_adv: ComplexAdv) -> None:
        try:
            await self._update_minus_phrases(complex_adv)
        except Exception as e:
            logger.error(
                "Ошибка обновления минус фраз для shop_id: %s, adv_id: %s, ошибка: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
                e,
                exc_info=True,
            )
            raise e


    async def _update_minus_phrases(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        bad_phrases = [
            kw.text for kw in keywords if kw.status == KeywordStatus.BAD
        ]

        if not bad_phrases:
            logger.debug(
                "Нет минус фраз для обновления для shop_id: %s, adv_id: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
            )
            return

        # API лимит - 1000 фраз. Берем только "плохие"
        minus_phrases_to_send = list(bad_phrases)[:1000]

        await self._wb_api.wb_modifier.set_minus_phrases_for_adv(
            complex_adv=complex_adv,
            phrases=minus_phrases_to_send,
        )

        logger.debug(
            "Минус-фразы успешно обновлены для shop_id: %s, adv_id: %s, фразы: %s",
            complex_adv.shop_id,
            complex_adv.adv_id,
            minus_phrases_to_send,
        )
