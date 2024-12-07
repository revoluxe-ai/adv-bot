import logging
import pandas as pd
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.wb_adv_updater import data_manager
from app.my_types import AdvSetting
from app.utils.db.session_maker import get_async_session_maker


logger = logging.getLogger(__name__)


_sm = get_async_session_maker




class DataSetter:
    def __init__(self, access: WBCabinetAccess):
        self._wb_api = WBApi(access)
        self._wb_cabinet = access.wb_cabinet

    async def _update_minus_keywords_in_adv(self, adv_setting: AdvSetting):
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




    async def update_minus_keywords_in_adv(self, adv_setting: AdvSetting):
        try:
            await self._update_minus_keywords_in_adv(adv_setting)
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