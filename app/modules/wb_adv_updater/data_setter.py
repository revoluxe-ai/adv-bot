import asyncio
import logging

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.wb_api import WBApi
from app.modules.wb_adv_updater import data_manager, search_advs_manager
from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from app.modules.white_list_updater.backend.white_list_updater import WhiteListUpdater
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)


_sm = get_async_session_maker


class DataSetter:
    def __init__(self, wb_api: WBApi) -> None:
        access = wb_api.wb_access
        self._wb_cabinet = access.wb_cabinet
        self._wb_api = wb_api
        self._client_session = wb_api.client_session

    async def _update_minus_keywords_in_adv(
        self, adv_setting: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        logger.debug(f"Обновляю минус слова для {adv_setting.name}")
        logger.debug(f"Получил ключи для {adv_setting.name}")
        bad_keywords = []
        for keyword in keywords:
            if keyword.status == KeywordStatus.BAD:
                bad_keywords.append(keyword)
                if clusters := keyword.childs_keywords:
                    for cluster in clusters:
                        bad_keywords.append(cluster)

        if len(bad_keywords) > 1000:
            sorted_bad_keywords = sorted(
                bad_keywords, key=lambda kw: kw.views, reverse=True
            )
            bad_keywords = sorted_bad_keywords[:1000]
            over_words_in_company = sorted_bad_keywords[1000:]
            if over_words_in_company:
                logger.debug(
                    f"Не смогу заблокировать ключи {len(over_words_in_company)}"
                )
        bad_phrases = [kw.text for kw in bad_keywords]
        if bad_phrases:
            bad_phrases = list(set(bad_phrases))
            await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
            adv_active_keyword_update_state_manager = (
                AdvActiveKeywordUpdateStateManager()
            )
            logger.debug(f"Обновил минус слова {adv_setting.name} {bad_phrases}")
            await adv_active_keyword_update_state_manager.set_one(adv_setting.adv_id)
        else:
            logger.debug(f"Нет минус слов для {adv_setting.name}")

    async def update_minus_keywords_in_adv(
        self,
        adv_setting: AdvSetting,
        wb_cabinet: WBCabinet,
        keywords: list[CalculatedKeyword] | None = None,
    ) -> None:
        if not keywords:
            fresh_keywords = await get_good_bad_phrases(adv_setting)
            keywords = fresh_keywords
        if wb_cabinet.white_list_update_active:
            white_list_updater = WhiteListUpdater()
            try:
                await white_list_updater.update_white_list(keywords, 20)
            except Exception as e:
                assert self._wb_cabinet
                logger.error(
                    f"Ошибка обновления белого списка для {adv_setting.name},"
                    f"adv_id: {adv_setting.adv_id},"
                    f"shop_id: {self._wb_cabinet.shop_id} "
                    f" {e}",
                    exc_info=True,
                )

            # try:
            #     if best_keyword:
            #         await white_list_updater.update_max_bid(adv_setting, best_keyword)
            # except Exception as e:
            #     logger.error(f'Ошибка обновления максимальной ставки для {adv_setting.name},'
            #                  f'adv_id: {adv_setting.adv_id},'
            #                  f'shop_id: {self._wb_cabinet.shop_id} '
            #                  f' {e}', exc_info=True)
        try:
            await asyncio.gather(
                self._update_minus_keywords_in_adv(
                    adv_setting,
                    keywords,
                ),
                search_advs_manager.update_keyword_phrases_for_search_adv(
                    adv_setting, keywords, self._wb_api.client_session
                ),
            )
        except Exception as e:
            assert self._wb_cabinet
            logger.error(
                f"Ошибка обновления минус слов для {adv_setting.name},"
                f"adv_id: {adv_setting.adv_id},"
                f"shop_id: {self._wb_cabinet.shop_id} "
                f" {e}",
                exc_info=True,
            )

    async def update_minus_keywords(self, adv_settings: list[AdvSetting]) -> None:
        logger.debug("Начинаю обновление минус слов")
        for adv_setting in adv_settings:
            logger.debug(f"Обновляю минус слова для {adv_setting.name}")
            keywords: list[CalculatedKeyword] = await get_good_bad_phrases(adv_setting)
            logger.debug(f"Получил ключи для {adv_setting.name}")
            good_phrases = []
            bad_phrases = []
            for keyword in keywords:
                if keyword.status == KeywordStatus.GOOD:
                    good_phrases.append(keyword.text)
                else:
                    bad_phrases.append(keyword.text)
                    if clusters := keyword.childs_keywords:
                        for cluster in clusters:
                            bad_phrases.append(cluster.text)

            if bad_phrases:
                bad_phrases = list(set(bad_phrases))
                await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
                logger.debug(f"Обновил минус слова {adv_setting.name} {bad_phrases}")
                logger.debug(f"Позитивные слова {good_phrases}")
            else:
                logger.debug(f"Нет минус слов для {adv_setting.name}")
        return
