import asyncio
import logging
import pandas as pd
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.wb_adv_updater import data_manager, search_advs_manager
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from app.modules.white_list_updater.backend.white_list_updater import WhiteListUpdater
from app.my_types import AdvSetting
from app.utils.db.session_maker import get_async_session_maker


logger = logging.getLogger(__name__)


_sm = get_async_session_maker




class DataSetter:
    def __init__(self, access: WBCabinetAccess):
        self._wb_api = WBApi(access)
        self._wb_cabinet = access.wb_cabinet

    async def _update_minus_keywords_in_adv(self, adv_setting: AdvSetting, keywords):
        logger.debug(f'Обновляю минус слова для {adv_setting.name}')
        logger.debug(f'Получил ключи для {adv_setting.name}')
        bad_keywords = []
        for keyword in keywords:
            if keyword.status == KeywordStatus.BAD:
                bad_keywords.append(keyword)
                if clusters := keyword.childs_keywords:
                    for cluster in clusters:
                        bad_keywords.append(cluster)

        if len(bad_keywords) > 1000:
            sorted_bad_keywords = sorted(bad_keywords, key=lambda kw: kw.views, reverse=True)
            bad_keywords = sorted_bad_keywords[:1000]
            over_words_in_company = sorted_bad_keywords[1000:]
            if over_words_in_company:
                 logger.debug(f'Не смогу заблокировать ключи {len(over_words_in_company)}')
        bad_phrases = [kw.text for kw in bad_keywords]
        if bad_phrases:
            bad_phrases = list(set(bad_phrases))
            await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
            adv_active_keyword_update_state_manager = AdvActiveKeywordUpdateStateManager()
            logger.debug(f'Обновил минус слова {adv_setting.name} {bad_phrases}')
            await adv_active_keyword_update_state_manager.set_one(adv_setting.adv_id)
        else:
            logger.debug(f'Нет минус слов для {adv_setting.name}')




    async def update_minus_keywords_in_adv(self,
                                           adv_setting: AdvSetting,
                                           wb_cabinet: WBCabinet,
                                           keywords: list[CalculatedKeyword] = None):
        if not keywords:
             keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)
        if wb_cabinet.white_list_update_active:
            white_list_updater = WhiteListUpdater()
            try:
                best_keyword = await white_list_updater.update_white_list(keywords, 10)
            except Exception as e:
                logger.error(f'Ошибка обновления белого списка для {adv_setting.name},'
                             f'adv_id: {adv_setting.adv_id},'
                             f'shop_id: {self._wb_cabinet.shop_id} '
                             f' {e}', exc_info=True)
                best_keyword = None
            try:
                if best_keyword:
                    await white_list_updater.update_max_bid(adv_setting, best_keyword)
            except Exception as e:
                logger.error(f'Ошибка обновления максимальной ставки для {adv_setting.name},'
                             f'adv_id: {adv_setting.adv_id},'
                             f'shop_id: {self._wb_cabinet.shop_id} '
                             f' {e}', exc_info=True)
        try:
            await asyncio.gather(self._update_minus_keywords_in_adv(adv_setting, keywords),
                                 search_advs_manager.set_keyword_phrases_for_search_adv(adv_setting, keywords),)
        except Exception as e:
            logger.error(f'Ошибка обновления минус слов для {adv_setting.name},'
                         f'adv_id: {adv_setting.adv_id},'
                         f'shop_id: {self._wb_cabinet.shop_id} '
                         f' {e}', exc_info=True)



    async def update_minus_keywords(self, adv_settings: list[AdvSetting]):
        logger.debug('Начинаю обновление минус слов')
        for adv_setting in adv_settings:
            logger.debug(f'Обновляю минус слова для {adv_setting.name}')
            keywords: list[CalculatedKeyword] = await data_manager.get_good_bad_phrases(adv_setting)
            logger.debug(f'Получил ключи для {adv_setting.name}')
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
                logger.debug(f'Обновил минус слова {adv_setting.name} {bad_phrases}')
                logger.debug(f'Позитивные слова {good_phrases}')
            else:
                logger.debug(f'Нет минус слов для {adv_setting.name}')
        return


    def _print_keywords(self, df: pd.DataFrame, df_fact: pd.DataFrame, nmid, min_ctr: float):
        full_goods = []
        full_bads = []
        for _, row in df.iterrows():
            keyword = row.keyword
            clicks = df_fact.loc[(df_fact['keyword'] == keyword) & (df_fact['nmid'] == nmid), 'clicks'].item()
            views = df_fact.loc[(df_fact['keyword'] == keyword) & (df_fact['nmid'] == nmid), 'views'].item()
            nmid = row.nmid
            predict_ctr = row.predict_ctr
            real_ctr = round(clicks / views, 2)
            str_ = f'{keyword} ({clicks}) ({views}) ({real_ctr}) ({round(predict_ctr, 3)})'
            if predict_ctr >= min_ctr:
                full_goods.append(str_)
            else:
                full_bads.append(str_)
        goods = ', '.join(full_goods)
        bads = ', '.join(full_bads)

        logger.info(f'{str(nmid)} Позитивные ключи: {goods}')
        logger.info(f'{str(nmid)} Негативные ключи: {bads}')