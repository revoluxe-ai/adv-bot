import asyncio
import logging
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import KeywordStatus, CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_adv_updater import data_manager


logger = logging.getLogger(__name__)


async def __update_search_adv_keywords_statistics(adv_setting):
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    api = WBApi(access)
    try:
        search_adv_id = adv_setting.search_adv_id
        keyword_stats = await api.advert.get_search_keywords_stat(search_adv_id)
        await data_manager.update_search_adv_keywords_stat(adv_setting, keyword_stats)

    except Exception as e:
        logger.error(f'Ошибка получения статистики по ключам для {adv_setting.name}: {e}', exc_info=True)
        return




async def _update_search_advs_keywords_statistics(adv_settinds):
    tasks = []
    for adv_setting in adv_settinds:
        task = asyncio.create_task(__update_search_adv_keywords_statistics(adv_setting))
        tasks.append(task)
    for task in tasks:
        try:
            await task
        except:
            logger.error('Ошибка обновления статистики по ключам для поисковых РК', exc_info=True)




async def _set_keyword_phrases_for_search_adv(adv_setting):
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    api = WBApi(access)
    keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)
    if not keywords:
        return
    keywords = sorted(keywords, key=lambda kw: kw.rating_by_predict_ctr, reverse=True)
    texts = [keyword.text for keyword in keywords if keyword.status == KeywordStatus.GOOD][:100]

    texts = [text.replace('"', '') for text in texts]
    try:
        search_adv_id = adv_setting.search_adv_id
        await api.advert.set_pluse_status_in_search_adv(search_adv_id, True)
        await api.advert.set_search_keywords(search_adv_id, texts)
    except Exception as e:
        logger.error(f'Ошибка установки фраз для {adv_setting.name}: {e}', exc_info=True)
        return

async def _set_keyword_phrases_for_search_advs(adv_settinds):
    tasks = []
    for adv_setting in adv_settinds:
        task = asyncio.create_task(_set_keyword_phrases_for_search_adv(adv_setting))
        tasks.append(task)
    for task in tasks:
        try:
            await task
        except:
            logger.error('Ошибка установки фраз для поисковых РК', exc_info=True)


async def _update_cpm_in_search_advs(adv_settinds: list[AdvSetting]):
    for adv in adv_settinds:
        try:
            wb_cabinet_id = adv.wb_cabinet_id
            access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
            api = WBApi(access)
            search_adv_id = adv.search_adv_id
            cpm = await data_manager._get_cpm_by_nmid(adv.nmids[0])
            if not cpm:
                cpm = adv.max_cpm
            if cpm < 150:
                cpm = 150
        except Exception as e:
             logger.error(f'Ошибка получения CPM для {adv.name}: {e}', exc_info=True)
             return
        try:
             await api.advert.set_search_cpm(search_adv_id, cpm)
        except Exception as e:
             logger.error(f'Ошибка установки CPM для {adv.name}: {e}', exc_info=True)
             return



async def update_search_advs_module_run():
    while True:
        try:
            adv_settinds: list[AdvSetting] = await data_manager.get_active_search_advs()
            await asyncio.gather(
                _set_keyword_phrases_for_search_advs(adv_settinds),
            )
        except:
            logger.error('Ошибка обновления статистики по ключам для поисковых РК', exc_info=True)
        finally:
            await asyncio.sleep(0)
