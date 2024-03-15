import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, NamedTuple
from aiocache import cached_stampede
from aiocache.decorators import cached

import numpy as np
import pydantic

import app
from app.keyword_async_ml_updater.models import KeywordFeature
from app.telegram_bot.models import User
from app.wildberries.data_classes.keywordstat_from_db import KeywordStatFromDB
from session_maker import get_async_session_maker
from sqlalchemy.orm import selectinload, joinedload

from app.my_types import WBUserCabinet
import sqlalchemy.orm
from sqlalchemy import select, and_, func

from app.wildberries.data_classes.card_from_wb import CardFromWB
import pandas as pd
from app.wildberries.data_classes.adv import AdvType, Adv
from app.wildberries.data_classes.wb_shop import WbShop
from app.keyword_async_ml_updater.ABC_manager import AbcManager
from app.my_types import AdvSetting
from app.wildberries.api import WBApi

from app.NeoDataScience.driver import DataScience
from app.wildberries.models import KeywordSetting, AdvKeyword, WBCategory, WBCard, WBCabinet

logger = logging.getLogger(__name__)



_sm = get_async_session_maker()


async def get_keyword_statistic(session, adv_setting: AdvSetting, hard_statuses: list[int] = None)->list[KeywordStatFromDB]:
    today = datetime.now().date()
    pass_days = adv_setting.pass_days
    base_stmt = (
        select(
            AdvKeyword.text.label("keyword_text"),
            func.sum(AdvKeyword.views).label("total_views"),
            func.sum(AdvKeyword.spend).label("total_spend"),
            func.sum(AdvKeyword.clicks).label("total_clicks")  # Используйте total_clicks для суммы кликов
        )
        .join(KeywordSetting, AdvKeyword.keyword_setting_id == KeywordSetting.id)
        .where(AdvKeyword.date >= today - timedelta(days=pass_days))

    )
    if hard_statuses:
        # Фильтрация по hard_statuses и adv_setting_id и добавление группировки
        stmt = base_stmt.where(
            and_(
                KeywordSetting.hard_status.in_(hard_statuses),
                KeywordSetting.adv_setting_id == adv_setting.id
            )
        )
    else: stmt = base_stmt.where(KeywordSetting.adv_setting_id == adv_setting.id)


    # Группировка по тексту ключевых слов и идентификатору настройки рекламной кампании вне зависимости от условия
    stmt = stmt.group_by(AdvKeyword.text, KeywordSetting.adv_setting_id)

    result = await session.execute(stmt)
    rows = result.all()  # Получение всех результатов запроса

    keyword_stats = []
    for row in rows:
        text = row.keyword_text
        if text:
            keyword_stat = KeywordStatFromDB(
                row.keyword_text,
                min(row.total_clicks, row.total_views) if row.total_clicks and row.total_views else 0,
                row.total_views or 0,
                row.total_spend or 0,
            )
            keyword_stats.append(keyword_stat)


    return keyword_stats



#
# async def get_keyword_statistic(session, keyword_setting: KeywordSetting):
#     today = datetime.now().date()
#     pass_days = keyword_setting.adv_setting.pass_days
#     stmt = (
#         select(
#             func.sum(AdvKeyword.clicks).label("total_clicks"),
#             func.sum(AdvKeyword.views).label("total_views"),
#             func.sum(AdvKeyword.spend).label("total_spend"),
#             func.greatest(func.sum(AdvKeyword.clicks), func.sum(AdvKeyword.views)).label("adjusted_clicks")
#         )
#         .join(KeywordSetting, AdvKeyword.keyword_setting_id == KeywordSetting.id)  # Явное указание соединения
#         .where(
#                 AdvKeyword.date >= today - timedelta(days=pass_days)
#         )
#     )
#
#     result = await session.execute(stmt)
#     total_clicks, total_views, total_spend, adjusted_clicks = result.one()
#     if total_views is None:
#         total_views = 0
#         total_clicks = 0
#         total_spend = 0
#
#     # Исправляем клики, если они превышают просмотры
#     adjusted_clicks = min(total_clicks, total_views)
#     return adjusted_clicks, total_views, total_spend


async def get_global_super_wb_user_cabinet(shop_id_filter: list[str] = None) -> WBUserCabinet:
    async with _sm() as session:
        stmt = select(User).options(selectinload(User.wb_tokens))
        result = await session.execute(stmt)
        users: list[User] = result.unique().scalars().all()
        all_tokens = [wb_token for user in users for wb_token in user.wb_tokens]
        super_user = User()
        super_user.wb_tokens = all_tokens
        wb_user_cabinet = WBUserCabinet()
        wbcabinet = WBCabinet()
        wb_user_cabinet.wb_cabinet = wbcabinet
        wb_user_cabinet.user = super_user
        return wb_user_cabinet





async def get_wb_category_to_keywordstat_list(session) -> defaultdict[WBCategory, list[KeywordStatFromDB]]:
    stmt = select(AdvSetting).options(
        selectinload(AdvSetting.adv_keywords),
        selectinload(AdvSetting.keyword_settings),
        selectinload(AdvSetting.wb_cards)
    )

    result = await session.execute(stmt)
    adv_settings: list[AdvSetting] = result.unique().scalars().all()
    wb_category_to_keywordstat_list = defaultdict(list)
    for adv_setting in adv_settings:
        wb_category = await get_wb_category(adv_setting, session)
        keyword_stats = await get_keyword_statistic(session, adv_setting,[2])
        for keyword_stat in keyword_stats:
            if keyword_stat.views:
                wb_category_to_keywordstat_list[wb_category].append(keyword_stat)
    return wb_category_to_keywordstat_list



async def get_parent_id_categories_subcategories_list() -> defaultdict[Any, list[app.my_types.Subcategory]]:
    user_cabinet = await get_global_super_wb_user_cabinet()
    wb_api = WBApi(user_cabinet)
    subcategories: list[app.my_types.Subcategory] = await wb_api.content.get_subcategories()
    parent_categories = defaultdict(list)
    for category in subcategories:
        parent_categories[category.parentID].append(category)
    parent_categories_subcategories_list = parent_categories
    return parent_categories_subcategories_list


@cached_stampede(ttl=60*60*3, key="get_category_name_min_ctr_final_data")
async def get_category_name_min_ctr_final_data(session) -> dict[int, float]:
    parent_categories_to_subcategories_list = await get_parent_id_categories_subcategories_list()
    category_name_to_parent_id = {}
    for parent_id, subcategories in parent_categories_to_subcategories_list.items():
        for subcategory in subcategories:
            category_name_to_parent_id[subcategory.subjectName] = parent_id

    wb_category_to_keywordstat_list = await get_wb_category_to_keywordstat_list(session)
    parent_category_to_keywordstat_list = {}
    for wb_category, keywordstat_list in wb_category_to_keywordstat_list.items():
        wb_category_name = wb_category.wb_category_name
        parentId = category_name_to_parent_id[wb_category_name]
        if parentId not in parent_category_to_keywordstat_list:
            parent_category_to_keywordstat_list[parentId] = []
        parent_category_to_keywordstat_list[parentId].extend(keywordstat_list)

    global_keywordstats_list = []
    for keywordstat_list in parent_category_to_keywordstat_list.values():
        global_keywordstats_list.extend(keywordstat_list)

    final_wb_category_name_to_min_ctr = {}
    percentile_value = 10
    for wb_category, keywordstat_list in wb_category_to_keywordstat_list.items():
        ctr_percentile = np.percentile([keywordstat.ctr for keywordstat in keywordstat_list],
                                       percentile_value)  # Исправлена переменная здесь
        wb_category_name = wb_category.wb_category_name
        if ctr_percentile == 0:
            parentId = category_name_to_parent_id[wb_category_name]
            keywordstats = parent_category_to_keywordstat_list[parentId]
            ctr_percentile = np.percentile([kw.ctr for kw in keywordstats], percentile_value)  # Исправлена переменная здесь
            if ctr_percentile == 0:
                ctr_percentile = np.percentile([kw.ctr for kw in global_keywordstats_list], percentile_value)  # И еще здесь
            final_wb_category_name_to_min_ctr[wb_category_name] = ctr_percentile
        else:
            final_wb_category_name_to_min_ctr[wb_category_name] = ctr_percentile  # И тут
    return final_wb_category_name_to_min_ctr



async def get_good_bad_phrases(session, adv_setting: AdvSetting,
                               min_ctr: float)->tuple[list[str], list[str]]:
    stmt = select(AdvSetting).where(AdvSetting.id == adv_setting.id).options(
        selectinload(AdvSetting.keyword_settings)
    )
    result = await session.execute(stmt)
    adv_setting: AdvSetting = result.unique().scalar()
    keyword_settings: list[KeywordSetting] = adv_setting.keyword_settings
    good_keywords: list[KeywordSetting] = []
    bad_keywords: list[KeywordSetting] = []
    keyword_stats = await get_keyword_statistic(session, adv_setting)
    keyword_text_to_keyword_stat = {keyword_stat.text: keyword_stat for keyword_stat in keyword_stats}

    for keyword_setting in keyword_settings:
        if keyword_setting.hard_status == 2:
           good_keywords.append(keyword_setting.text)
           continue
        elif keyword_setting.hard_status == 0:
            bad_keywords.append(keyword_setting.text)
            continue
        keyword_stat = keyword_text_to_keyword_stat.get(keyword_setting.text, None)
        if not keyword_stat:
            good_keywords.append(keyword_setting.text)
            continue
        if min_ctr == 0:
            good_keywords.append(keyword_setting.text)
            continue
        enough_views = int(1 / min_ctr)
        views = keyword_stat.views + enough_views
        clicks = keyword_stat.clicks + 1
        fact_ctr = clicks / views
        predict_ctr = keyword_setting.predict_ctr
        if not predict_ctr:
            predict_ctr = fact_ctr
        elif fact_ctr > predict_ctr:
            predict_ctr = fact_ctr
        boost = adv_setting.boost
        predict_ctr *= boost
        if predict_ctr >= min_ctr:
            good_keywords.append(keyword_setting.text)
        else:
            bad_keywords.append(keyword_setting.text)

    return good_keywords, bad_keywords








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


async def get_wb_category(adv_setting: AdvSetting, session)-> WBCategory:
    nmid = adv_setting.nmids[0]
    smtp = select(WBCard).where(WBCard.nmid == nmid).options(selectinload(WBCard.wb_category))
    wb_card = await session.execute(smtp)
    wb_card : WBCategory = wb_card .unique().scalar()
    wb_category = wb_card.wb_category
    return wb_category

#
#
# async def get_adv_id_min_ctr(session, super_wb_user_cabinet: WBUserCabinet):
#     wb_api = WBApi(super_wb_user_cabinet)
#     subcategories: list[Subcategories] = await wb_api.content.get_all_subcategories()
#     smtp = select(AdvSetting).options(selectinload(AdvSetting.adv_keywords))
#     result = session.execute(smtp)
#     adv_settings: list[AdvSetting] = result.unique().scalars().all()
#
#     wb_category_advs = defaultdict(list)
#
#     for adv_setting in adv_settings:
#         clicks, views, _ = await get_keyword_statistic(adv_setting)
#         if views:
#             adv_setting.ctr = clicks/ views
#         else:
#             adv_setting.ctr = 0
#         category = get_wb_category(adv_setting)
#         category_name = category.wb_category_name
#         wb_category_advs[category_name].append(adv_setting)
#
#     wb_category_min_ctr = {}
#     parent_category_min_ctr = {}
#     for category, advs in wb_category_advs.items():
#         min_ctr = np.percentile([adv_setting.ctr for adv_setting in advs], 10)
#         wb_category_min_ctr[category] = min_ctr
#         if parent_category_min_ctr.get(category):
#             parent_category_min_ctr[category_name] = min_ctr




class DataSetter:
    def __init__(self, wb_user_cabinet: WBUserCabinet):
        self._wb_api = WBApi(wb_user_cabinet)



    async def update_minus_keywords(self, category_name_to_min_ctr):
        async with _sm() as session:
            stmt = select(AdvSetting).where(AdvSetting.bot_active == True) \
                .options(selectinload(AdvSetting.keyword_settings)
                         .selectinload(KeywordSetting.adv_keywords))\
            .where (AdvSetting.bot_active == True)
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.unique().scalars().all()
            for adv_setting in adv_settings:
                if adv_setting.bot_active:
                    category:WBCategory = await get_wb_category(adv_setting, session)
                    min_ctr = category_name_to_min_ctr.get(category.wb_category_name, 0)
                    good_phrases, bad_phrases = await get_good_bad_phrases(session, adv_setting, min_ctr)
                    await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
                    logger.debug(f'Обновил минус слова для {adv_setting.name} {bad_phrases}')





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




