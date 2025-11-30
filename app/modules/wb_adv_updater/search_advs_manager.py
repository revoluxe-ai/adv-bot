import asyncio
import logging
from collections.abc import Iterable

from aiohttp import ClientSession

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager

logger = logging.getLogger(__name__)


# async def __update_search_adv_keywords_statistics(adv_setting):
#     wb_cabinet_id = adv_setting.wb_cabinet_id
#     access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
#     api = WBApi(access)
#     try:
#         search_adv_id = adv_setting.search_adv_id
#         keyword_stats = await api.advert.get_search_keywords_stat(search_adv_id)
#         await data_manager.update_search_adv_keywords_stat(adv_setting, keyword_stats)
#
#     except Exception as e:
#         logger.error(
#             f"Ошибка получения статистики по ключам для {adv_setting.name}: {e}",
#             exc_info=True,
#         )
#         return


# async def _update_search_advs_keywords_statistics(adv_settinds):
#     tasks = []
#     for adv_setting in adv_settinds:
#         task = asyncio.create_task(__update_search_adv_keywords_statistics(adv_setting))
#         tasks.append(task)
#     for task in tasks:
#         try:
#             await task
#         except:
#             logger.error(
#                 "Ошибка обновления статистики по ключам для поисковых РК", exc_info=True
#             )


async def set_fix_keywords_phrases_for_search_adv(
    adv_setting, keywords, client_session: ClientSession
):
    search_adv_id = adv_setting.search_adv_id
    adv_update_state_manager = AdvActiveKeywordUpdateStateManager()
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    api = WBApi(access, client_session)
    if not keywords:
        return
    keywords = sorted(keywords, key=lambda kw: kw.rating_by_predict_ctr, reverse=True)
    texts = [
        keyword.text for keyword in keywords if keyword.status == KeywordStatus.GOOD
    ][:100]

    texts = [text.replace('"', "") for text in texts]
    try:
        await api.advert.set_pluse_status_in_search_adv(search_adv_id, True)
        await api.advert.set_search_keywords(search_adv_id, texts)
        await adv_update_state_manager.set_one(search_adv_id)
    except Exception as e:
        logger.error(
            f"Ошибка установки фраз для {adv_setting.name}: {e}", exc_info=True
        )
        del e
        return


async def set_minus_keywords_for_search_adv(
    adv_setting, keywords, client_session: ClientSession
):
    search_adv_id = adv_setting.search_adv_id
    adv_update_state_manager = AdvActiveKeywordUpdateStateManager()
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    api = WBApi(access, client_session)
    if not keywords:
        return
    keywords = sorted(keywords, key=lambda kw: kw.rating_by_predict_ctr, reverse=False)
    texts = [
        keyword.text for keyword in keywords if keyword.status == KeywordStatus.BAD
    ]
    texts = texts[:1000]
    if texts:
        texts = [text.replace('"', "") for text in texts]
        texts = set(texts)
        # TODO: Тут был метод установки фикс-фраз, который не работал и вызывал ошибку всего процесса
        try:
            await api.advert.set_minus_phrase_for_search_adv(search_adv_id, texts)
            await adv_update_state_manager.set_one(search_adv_id)
        except Exception as e:
            logger.error(
                f"Ошибка установки минус-фраз для аукциона {adv_setting.adv_id}: {e}",
                exc_info=True,
            )
            del e
            return


async def update_keyword_phrases_for_search_adv(
    adv_setting: AdvSetting, keywords: Iterable[CalculatedKeyword], client_session
):
    search_adv_id = adv_setting.search_adv_id
    if not search_adv_id:
        return None
    await set_minus_keywords_for_search_adv(adv_setting, keywords, client_session)


async def _set_keyword_phrases_for_search_advs(adv_settinds, client_session) -> None:
    tasks = []
    for adv_setting in adv_settinds:
        keywords = await get_good_bad_phrases(adv_setting)
        task = asyncio.create_task(
            update_keyword_phrases_for_search_adv(adv_setting, keywords, client_session)
        )
        tasks.append(task)
    for task in tasks:
        try:
            await task
        except:
            logger.error("Ошибка установки фраз для поисковых РК", exc_info=True)
