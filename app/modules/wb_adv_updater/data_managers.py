import asyncio
import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Union

from PIL import Image

from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.data_classes.subcategories import Subcategory
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.utils.db.models import User
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import KeywordStatFromDB
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy.orm import selectinload

from app.my_types import WBUserCabinet
from sqlalchemy import select, and_, func

from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
import pandas as pd
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.my_types import AdvSetting
from app.modules.common_slaves.wildberries.api import WBApi

from app.utils.NeoDataScience.driver import DataScience
from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvKeyword, WBCategory, WBCard, WBCabinet
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess


logger = logging.getLogger(__name__)


_sm = get_async_session_maker()


async def get_keyword_statistic(adv_setting: AdvSetting,
                                pass_time: Union[timedelta, None],
                                hard_statuses: list[int] = None,
                                )->list[KeywordStatFromDB]:

    base_stmt = (
        select(
            AdvKeyword.text.label("keyword_text"),
            func.sum(AdvKeyword.views).label("total_views"),
            func.sum(AdvKeyword.spend).label("total_spend"),
            func.sum(AdvKeyword.clicks).label("total_clicks")  # Используйте total_clicks для суммы кликов
        )
        .join(KeywordSetting, AdvKeyword.keyword_setting_id == KeywordSetting.id)
    )
    if  pass_time:
         today = datetime.today()
         base_stmt = base_stmt\
        .where(AdvKeyword.date >= today - pass_time)


    if hard_statuses:
        # Фильтрация по hard_statuses и adv_setting_id и добавление группировки
        stmt = base_stmt.where(
            and_(
                KeywordSetting.hard_status.in_(hard_statuses),
                KeywordSetting.adv_setting_id == adv_setting.id
            )
        )
    else:
        stmt = base_stmt.where(KeywordSetting.adv_setting_id == adv_setting.id)


    # Группировка по тексту ключевых слов и идентификатору настройки рекламной кампании вне зависимости от условия
    stmt = stmt.group_by(AdvKeyword.text, KeywordSetting.adv_setting_id)
    async with _sm() as session:
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


async def get_global_super_wb_user_cabinet() -> WBUserCabinet:
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





async def get_wb_category_to_keywordstat_list() -> defaultdict[WBCategory, list[KeywordStatFromDB]]:
    stmt = select(AdvSetting).options(
        selectinload(AdvSetting.adv_keywords),
        selectinload(AdvSetting.keyword_settings),
        selectinload(AdvSetting.wb_cards)
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()
    wb_category_to_keywordstat_list = defaultdict(list)
    for adv_setting in adv_settings:
        wb_category: Union[WBCategory, None] = await get_wb_category(adv_setting)
        if not wb_category:
            continue
        wb_category_name = wb_category.wb_category_name
        keyword_stats = await get_keyword_statistic(adv_setting, None, [1, 2])
        for keyword_stat in keyword_stats:
            if keyword_stat.views:
                wb_category_to_keywordstat_list[wb_category_name].append(keyword_stat)
    return wb_category_to_keywordstat_list


# @cached_stampede(ttl=60*60*24, key="get_category_name_min_ctr_final_data", cache=aiocache.RedisCache)
async def get_parent_id_categories_subcategories_name_list() -> defaultdict[Any, list[Subcategory]]:
    access = await super_cabinet_manager.get_super_user_access()
    wb_api = WBApi(access)
    subcategories: list[Subcategory] = await wb_api.content.get_subcategories()
    parent_categories = defaultdict(list)
    for category in subcategories:
        parent_categories[category.parentID].append(category.subjectName)
    parent_categories_subcategories_name_list = parent_categories
    return parent_categories_subcategories_name_list


# @cached_stampede(ttl=60, key="get_category_name_min_ctr_final_data", cache=aiocache.RedisCache)
async def get_category_name_min_ctr_final_data() -> dict[int, float]:
    async with _sm() as session:
        stmt = select(GlobalCategorySetting.category_name, GlobalCategorySetting.min_ctr)
        result = await session.execute(stmt)
        global_category_settings: list[GlobalCategorySetting] = result.all()
    get_category_name_min_ctr = {}
    for row in global_category_settings:
        category_name = row[0]
        min_ctr = row[1]
        get_category_name_min_ctr[category_name] = min_ctr
    return get_category_name_min_ctr



async def get_good_bad_phrases(adv_setting: AdvSetting,
                               min_ctr: float)->tuple[list[str], list[str]]:
    stmt = select(AdvSetting).where(AdvSetting.id == adv_setting.id).options(
        selectinload(AdvSetting.keyword_settings)
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.unique().scalar()
    keyword_settings: list[KeywordSetting] = adv_setting.keyword_settings
    good_keywords: list[KeywordSetting] = []
    bad_keywords: list[KeywordSetting] = []
    keyword_stats = await get_keyword_statistic(adv_setting, None)
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


async def get_wb_category(adv_setting: AdvSetting)-> Union[WBCategory, None]:
    try:
         nmid = adv_setting.nmids[0]
    except:
        logger.error(f'У {adv_setting.name} нет товаров')
        return None
    async with _sm() as session:
        smtp = select(WBCard).where(WBCard.nmid == nmid).options(selectinload(WBCard.wb_category))
        wb_card = await session.execute(smtp)
    wb_card : WBCategory = wb_card.unique().scalar()
    if wb_card:
        wb_category = wb_card.wb_category
    else:
        return None
    return wb_category

class DataSetter:
    def __init__(self, access: WBCabinetAccess):
        self._wb_api = WBApi(access)
        self._wb_user_cabinet = access.wb_user_cabinet


    async def update_minus_keywords(self, category_name_to_min_ctr):
        async with _sm() as session:
            stmt = select(AdvSetting) \
                .options(selectinload(AdvSetting.keyword_settings)
                         .selectinload(KeywordSetting.adv_keywords))\
            .where (and_(AdvSetting.bot_active == True, AdvSetting.bot_active == True))
            result = await session.execute(stmt)
            adv_settings: list[AdvSetting] = result.unique().scalars().all()
        for adv_setting in adv_settings:
            if adv_setting.bot_active:
                category:WBCategory = await get_wb_category(adv_setting)
                if not category:
                    continue
                min_ctr = category_name_to_min_ctr.get(category.wb_category_name, 0)
                good_phrases, bad_phrases = await get_good_bad_phrases(adv_setting, min_ctr)
                await self._wb_api.advert.set_minus_phrases(adv_setting, bad_phrases)
                logger.debug(f'Обновил минус слова для {adv_setting.name} {bad_phrases}')
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


async def get_main_photos(nmids: list[int]):
    async with _sm() as session:
        smtp = (select(WBCard).where(WBCard.nmid.in_(nmids)))
        result = await session.execute(smtp)
        wb_cards: list[WBCard] = result.unique().scalars().all()
    main_photos: list[str] = [wb_card.photos[0] for wb_card in wb_cards]
    return main_photos



async def __download_and_resize_image(url, session, max_size=1280):
    while True:
        async with session.get(url) as response:
            if response.status != 200:
                await asyncio.sleep(1)
                continue
            image_data = await response.read()
            # Открываем изображение используя BytesIO
            with io.BytesIO(image_data) as image_file:
                with Image.open(image_file) as img:
                    # Масштабируем изображение, сохраняя пропорции
                    img.thumbnail((max_size, max_size))

                    # Сохраняем изображение в BytesIO объект
                    with io.BytesIO() as output:
                        img.save(output, format="JPEG")
                        return output.getvalue()


async def get_adv_keyword_text_in_black_list()-> list[tuple[int, str]]:
    async with _sm() as session:
        stmt = select(KeywordSetting)\
            .options(selectinload(KeywordSetting.adv_setting))\
        .where(KeywordSetting.hard_status == 0)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    adv_keyword_text_in_black_list = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_black_list.append((adv_setting.adv_id, keyword_setting.text))

    return adv_keyword_text_in_black_list


