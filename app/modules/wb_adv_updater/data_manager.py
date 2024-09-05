import asyncio
import io
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Union, Optional, List
import aiogram
from aiogram.utils import deep_linking
from sqlalchemy.exc import NoResultFound
from app.exc import CardNotFoundInDB
import pandas as pd
from PIL import Image
from sqlalchemy import and_, func, select, case, cast, Float, distinct
from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.data_classes.subcategories import Subcategory
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    KeywordSetting,
    WBCabinet,
    WBCard,
    WBCategory,
    CommonKeyword,
    WBItemPosition,
)
from app.modules.keywords_query import keywords_query
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.my_types import AdvSetting, WBUserCabinet
from app.payments.db.models import Payment

from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.models import User, RefLink, user_reflink_association
from app.utils.db.session_maker import get_async_session_maker
from app.utils.NeoDataScience.driver import DataScience
from app.utils import redis_manager

logger = logging.getLogger(__name__)


_sm = get_async_session_maker




async def measure_time(function):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await function(*args, **kwargs)  # Используйте await для асинхронного вызова
        end_time = time.time()
        print(f"{function.__name__} выполнена за {end_time - start_time} секунд.")
        return result
    return wrapper


async def get_keywords_statistic_clickhouse(
        adv_setting: AdvSetting,
        pass_time: Optional[timedelta] = None,
        hard_statuses: Optional[List[int]] = None,
        cache_timeout: int = 60 * 15
) -> List[CalculatedKeyword]:

    async with get_clickhouse_client() as ch_client:
        query = _build_clickhouse_query(adv_setting.adv_id, pass_time)
        result = await ch_client.query(query)
        rows = result.result_rows
        keywords = []
        for row in rows:
            text = row[0]
            clicks = row[1]
            views = row[2]
            spend = row[3]
            if clicks > views:
                views = clicks
            keyword = CalculatedKeyword(
                text=text,
                clicks=clicks,
                views=views,
                spend=spend
            )
            keywords.append(keyword)

    return keywords


async def _get_keyword_settings(adv_setting_id: int, hard_statuses: Optional[List[int]]) -> List[KeywordSetting]:
    async with _sm() as session:
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_id)
        if hard_statuses:
            stmt = stmt.where(KeywordSetting.hard_status.in_(hard_statuses))
        result = await session.execute(stmt)
        return result.scalars().all()


def _build_clickhouse_query(adv_id: int,  pass_time: Optional[timedelta]) -> str:
    query = f"""
          SELECT
              text,
              COALESCE(SUM(total_clicks), 0) AS total_clicks,
              COALESCE(SUM(total_views), 0) AS total_views,
              COALESCE(SUM(total_spend), 0) AS total_spend
          FROM (
              SELECT
                  text,
                  clicks AS total_clicks,
                  views AS total_views,
                  spend AS total_spend
              FROM
                  default_db.advkeyword
              WHERE
                  adv_id = {adv_id}
                  AND (text, date, version) IN (
                      SELECT
                          text, date, MAX(version) AS version
                      FROM
                          default_db.advkeyword
                      WHERE
                          adv_id = {adv_id}
                      GROUP BY
                          text, date
                  )
          ) AS latest_records
      """
    if pass_time:
        start_time = datetime.now() - pass_time
        query += f" AND date >= '{start_time.strftime('%Y-%m-%d')}'"



    query += " GROUP BY text"
    return query


async def get_keyword_statistic_clickhouse(client, keyword_setting: KeywordSetting,
                                           adv_id: int,
                                           pass_days: Union[int, None] = None) -> tuple[int, int, int]:

    today = datetime.now().date()
    text = keyword_setting.text
    query = f"""
        SELECT
            COALESCE(SUM(total_clicks), 0) AS total_clicks,
            COALESCE(SUM(total_views), 0) AS total_views,
            COALESCE(SUM(total_spend), 0) AS total_spend
        FROM (
            SELECT
                clicks AS total_clicks,
                views AS total_views,
                spend AS total_spend
            FROM
                default_db.advkeyword
            WHERE
                adv_id = {adv_id}
                AND text = %(text)s
                AND (text, date, version) IN (
                    SELECT
                        text,
                        date,
                        MAX(version) AS version
                    FROM
                        default_db.advkeyword
                    WHERE
                        adv_id = {adv_id}
                        AND text = %(text)s
                    GROUP BY
                        text,
                        date
                )
        ) AS latest_records
    """

    # Добавление условия для фильтрации по дате, если указано количество дней
    if pass_days:
        start_date = today - timedelta(days=pass_days)
        query += f" AND date >= '{start_date}'"

    # Выполнение запроса
    result = await client.query(query, {'text': text})

    # Проверка наличия результатов
    if not result.result_rows:
        logger.warning("No results found for the query.")
        return 0, 0, 0

    total_clicks, total_views, total_spend = result.result_rows[0]

    # Коррекция значений, если количество кликов больше количества просмотров
    if total_clicks > total_views:
        total_views = total_clicks

    return total_clicks, total_views, total_spend



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





# async def get_wb_category_to_keywordstat_list() -> defaultdict[WBCategory, list[CalculatedKeyword]]:
#     logger.debug('Начинаю получать статистику ключевых слов для расчета min_ctr')
#     stmt = select(AdvSetting).options(
#         selectinload(AdvSetting.adv_keywords),
#         selectinload(AdvSetting.keyword_settings),
#         selectinload(AdvSetting.wb_cards)
#     ).where(and_(AdvSetting.bot_active == True, AdvSetting.active_status == 'started'))
#
#     async with _sm() as session:
#         result = await session.execute(stmt)
#         adv_settings: list[AdvSetting] = result.unique().scalars().all()
#     wb_category_to_keywordstat_list = defaultdict(list)
#     for adv_setting in adv_settings:
#         logger.info(f'Обрабатываю {adv_setting.name} для расчета min_ctr')
#         try:
#             wb_category: Union[WBCategory, None] = await get_wb_category(adv_setting)
#         except (NotItemsInAdvSetting, CardNotFoundInDB) as e:
#             logger.debug(f'У кампании {adv_setting.name} нет товаров {e}')
#             continue
#         wb_category_name = wb_category.wb_category_name
#         keyword_stats = await get_keywords_statistic_clickhouse(adv_setting, None, [1, 2, 3])
#         for keyword_stat in keyword_stats:
#             if keyword_stat.views:
#                 wb_category_to_keywordstat_list[wb_category_name].append(keyword_stat)
#     return wb_category_to_keywordstat_list


async def get_parent_id_categories_subcategories_name_list() -> defaultdict[Any, list[Subcategory]]:
    access = await super_cabinet_manager.get_super_user_access()
    wb_api = WBApi(access)
    subcategories: list[Subcategory] = await wb_api.content.get_subcategories()
    parent_categories = defaultdict(list)
    for category in subcategories:
        parent_categories[category.parentID].append(category.subjectName)
    parent_categories_subcategories_name_list = parent_categories
    return parent_categories_subcategories_name_list


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



def __sort_by_update_keyword(keyword: WBItemPosition):
    if not (update := keyword.timestamp):
        update = datetime.now() - timedelta(days=1000)
    return update


async def  set_position(keyword_stat: CalculatedKeyword,
                        adv_setting: AdvSetting) -> CalculatedKeyword:
    keyword_cluster_name = await redis_manager.get_cluster_name(keyword_stat.text)
    position = await redis_manager.get_keyword_position(keyword_cluster_name,
                                                        adv_setting.nmids[0])
    if position:
        base_position = position.base_position
        promo_position = position.promo_position
        real_position = position.real_position
        keyword_stat.base_position = base_position
        keyword_stat.promo_position = promo_position
        keyword_stat.real_position = real_position
        keyword_stat.cpm = position.cpm

    else:
        keywords = keyword_stat.childs_keywords
        if keywords:
            texts = [kw.text for kw in keywords]
            positions = await redis_manager.get_keywords_positions(adv_setting, texts)
            if positions:
                position = max(positions, key=lambda kw: __sort_by_update_keyword(kw))
                base_position = position.base_position
                promo_position = position.promo_position
                real_position = position.real_position
                keyword_stat.base_position = base_position
                keyword_stat.promo_position = promo_position
                keyword_stat.real_position = real_position
                keyword_stat.cpm = position.cpm

    return keyword_stat

async def convert_keyword_stats_in_clusters(keyword_stats: list[CalculatedKeyword]) -> list[CalculatedKeyword]:

    preset_to_keywords = defaultdict(list)
    preset_to_cluster_name = {}

    for keyword in keyword_stats:
        text = keyword.text
        try:
           cluster_name, preset = await redis_manager.get_cluster_and_preset(text)
        except Exception as exc:
            logger.error(f'Ошибка при получении кластера и пресета для ключевого слова {text}', exc_info=True)
            cluster_name = None
            preset = None
        if cluster_name:
            preset_to_keywords[preset].append(keyword)
            preset_to_cluster_name[preset] = cluster_name

    keyword_stats = []

    for preset in preset_to_keywords:
        keywords = preset_to_keywords[preset]
        keyword_cluster_name = preset_to_cluster_name[preset]
        views = sum([keyword.views for keyword in keywords])
        clicks = sum([keyword.clicks for keyword in keywords])
        spend = sum([keyword.spend for keyword in keywords])
        query = sum([keyword.query if isinstance(keyword.query, int) else 0  for keyword in keywords])
        cluster_keyword = CalculatedKeyword(text=keyword_cluster_name,
                                            views=views,
                                            clicks=clicks,
                                            spend=spend
                                            )
        cluster_keyword.query = query if query else "<50"
        cluster_keyword.childs_keywords = keywords
        keyword_stats.append(cluster_keyword)

    return keyword_stats



async def get_good_bad_phrases(adv_setting: AdvSetting)->list[CalculatedKeyword]:
    min_ctr = await get_min_ctr(adv_setting)
    max_position = adv_setting.max_place
    logger.debug('Минимальный ctr получен')
    keyword_stats = await get_keywords_statistic_clickhouse(adv_setting, None)
    async with _sm() as session:
        logger.debug('Начинаю получать фразы')
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting.id)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    texts_to_keyword_setting = {kws.text: kws for kws in keyword_settings}
    if adv_setting.clusters_mode:
        keyword_stats = await convert_keyword_stats_in_clusters(keyword_stats)
    keyword_stats = [await set_position(kw, adv_setting) for kw in keyword_stats]
    async with _sm() as session:
        for keyword_stat in keyword_stats:
            cluster_name = keyword_stat.text
            if not (keyword_setting := texts_to_keyword_setting.get(cluster_name)):
                clusters = keyword_stat.childs_keywords
                stat_hard_statuses = defaultdict(int)
                for kw in clusters:
                    original_text = kw.text
                    if not (keyword_setting := texts_to_keyword_setting.get(original_text)):
                        continue
                    hard_status = keyword_setting.hard_status
                    stat_hard_statuses[hard_status] += 1
                result_hard_status = max(stat_hard_statuses.items(), key=lambda x: x[1])[0]
                keyword_setting = KeywordSetting()
                keyword_setting.text = cluster_name
                keyword_setting.adv_setting = adv_setting
                keyword_setting.hard_status = result_hard_status
                session.add(adv_setting)
                session.add(keyword_setting)
                await session.commit()
            keyword_stat.keyword_setting = keyword_setting


    texts_in_keyword_stat = {kw.text for kw in keyword_stats}
    text_to_keyword_setting = {kw.text: kw for kw in keyword_settings}


    for keyword_setting in keyword_settings:
        text = keyword_setting.text
        if text not in texts_in_keyword_stat and keyword_setting.hard_status == 2:
            keyword_setting = text_to_keyword_setting[text]

            keyword = CalculatedKeyword(text=text,
                                            clicks=0,
                                            views=0,
                                            spend=0,
                                            keyword_setting=keyword_setting)
            position = await redis_manager.get_keyword_position(text, adv_setting.nmids[0])
            if position:
                keyword.real_position = position.real_position
                keyword.base_position = position.base_position
                keyword.promo_position = position.promo_position
                keyword.position_update = position.timestamp
                keyword.cpm = position.cpm
            keyword.query = keywords_query.get_queries_of_keyword(text)
            keyword_stats.append(keyword)

    keyword_text_to_keyword_setting = {keyword_setting.text: keyword_setting for keyword_setting in keyword_settings}

    for keyword_stat in keyword_stats:
        logger.debug(f'Обрабатываю ключевое слово {keyword_stat.text}')
        keyword_setting = keyword_text_to_keyword_setting[keyword_stat.text]
        keyword_stat.keyword_setting = keyword_setting
        predict_ctr = await redis_manager.get_predict_ctr(adv_setting.adv_id, keyword_stat.text)
        if not predict_ctr:
            predict_ctr = keyword_setting.predict_ctr
        keyword_stat.predict_ctr = predict_ctr
        original_predict_ctr = keyword_stat.predict_ctr
        predict_ctr = original_predict_ctr
        keyword_stat.hard_status = keyword_setting.hard_status
        if min_ctr == 0:
            enough_views = 100
        else:
            enough_views = int(1 / min_ctr)
        views = keyword_stat.views
        clicks = keyword_stat.clicks
        if clicks == 0:
             clicks += 1
             views += enough_views
        added_clicks = keyword_setting.added_clicks
        if added_clicks:
            clicks += added_clicks
        real_baes_ctr = clicks / views
        keyword_stat.baes_ctr = real_baes_ctr
        if not original_predict_ctr:
            predict_ctr = real_baes_ctr
            keyword_stat.predict_ctr = predict_ctr
        calculate_ctr = (real_baes_ctr + predict_ctr)/2
        keyword_stat.predict_ctr = calculate_ctr
        if max_position:
            position = await redis_manager.get_keyword_position(keyword_setting.text, adv_setting.nmids[0])
            if position:
                organic_position = position.base_position
                if 0 < organic_position <= max_position:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'max_position'
                    await redis_manager.set_auto_block_status(keyword_setting.id, False)
                    await asyncio.sleep(0)
                    continue

        if adv_setting.max_cpc:
            if keyword_stat.cpc > adv_setting.max_cpc:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'max_cpc'
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
                await asyncio.sleep(0)
                continue

        if not  original_predict_ctr and enough_views/2 > keyword_stat.views and not adv_setting.min_views_for_ml_predict and not keyword_setting.hard_status != 1:
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
            await redis_manager.set_auto_block_status(keyword_setting.id, True)
            await asyncio.sleep(0)
            continue

        if keyword_setting.hard_status == 3:
            keyword_stat.status = KeywordStatus.BAD
            keyword_stat.reason = 'turn_off'
            await redis_manager.set_auto_block_status(keyword_setting.id, False)
            await asyncio.sleep(0)
            continue
        if keyword_setting.hard_status == 2:
           keyword_stat.status = KeywordStatus.GOOD
           keyword_setting.auto_block = False
           await redis_manager.set_auto_block_status(keyword_setting.id, False)
           await asyncio.sleep(0)
           continue
        elif keyword_setting.hard_status == 0:
            keyword_stat.status = KeywordStatus.BAD
            keyword_stat.reason = 'black_list'
            await redis_manager.set_auto_block_status(keyword_setting.id, False)
            await asyncio.sleep(0)
            continue
        if min_ctr == 0:
            keyword_stat.status = KeywordStatus.GOOD
            await redis_manager.set_auto_block_status(keyword_setting.id, False)
            await asyncio.sleep(0)
            continue

        if calculate_ctr >= min_ctr or real_baes_ctr >= min_ctr:
            keyword_stat.status = KeywordStatus.GOOD
            await redis_manager.set_auto_block_status(keyword_setting.id, False)
        else:
            if keyword_stat.views < adv_setting.min_views_for_ml_predict:
                keyword_stat.status = KeywordStatus.GOOD
                keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
                await redis_manager.set_auto_block_status(keyword_setting.id, True)
            else:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'min_ctr'
                await redis_manager.set_auto_block_status(keyword_setting.id, True)
        assert keyword_stat.predict_ctr
        await asyncio.sleep(0)

    logger.debug('Проверяю статусы ключевых слов с assert')

    for keyword_stat in keyword_stats:
        assert keyword_stat.status
        assert keyword_stat.status in ['good', 'bad']
    logger.debug('Слова по assert проверены')
    logger.debug('Возвращаю итоговую статистику')
    return keyword_stats







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

    async def get_item_features_from_neo(self, nmids_batch):
        result = await self._gds.get_nmid_vectors(nmids_batch)
        return result

    async def get_item_features_from_redis(self, nmids_batch):
        result = await redis_manager.get_nmid_vectors(nmids_batch)
        return result

    async def get_keyword_features_from_neo(self, keywords):
        result = await self._gds.get_keywords_vectors_by_keywords(keywords)
        return result

    async def get_keyword_features_from_redis(self, keywords)->list[tuple[str, list[float]]]:
        result = await redis_manager.get_keywords_vectors(keywords)
        return result


async def get_wb_category(adv_setting: AdvSetting)-> Union[WBCategory, None]:
    try:
         nmid = adv_setting.nmids[0]
    except:
        raise NotItemsInAdvSetting('У кампании в базе нет товаров')
    async with _sm() as session:
        smtp = select(WBCard).where(WBCard.nmid == nmid).options(selectinload(WBCard.wb_category))
        wb_card = await session.execute(smtp)
    wb_card: WBCategory = wb_card.unique().scalar()
    if wb_card:
        wb_category = wb_card.wb_category
    else:
        raise CardNotFoundInDB('В базе не найдена карточка товара: ' + str(nmid))
    return wb_category




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

async def get_adv_keyword_text_in_white_list():
    async with _sm() as session:
        stmt = select(KeywordSetting) \
            .options(selectinload(KeywordSetting.adv_setting)) \
            .where(KeywordSetting.hard_status.in_([2, 3]))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    adv_keyword_text_in_white_list = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_white_list.append((adv_setting.adv_id, keyword_setting.text))

    return adv_keyword_text_in_white_list




async def get_all_users()-> list[User]:
    async with _sm() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users: list[User] = result.unique().scalars().all()
    return users


async def get_all_shops_for_user(user:User):
    async with _sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.user_id == user.id)
        result = await session.execute(stmt)
        wb_user_cabinets = result.scalar()
        if wb_user_cabinets:
            return  wb_user_cabinets.all()
        else:
            return []


async def get_adv_id_to_min_ctr(adv_ids: list[int])-> dict[int, float]:
    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(adv_ids))
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars()
    adv_id_to_min_ctr = {}

    for adv_setting in adv_settings:
        logger.debug('Получаю min_ctr')
        min_ctr = await get_min_ctr(adv_setting)
        logger.debug('min_ctr получен')
        adv_id_to_min_ctr[adv_setting.adv_id] = min_ctr
    return adv_id_to_min_ctr


async def get_adv_id_keyword_text_to_status(adv_ids: list[int]):
    async with _sm() as session:
        # Используем только необходимые колонки и убираем лишние алиасы
        stmt = select(AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status) \
            .join(KeywordSetting, AdvSetting.id == KeywordSetting.adv_setting_id) \
            .where(AdvSetting.adv_id.in_(adv_ids))

        # Выполняем запрос
        result = await session.execute(stmt)

        # Извлекаем данные в виде словаря сразу в процессе итерации по результату
        adv_id_keyword_text_to_status = {
            (row.adv_id, row.text): row.hard_status
            for row in result
        }

    return adv_id_keyword_text_to_status



@dataclass
class ReferralStatistic:
    name: str
    referrals_count: int
    total_payments: float

async def get_ref_statistic(user_telegram_id: int) -> Optional[list[ReferralStatistic]]:
    """НУЖНО ЧИНИТЬ,ПОКА НЕ РАБОТАЕТ ПАРТНЕРКА"""
    async with _sm() as session:
        # Сначала найдем пользователя по telegram_id
        user_query = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(user_query)
        user_id = result.scalar()

        if user_id is None:
            return None

        # Теперь получим статистику по реферальным ссылкам
        statistics_query = select(
            RefLink.name,
            func.count(user_reflink_association.c.user_id).label("referrals_count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_payments")
        ).select_from(RefLink) \
         .outerjoin(user_reflink_association, RefLink.id == user_reflink_association.c.reflink_id) \
         .outerjoin(User, user_reflink_association.c.user_id == User.id) \
         .outerjoin(WBUserCabinet, WBUserCabinet.user_id == User.id) \
         .outerjoin(WBCabinet, WBCabinet.id == WBUserCabinet.wbcabinet_id) \
         .outerjoin(Payment, Payment  == WBCabinet.id) \
         .where(RefLink.referrer_id == user_id) \
         .group_by(RefLink.name)

        result = await session.execute(statistics_query)
        stats = result.fetchall()

        # Возвращаем результаты в удобном для использования виде
        return [ReferralStatistic(name=row[0], referrals_count=row[1], total_payments=min(row[2], 500)) for row in stats]



@dataclass
class ReferralLink:
    name: str
    link: str



async def get_ref_names_and_links(user_telegram_id: int, bot:aiogram.Bot):
    async with _sm() as session:
        stmt = select(User.id).where(User.user_telegram_id == user_telegram_id)
        result = await session.execute(stmt)
        user_id = result.scalar()
        stmt = select(RefLink.name, RefLink.id).where(RefLink.referrer_id == user_id)
        result = await session.execute(stmt)
        refs = result.fetchall()

    ref_links = []
    for ref in refs:
        link = await deep_linking.create_start_link(bot, ref[1])
        ref_links.append(ReferralLink(name=ref[0], link= link))
    return ref_links


async def get_mean_ctr(adv: AdvSetting):
    keywords: list[CalculatedKeyword] = await get_good_bad_phrases(adv)
    goods = [kw for kw in keywords if kw.status == 'good']
    goods = [kw.text for  kw in goods]
    async with _sm() as session:
        stmt = (
            select(
                case(
                    (func.sum(AdvKeyword.views) == 0, 0),  # Условие, если показов нет, возвращаем 0
                    else_=cast(func.sum(AdvKeyword.clicks) / func.sum(AdvKeyword.views), Float)  # Иначе вычисляем CTR
                ).label("average_ctr")
            )
        ).where(and_(AdvKeyword.adv_setting_id == adv.id,
                     AdvKeyword.text.in_(goods)))
        result = await session.execute(stmt)
        mean_ctr = result.scalar_one()
        return mean_ctr  # Возвращаем значение mean_ctr вместо pass


async def get_min_ctr(adv: AdvSetting):
    if adv.hard_min_ctr:
        return float(adv.hard_min_ctr)
    async with _sm() as session:
        stmt = select(KeywordSetting)\
        .where(
            KeywordSetting.hard_status == 2,
               KeywordSetting.adv_setting_id == adv.id,
            )
        result = await session.execute(stmt)
        keyword_settings = result.unique().scalars().all()
    texts = [kw.text for kw in keyword_settings]
    if texts:
        adv_id = adv.adv_id
        query = f"""
                  WITH
        latest_versions AS (
            SELECT
                text,
                date,
                MAX(version) AS latest_version
            FROM
                default_db.advkeyword
            WHERE
                adv_id = {adv_id}
                AND text IN ({', '.join(f"'{text}'" for text in texts)})
            GROUP BY
                text, date
        ),
        stats AS (
            SELECT
                a.text,
                SUM(a.clicks) AS total_clicks,
                SUM(a.views) AS total_views
            FROM
                default_db.advkeyword a
            INNER JOIN
                latest_versions lv
            ON
                a.text = lv.text
                AND a.date = lv.date
                AND a.version = lv.latest_version
            WHERE
                a.adv_id = {adv_id}
            GROUP BY
                a.text
        )
                    SELECT
                        text,
                        total_clicks / CASE
                            WHEN total_views = 0 THEN 1
                            ELSE total_views
                        END AS ctr,
                        total_views AS views
                    FROM
                        stats
                    WHERE
                        total_views > 0
    
    
                """

        async with get_clickhouse_client() as client:
            result = await client.query(query)
            rows = result.result_rows
        text_to_real_ctr = {row[0]: row[1] for row in rows}
        real_ctrs  = []
        predict_ctrs = []
        for kw in keyword_settings:
            real_ctr = text_to_real_ctr.get(kw.text)
            if real_ctr:
                real_ctrs.append(text_to_real_ctr[kw.text])
            predict_ctr = kw.predict_ctr
            if predict_ctr:
                predict_ctrs.append(kw.predict_ctr)
        if real_ctrs:
            return float(min(real_ctrs))

        if predict_ctrs:
            return float(min(predict_ctrs))

    category = await get_wb_category(adv)
    category_name = category.wb_category_name
    async with _sm() as session:
        stmt = select(GlobalCategorySetting.min_ctr).where(GlobalCategorySetting.category_name == category_name)
        result = await session.execute(stmt)
        try:
             min_ctr = result.scalar_one()
        except NoResultFound:
            return 0.03
    return float(min_ctr)



async def get_needs_nmids():
    async with _sm() as session:
        stmt = select(AdvSetting)
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.unique().scalars().all()
    nmids = []
    for adv_setting in adv_settings:
        if adv_setting.nmids:
            nmids.extend(adv_setting.nmids)
    return nmids


async def get_all_keywords()-> list[str]:
    async with _sm() as session:
        stmt = select(KeywordSetting)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    keywords = []
    for keyword_setting in keyword_settings:
        keywords.append(keyword_setting.text)
    return keywords


async def clear_cards(need_nmids: list[int]):
    async with _sm() as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(need_nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = result.unique().scalars().all()
        await session.delete(wb_cards)
        await session.commit()


async def clear_keywords(need_keywords):
    async with _sm() as session:
        stmt = select(KeywordSetting).where(KeywordSetting.text.notin_(need_keywords))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
        await session.delete(keyword_settings)
        await session.commit()


async def get_expired_cabinets(session):
    delete_expired_time = datetime.now() - timedelta(days=30)
    stmt = select(WBCabinet).options(
        selectinload(WBCabinet.adv_settings)
    ).where(WBCabinet.expiration_time < delete_expired_time)
    result = await session.execute(stmt)
    wb_cabinets: list[WBCabinet] = result.unique().scalars().all()
    return wb_cabinets

async def clear_cards_in_db(nmids: list[int]):
    async with _sm() as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = result.unique().scalars().all()
        for card in wb_cards:
             await session.delete(card)
             await session.commit()
             await asyncio.sleep(0)


async def get_keywords_from_clickhouse(adv_id: int)-> list[str]:
    query = f"""
SELECT DISTINCT text
FROM default_db.advkeyword 
WHERE adv_id = {adv_id}
"""
    async with get_clickhouse_client() as client:
        result = await client.query(query)
        keywords = result.result_rows
    return [keyword[0] for keyword in keywords if keyword]


async def get_nmids_for_keyword_text(text: str )-> set[int]:
    query = """
    SELECT DISTINCT adv_id
    FROM default_db.advkeyword 
    WHERE text = %(text)s
    """
    params = {'text': text}
    async with get_clickhouse_client() as client:
        result = await client.query(query, parameters=params)
        nmids = result.result_rows
    return set([nmid[0] for nmid in nmids if nmid])



async def get_phrases_for_parsing(semaphore = None):
    pass_texts = set()
    async with _sm(semaphore) as session:
        stmt = select(AdvSetting.adv_id).where(
            AdvSetting.parsing_active == True)
        adv_ids  = await session.execute(stmt)
        adv_ids = adv_ids.scalars().all()
        random.shuffle(adv_ids)
        for adv_id in adv_ids:
            keywords_texts: list[str] = await get_keywords_from_clickhouse(adv_id)
            for text in keywords_texts:
                hash_text = hash(text)
                if hash_text in pass_texts:
                    continue
                adv_ids_with_text: set[int] = await get_nmids_for_keyword_text(text)
                nmids_need = set()
                not_found_adv_id = set()
                for adv_id_with_text in adv_ids_with_text:
                    if adv_id_with_text not in  adv_ids:
                        continue
                    nmid = await redis_manager.get_nmid(adv_id)
                    if not nmid:
                        not_found_adv_id.add(adv_id_with_text)
                    else:
                        nmids_need.add(nmid)

                if not_found_adv_id:
                    async with _sm() as session:
                        stmt = select(distinct(AdvSetting.nmids)).where(AdvSetting.adv_id.in_(not_found_adv_id))
                        result = await session.execute(stmt)
                        nmids = result.scalars().all()
                        if nmids:
                             nmids = [nmid for row in nmids for nmid in row]
                             for nmid in nmids:
                                 await redis_manager.set_nmid(adv_id, nmid)
                             nmids_need = nmids_need.union(nmids)
                yield text, nmids_need
                pass_texts.add(hash_text)
                await asyncio.sleep(0)


async def get_last_updated_phrases(all_white_phrases):
    async with _sm() as session:
        stmt = select(CommonKeyword.text)\
            .where(CommonKeyword.text.in_(all_white_phrases))\
            .order_by(CommonKeyword.updated_at)
        result = await session.execute(stmt)
        last_updated_phrases = result.scalars().all()
        return last_updated_phrases


async def get_keywords_positions_dict_by_text(adv_setting: AdvSetting, texts: list[str]) -> dict[str, WBItemPosition]:
    positions =  await redis_manager.get_keywords_positions(adv_setting, texts)
    positions = [position for position in positions if position]
    positions = {position.keyword_text: position for position in positions}
    return positions


async def add_white_phrases(keywords: list[str], adv_setting_id: int):
    async with _sm() as session:
        for text in keywords:
            stmt = select(KeywordSetting)\
                .join(KeywordSetting.adv_setting)\
                .where(KeywordSetting.text == text,
                                                AdvSetting.id == adv_setting_id)
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            if not keyword_setting:
                adv_keyword = AdvKeyword(text=text,
                                         adv_setting_id=adv_setting_id,
                                         views=0,
                                         clicks=0,
                                         spend=0,
                                         date=datetime.now().date())

                keyword_setting = KeywordSetting(text=text,
                                                 adv_setting_id=adv_setting_id,
                                                 )
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            keyword_setting.hard_status = 2
        await session.commit()



async def update_black_phrases(adv_setting_id, keywords: list[str]):
    await redis_manager.set_black_phrases(adv_setting_id, keywords)
    async with _sm() as session:
        stmt = select(KeywordSetting)\
            .join(KeywordSetting.adv_setting)\
            .where(AdvSetting.id == adv_setting_id,
                   KeywordSetting.hard_status != 0)
        result = await session.execute(stmt)
        keyword_settings = result.scalars().all()
        for keyword_setting in keyword_settings:
            for black_phrase in keywords:
                black_phrase_text = black_phrase.lower().strip()
                if "'" in black_phrase_text or '"' in black_phrase_text:
                    black_phrase_text = black_phrase_text.replace("'", "''").replace('"', '""')
                    if black_phrase_text == keyword_setting.text:
                        keyword_setting.hard_status = 0
                        break
                else:
                    if black_phrase_text in keyword_setting.text:
                        keyword_setting.hard_status = 0
                        break

        await session.commit()


async def check_by_black_list_template(keyword_text: str, adv_setting_id: int):
    black_keywords = await redis_manager.get_black_phrases(adv_setting_id)
    keyword_text_lower = keyword_text.lower().strip()

    for black_phrase in black_keywords:
        black_phrase_text = black_phrase.lower().strip()
        if "'" in black_phrase_text or '"' in black_phrase_text:
            black_phrase_text = black_phrase_text.replace("'", "''").replace('"', '""')
            if black_phrase_text == keyword_text_lower:
                return True
        else:
            if black_phrase_text in keyword_text_lower:
                return True
    return False


async def reset_black_phrases(adv_setting_id):
    await redis_manager.set_black_phrases(adv_setting_id, [])
