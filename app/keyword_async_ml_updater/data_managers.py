import asyncio
import logging
from collections import defaultdict
from app.my_types import WBUserCabinet
import sqlalchemy.orm
from sqlalchemy import select

from app.wildberries.data_classes.card_from_wb import CardFromWB
import pandas as pd
from app.wildberries.data_classes.adv import AdvType, Adv
from app.wildberries.data_classes.wb_shop import WbShop
from app.keyword_async_ml_updater.ABC_manager import AbcManager
from app.my_types import AdvSetting
from app.wildberries.api import WBApi

from app.NeoDataScience.driver import DataScience


logger = logging.getLogger(__name__)

class DataGetter(AbcManager):

    def __init__(self):
        self._gds = DataScience()

    @staticmethod
    def normalize_df_data(df: pd.DataFrame, param_for_norm: str) -> pd.DataFrame:
        max_ = df[param_for_norm].max()
        min_ = df[param_for_norm].min()
        return (df[param_for_norm] - min_) / (max_ - min_)


    async def get_full_df(self, shops: list[WBUserCabinet]):
        shops_df_tasks = [self.get_df_for_shop(shop) for shop in shops]
        shops_dfs = await asyncio.gather(*shops_df_tasks)
        df = pd.concat(shops_dfs)
        return df



    @staticmethod
    def __get_df_from_date_answer(answer, company):
        data_dict = defaultdict(list)
        for date_data in answer:
            stat = date_data['stat']
            for keyword_stat in stat:
                keyword = keyword_stat['keyword']
                views = keyword_stat['views']
                clicks = keyword_stat['clicks']
                spend = keyword_stat['sum']
                if views > 0:
                    data_dict['keyword'].append(keyword)
                    data_dict['views'].append(views)
                    data_dict['clicks'].append(clicks)
                    data_dict['spend'].append(spend)

        df = pd.DataFrame(data_dict)
        df = df.groupby(['keyword']).agg({'views': 'sum', 'clicks': 'sum', 'spend': 'sum'})
        df = df.reset_index()
        df['adv_id'] = company.advertId
        df['nmids'] = [company.nmids] * (len(df))
        return df


    async def get_df_for_shop(self, shop: WBUserCabinet) -> pd.DataFrame:
        wb_api = WBApi(shop)
        companies = await wb_api.advert.get_all_adv_companies()
        keywords_dfs = []
        for company in companies:
            logger.debug('Начинаю получать ключи')
            answer = await wb_api.advert.get_keywords_stat(company)
            logger.debug('Ключи получены')
            await asyncio.sleep(10)
            if answer == []:
                continue
            df = self.__get_df_from_date_answer(answer, company)
            keywords_dfs.append(df)
        if keywords_dfs == []:
            return pd.DataFrame()
        df = pd.concat(keywords_dfs)
        return df


    async def get_cards_for_shop(self, shop: WBUserCabinet):
        wb_api = WBApi(shop)
        cards: list[CardFromWB] = await wb_api.advert.get_cards()
        for card in cards:
            card.shop_name = shop.name
        return cards

    def get_nmid_offer_id_df(self, cards: list[CardFromWB]) -> pd.DataFrame:
        dict_ = defaultdict(list)
        for card in cards:
            dict_['nmid'].append(card.nmid)
            dict_['offer_id'].append(card.offer_id)
            dict_['shop_name'].append(card.shop_name)
        nmid_offer_id_df = pd.DataFrame(dict_)
        return nmid_offer_id_df

    async def listProgress(self, jobid):
        result = await self._gds.get_status_job(jobid)
        return result





class DataSetter:
    def __init__(self, shop: WbShop, async_sm: sqlalchemy.orm.sessionmaker):
        self._wb_api = async_WBApi(shop)
        self._getter = DataGetter()
        self._async_sm = async_sm

    async def update_minus_keywords(self, wb_api, df_predict, df_fact):
        all_companies = await wb_api.get_all_adv_companies()
        for n, company in enumerate(all_companies):
            if company.adv_type == AdvType.KEYWORD_TEST:
                async with self._async_sm() as session:
                    stmt = select(AdvSetting).where(AdvSetting.nmid == nmid,
                                                    AdvSetting.bot_active == True)
                    result = await session.execute(stmt)
                    adv_setting = result.scalars().first()
                    if not adv_setting:
                        logger.debug(f'Кампания {company.name} не активна')
                        continue
                min_ctr = adv_setting.min_ctr/100
                logger.info('Минимальный ctr в настройках: %s',min_ctr)
                shop_df = df_predict[df_predict['nmid'] == nmid]
                bad_phrases = list(shop_df[(shop_df['predict_ctr'] < min_ctr)]['keyword'].unique())
                self._print_keywords(shop_df, df_fact, nmid, min_ctr)

                while True:
                    try:
                         await wb_api.set_minus_phrases(company, bad_phrases)
                         break
                    except Exception as exc:
                        logger.error('Ошибка обновления минус-фраз: %s', exc)
                        await asyncio.sleep(30)
                await asyncio.sleep(30)

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




