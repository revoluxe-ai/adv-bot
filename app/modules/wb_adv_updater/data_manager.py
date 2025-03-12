import io
import json
import logging
import time
import cProfile
import pstats
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Union, Optional, List, Callable, Iterable
import aiogram
from aiogram.utils import deep_linking
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql.functions import coalesce

from app.exc import CardNotFoundInDB, PositionNotFoundError, NotFoundPositionWithCMPError
import pandas as pd
from PIL import Image
from sqlalchemy import and_, func, select, case, cast, Float, distinct
from sqlalchemy.orm import selectinload, subqueryload, aliased, load_only
from app.modules.common_slaves.wildberries.data_classes.card_from_wb import CardFromWB
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword, KeywordStatus
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    KeywordSetting,
    WBCabinet,
    WBCard,
    WBCategory,
    WBItemPosition,
)
from app.modules.keywords_query import keywords_query
from app.modules.full_stat_adv_updater.types import FullAdvStat
from app.modules.wb_adv_updater.ABC_manager import AbcManager
from app.modules.wb_adv_updater.models import GlobalCategorySetting
from app.my_types import AdvSetting, WBUserCabinet
from app.payments.db.models import Payment

from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.models import User, RefLink, user_reflink_association
from app.utils.db.session_maker import get_async_session_maker
from app.utils.NeoDataScience.driver import DataScience
from app.utils import redis_manager
from app.utils.redis_manager.exc import DataNotFoundError

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



async def get_keyword_statistic_clickhouse(client,
                                           text: str,
                                           adv_id: int,
                                           pass_days: Union[int, None] = 7) -> tuple[int, int, int]:

    today = datetime.now().date()
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
                    """

    # Добавление условия для фильтрации по дате внутри подзапроса
    if pass_days:
        start_date = today - timedelta(days=pass_days)
        query += f" AND date >= '{start_date}'"

    query += """
                    GROUP BY
                        text,
                        date
                )
        ) AS latest_records
    """

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






async def get_keywords_statistic_clickhouse(
        adv_setting: AdvSetting,
        pass_time: Optional[timedelta] = timedelta(days=7),
        last_views = None,
        hard_statuses: Optional[List[int]] = None,
        cache_timeout: int = 60 * 15
) -> List[CalculatedKeyword]:

    async with get_clickhouse_client() as ch_client:
        query = _build_clickhouse_query(adv_setting.adv_id,
                                        pass_time,
                                        last_views)
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

    keywords = await redis_manager.set_predict_ctrs(adv_setting.adv_id, keywords)
    return keywords






async def _get_keyword_settings(adv_setting_id: int, hard_statuses: Optional[List[int]]) -> List[KeywordSetting]:
    async with _sm() as session:
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_id)
        if hard_statuses:
            stmt = stmt.where(KeywordSetting.hard_status.in_(hard_statuses))
        result = await session.execute(stmt)
        return result.scalars().all()


def _build_clickhouse_query(adv_id: int,
                            pass_time: Optional[timedelta],
                            last_views: Optional[int] = None) -> str:
    # Формируем основной запрос
    query = f"""
        SELECT
            text,
            SUM(total_clicks) AS total_clicks,
            SUM(total_views) AS total_views,
            SUM(total_spend) AS total_spend,
            date
        FROM (
            SELECT
                text,
                COALESCE(SUM(clicks), 0) AS total_clicks,
                COALESCE(SUM(views), 0) AS total_views,
                COALESCE(SUM(spend), 0) AS total_spend,
                date
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
    """

    # Добавляем условие для pass_time
    if pass_time:
        start_time = datetime.now() - pass_time
        query += f" AND date >= '{start_time.strftime('%Y-%m-%d')}'"

    # Завершаем основной подзапрос
    query += """
            GROUP BY
                text, date
        ) AS latest_records
        GROUP BY text, date
    """

    # Если указаны last_views, добавляем дополнительный запрос с CTE
    if last_views:
        query = f"""
            WITH
            records AS ({query}),
            cumulative_views AS (
                SELECT
                    text,
                    total_clicks,
                    total_views,
                    total_spend,
                    date,
                    SUM(total_views) OVER (PARTITION BY text ORDER BY date DESC) AS cumulative_total_views
                FROM
                    records
            )
            SELECT
                text,
                SUM(total_clicks) AS total_clicks,
                SUM(total_views) AS total_views,
                SUM(total_spend) AS total_spend
            FROM
                cumulative_views
            WHERE
                cumulative_total_views <= {last_views}
            GROUP BY text
        """

    return query





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


# async def get_parent_id_categories_subcategories_name_list() -> defaultdict[Any, list[Subcategory]]:
#     access = await super_cabinet_manager.get_super_user_access()
#     wb_api = WBApi(access)
#     subcategories: list[Subcategory] = await wb_api.content.get_subcategories()
#     parent_categories = defaultdict(list)
#     for category in subcategories:
#         parent_categories[category.parentID].append(category.subjectName)
#     parent_categories_subcategories_name_list = parent_categories
#     return parent_categories_subcategories_name_list


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

async def set_positions(keyword_stats: list[CalculatedKeyword],
                        adv_setting: AdvSetting) -> list[CalculatedKeyword]:
    texts = [keyword.text for keyword in keyword_stats]
    try:
       positions = await redis_manager.get_keywords_positions(adv_setting, texts)
    except:
        logger.warning(f'Ошибка получения позиций из Redis для арк {adv_setting.adv_id}')
        return keyword_stats
    text_to_position = {position.keyword_text: position for position in positions}
    for keyword_stat in keyword_stats:
        text = keyword_stat.text
        try:
            cluster, preset = await redis_manager.get_cluster_and_preset(text)
        except:
            logger.error(f'Ошибка получения кластера и пресета для {text}', exc_info=True)
            continue
        keyword_stat.cluster_name = cluster
        keyword_stat.preset = preset
        if position := text_to_position.get(text):
            keyword_stat.base_position = position.base_position
            keyword_stat.promo_position = position.promo_position
            keyword_stat.real_position = position.real_position
            keyword_stat.cpm = position.cpm
            keyword_stat.position = position
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

    return keyword_stats





async def  set_position(keyword_stat: CalculatedKeyword,
                        adv_setting: AdvSetting) -> CalculatedKeyword:
    text = keyword_stat.text
    position = await redis_manager.get_keyword_position(text,
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


def __calculate_clusters(preset_to_keywords, preset_to_cluster_name):
    keyword_stats = []
    for preset in preset_to_keywords:
        keywords = preset_to_keywords[preset]
        keyword_cluster_name = preset_to_cluster_name[preset]
        views = clicks = spend = query = 0
        for keyword in keywords:
            views += keyword.views
            clicks += keyword.clicks
            spend += keyword.spend
            if isinstance(keyword.query, int):
                query += keyword.query

        cluster_keyword = CalculatedKeyword(
            text=keyword_cluster_name,
            views=views,
            clicks=clicks,
            spend=spend
        )
        cluster_keyword.query = query if query else "<50"
        cluster_keyword.childs_keywords = keywords
        keyword_stats.append(cluster_keyword)

    return keyword_stats


def profile_function(func: Callable, *args, **kwargs):
    profiler = cProfile.Profile()
    profiler.enable()
    func(*args, **kwargs)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats(10)


async def convert_keyword_stats_in_clusters(keyword_stats: list[CalculatedKeyword]) -> list[CalculatedKeyword]:
    preset_to_keywords = defaultdict(list)
    preset_to_cluster_name = {}
    texts = [keyword.text for keyword in keyword_stats]
    try:
        text_to_custer_and_present: dict[str, tuple] = await redis_manager.get_clusters_and_presets(texts)
    except:
        logger.error(f'Ошибка получения кластеров и пресетов: {texts}', exc_info=True)
        return keyword_stats
    for keyword in keyword_stats:
        text = keyword.text
        cluster_name, preset = text_to_custer_and_present.get(text, (None, None))
        if cluster_name:
            preset_to_keywords[preset].append(keyword)
            preset_to_cluster_name[preset] = cluster_name
        else:
            preset = hash(text)
            cluster_name = text
            preset_to_keywords[preset].append(keyword)
            preset_to_cluster_name[preset] = cluster_name
    keyword_stats = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)

    return keyword_stats


async def get_cpm_by_nmid(nmid, texts)-> Optional[int]:
    cpm = await __get_cpm_from_positions(nmid, texts)
    return cpm


async def __get_cpm_from_positions(nmid: int, texts) -> Optional[int]:
    positions = await redis_manager.get_keywords_positions_by_nmid(nmid, texts)
    if not positions:
        raise PositionNotFoundError(f'Позиции не найдены для nmid в редис {nmid}')

    positions = [position for position in positions if position.cpm]
    if not positions:
        raise NotFoundPositionWithCMPError(f'Позиции не найдены с cpm для nmid в редис {nmid}')
    def __get_last_update(position: WBItemPosition):
        # Выводим значение timestamp для отладки
        print(f"Timestamp: {position.timestamp}")
        return position.timestamp


    last_position = sorted(positions, key=__get_last_update, reverse=True)[0]
    cpm = last_position.cpm
    return cpm


async def get_good_bad_phrases_for_target_ctr(adv_setting: AdvSetting,
                                              max_cpc: Optional[float] = None,
    pass_time = timedelta(days=7)) -> list[CalculatedKeyword]:
    min_ctr = await get_min_ctr(adv_setting)
    max_position = adv_setting.max_place
    logger.debug('Минимальный ctr получен')
    keyword_stats = await get_keywords_statistic_clickhouse(adv_setting, pass_time)
    async with _sm() as session:
        logger.debug('Начинаю получать фразы')
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting.id)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
    texts_to_keyword_setting = {kws.text: kws for kws in keyword_settings}
    if adv_setting.clusters_mode:
        keyword_stats = await convert_keyword_stats_in_clusters(keyword_stats)
    keyword_stats = await set_positions(keyword_stats, adv_setting)
    async with _sm(read_only=False) as session:
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
    sum_views = 0
    sum_clicks = 0
    try:
        cpm_now = await get_cpm_by_nmid(adv_setting.nmids[0])
    except Exception as e:
        logger.error(f'Ошибка при получении cpm {e}')
        cpm_now = None
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
        calculate_ctr = (real_baes_ctr + predict_ctr) / 2
        keyword_stat.predict_ctr = calculate_ctr
        if max_position:
            try:
                 position = await redis_manager.get_keyword_position(keyword_setting.text, adv_setting.nmids[0])
            except Exception as e:
                position = None
                logger.warning(f'Ошибка получения позиции {e} для {keyword_setting.text} adv_id: {adv_setting.adv_id}' )
            if position:
                organic_position = position.base_position
                if 0 < organic_position <= max_position:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'max_position'
                    await redis_manager.set_auto_block_status(keyword_setting.id, False)
                    await asyncio.sleep(0)
                    continue

        if max_cpc:
            if cpm_now:
                cpc = (cpm_now / 1000)/ keyword_stat.predict_ctr
            elif clicks > 0:
                cpc = views/clicks
            else:
                cpc = None
            if cpc and  cpc > max_cpc:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'max_cpc'
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
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
            sum_views += keyword_stat.views
            sum_clicks += keyword_stat.views * keyword_stat.predict_ctr
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
            sum_views += keyword_stat.views
            sum_clicks += keyword_stat.views * keyword_stat.predict_ctr
            await asyncio.sleep(0)
            continue
        assert keyword_stat.predict_ctr
        await asyncio.sleep(0)
    keyword_stats = sorted(keyword_stats, key=lambda x: x.predict_ctr, reverse=True)


    for keyword_stat in keyword_stats:
        if keyword_stat.status:
            continue
        if keyword_stat.predict_ctr >= min_ctr:
            keyword_stat.status = KeywordStatus.GOOD
            await redis_manager.set_auto_block_status(keyword_stat.keyword_setting.id, False)
            if keyword_stat.base_position != 0:
                sum_views += keyword_stat.views
                sum_clicks += keyword_stat.views * keyword_stat.predict_ctr
        else:
            if adv_setting.target_ctr_mode_strategy == 'forward':
                if sum_views != 0:
                    total_ctr = sum_clicks / sum_views
                else:
                    total_ctr = None
                if not total_ctr or total_ctr >= min_ctr:
                    keyword_stat.status = KeywordStatus.GOOD
                    await redis_manager.set_auto_block_status(keyword_stat.keyword_setting.id, False)
                    if keyword_stat.base_position != 0:
                        sum_views += keyword_stat.views
                        calculate_clicks = keyword_stat.views * keyword_stat.predict_ctr
                        calculate_clicks -= 1
                        if calculate_clicks < 0:
                            calculate_clicks = 0
                        sum_clicks += calculate_clicks
                else:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'min_ctr'
                    await redis_manager.set_auto_block_status(keyword_stat.keyword_setting.id, True)
            elif adv_setting.target_ctr_mode_strategy == 'keep':
                if keyword_stat.base_position:
                    sum_views += keyword_stat.views
                    sum_clicks += keyword_stat.views * keyword_stat.predict_ctr
                if sum_views != 0:
                    total_ctr = sum_clicks / sum_views
                else:
                    total_ctr = None
                if not total_ctr or total_ctr >= min_ctr:
                    keyword_stat.status = KeywordStatus.GOOD
                    await redis_manager.set_auto_block_status(keyword_stat.keyword_setting.id, False)
                else:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'min_ctr'
                    await redis_manager.set_auto_block_status(keyword_stat.keyword_setting.id, True)



    logger.debug('Проверяю статусы ключевых слов с assert')

    for keyword_stat in keyword_stats:
        try:
            assert keyword_stat.status
            assert keyword_stat.status in ['good', 'bad']
        except AssertionError:
            raise AssertionError(f'Статус не установлен для ключевого слова {keyword_stat.text}')

    logger.debug('Слова по assert проверены')
    logger.debug('Возвращаю итоговую статистику')
    return keyword_stats


async def get_full_adv_stat_for_adv_id_from_redis(adv_id: int) -> Optional[FullAdvStat]:
    """Получение Полной статистики из Redis по adv_id"""
    try:
        full_stat_json = await redis_manager.get_full_stat_adv(adv_id)
        full_stat = json.loads(full_stat_json)
        full_stat = FullAdvStat.model_validate(full_stat)
        return full_stat
    except  DataNotFoundError:
        return None

# async def get_max_cpc(adv: AdvSetting)-> Optional[int]:
#     max_cpc = await get_max_cpc_from_max_pay_for_order(adv)
#     if max_cpc and adv.max_cpc:
#         return min(max_cpc, adv.max_cpc)
#     if not max_cpc:
#         return adv.max_cpc
#     if not adv.max_cpc:
#         return max_cpc

#
# async def get_max_cpc_from_max_pay_for_order(adv: AdvSetting)-> Optional[int]:
#     max_pay_for_order: Optional[int]  = adv.max_pay_for_order
#     if not max_pay_for_order:
#         return None
#     all_keywords = await data_manager
#     cpm_now = await get_cpm_by_nmid(adv.nmids[0])
#     if not cpm_now:
#         return None
#     full_stat: FullAdvStat = await get_full_adv_stat_for_adv_id_from_redis(adv.adv_id)
#     if not full_stat:
#         return None
#     else:
#         clicks = full_stat.clicks + 1
#         orders = full_stat.orders + 1
#         need_clicks_for_order = clicks/orders
#         max_cpc = max_pay_for_order / need_clicks_for_order
#         return max_cpc



async def get_good_bad_phrases(adv: AdvSetting)-> list[CalculatedKeyword]:
    # max_cpc = await get_max_cpc_from_max_pay_for_order(adv)
    max_cpc = None
    if not max_cpc:
        max_cpc = adv.max_cpc
    else:
        if max_cpc > adv.max_cpc:
            max_cpc = adv.max_cpc
    if adv.target_ctr_mode:
        keywords =  await get_good_bad_phrases_for_target_ctr(adv,  max_cpc )
    else:
        keywords =  await get_good_bad_phrases_for_min_ctr(adv,  max_cpc )
    for kw in keywords:
        kw.predict_ctr_exponent = adv.exponent_predict_ctr
    keywords_with_rating = [kw for kw in keywords if kw.rating_by_predict_ctr > 0]
    keywords_with_rating.sort(key=lambda x: x.rating_by_predict_ctr, reverse=True)
    keywords_without_rating = [kw for kw in keywords if kw.rating_by_predict_ctr == 0]
    keywords_without_rating.sort(key=lambda x: x.predict_ctr, reverse=True)
    keywords = keywords_with_rating + keywords_without_rating
    return keywords


def __set_predict_ctr(keyword_stats: list[CalculatedKeyword],
                      min_ctr,
                      adv_setting:AdvSetting)->list[CalculatedKeyword]:
    for keyword_stat in keyword_stats:
        keyword_stat.predict_ctr_exponent = adv_setting.exponent_predict_ctr
        original_predict_ctr = keyword_stat.original_predict_ctr
        keyword_setting = keyword_stat.keyword_setting
        if not original_predict_ctr:
            original_predict_ctr = keyword_setting.predict_ctr
        logger.debug(f'Обрабатываю ключевое слово {keyword_stat.text}')
        if min_ctr == 0:
            enough_views = 100
        else:
            enough_views = int(1 / min_ctr)
        keyword_stat.enough_views = enough_views
        views = keyword_stat.views
        clicks = keyword_stat.clicks
        if clicks == 0:
             clicks += 1
             views += enough_views
        original_baes_ctr = clicks / views
        keyword_stat.baes_ctr = original_baes_ctr
        added_clicks = keyword_setting.added_clicks
        if added_clicks:
            clicks += added_clicks
        if original_predict_ctr:
            predicted_views = int(clicks + 1 / original_predict_ctr)
            predicted_clicks = int(predicted_views * original_predict_ctr)
            views += predicted_views
            clicks += predicted_clicks + 1
        baes_predict_ctr = clicks / views
        keyword_stat.predict_ctr = baes_predict_ctr
        keyword_stat.baes_predict_ctr = baes_predict_ctr
        keyword_stat.calculated_clicks = clicks
        keyword_stat.calculated_views = views
    return keyword_stats


async def get_good_bad_phrases_for_min_ctr(adv_setting: AdvSetting,
                                           max_cpc = None,
                                           pass_time = timedelta(days=7))->list[CalculatedKeyword]:

    min_ctr = await get_min_ctr(adv_setting)
    max_position = adv_setting.max_place
    logger.debug('Минимальный ctr получен')
    keyword_stats = await get_keywords_statistic_clickhouse(adv_setting, pass_time)
    async with _sm() as session:
        logger.debug('Начинаю получать фразы')
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting.id)
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = result.unique().scalars().all()
        logger.debug('Получил ключи')
    texts_to_keyword_setting = {kws.text: kws for kws in keyword_settings}
    if adv_setting.clusters_mode:
        logger.debug('Начинаю конвертацию в кластеры')
        keyword_stats = await convert_keyword_stats_in_clusters(keyword_stats)
        logger.debug('В кластеры сконвертировали')
    logger.debug('Начинаю установку позиций')
    keyword_stats = await set_positions(keyword_stats, adv_setting)
    async with _sm(read_only=False) as session:
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
                try:
                    result_hard_status = max(stat_hard_statuses.items(), key=lambda x: x[1])[0]
                except:
                    result_hard_status = 1
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
        if text not in texts_in_keyword_stat:
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
    adv_id = adv_setting.adv_id
    texts = [kw.text for kw in keyword_stats]
    text_to_predict_ctr: dict[str, float]\
        = await redis_manager.get_adv_id_to_text_predict_ctr_dict(adv_id, texts)
    # keyword_positions = await redis_manager.get_keywords_positions(adv_setting, texts)
    # text_to_keyword_position: dict[str, WBItemPosition]\
    #     = {position.keyword_text: position for position in keyword_positions}
    try:
        cpm_now = await get_cpm_by_nmid(adv_setting.nmids[0], texts)
    except Exception as e:
        logger.error(f'Ошибка при получении cpm {e}', exc_info=True)
        cpm_now = None
    new_statuses = []


    for keyword_stat in keyword_stats:
        text = keyword_stat.text
        keyword_setting = keyword_text_to_keyword_setting[text]
        keyword_stat.keyword_setting = keyword_setting
        keyword_stat.hard_status = keyword_setting.hard_status
        original_predict_ctr = text_to_predict_ctr.get(text, None)
        keyword_stat.original_predict_ctr = original_predict_ctr

    keyword_stats: list[CalculatedKeyword] = __set_predict_ctr(keyword_stats, min_ctr, adv_setting)

    best_keyword = get_best_keyword(keyword_stats)
    best_keyword.best_keyword_status = True

    for keyword_stat in keyword_stats:
        clicks = keyword_stat.calculated_clicks
        views = keyword_stat.calculated_views
        enough_views = keyword_stat.enough_views
        original_predict_ctr = keyword_stat.original_predict_ctr
        hard_status = keyword_stat.hard_status
        if max_position:
            try:
                position = keyword_stat.position
            except:
                logger.error('Не удалось получить позицию')
                position = None
            if position:
                organic_position = position.base_position
                if 0 < organic_position <= max_position:
                    keyword_stat.status = KeywordStatus.BAD
                    keyword_stat.reason = 'max_position'
                    new_statuses.append((keyword_setting.id, False, ))
                    await asyncio.sleep(0)
                    continue
        if max_cpc:
            if cpm_now:
                cpc = (cpm_now / 1000) / keyword_stat.predict_ctr
            elif clicks > 0:
                cpc = views / clicks
            else:
                cpc = None
            if cpc and cpc > max_cpc:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = 'max_cpc'
                await redis_manager.set_auto_block_status(keyword_setting.id, False)
                await asyncio.sleep(0)
                continue

        if not original_predict_ctr and enough_views/2 > keyword_stat.views and not adv_setting.min_views_for_ml_predict and  keyword_setting.hard_status in [1, 2]:
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
            await redis_manager.set_auto_block_status(keyword_setting.id, True)
            await asyncio.sleep(0)
            continue

        if hard_status == 3:
            keyword_stat.status = KeywordStatus.BAD
            keyword_stat.reason = 'turn_off'
            await redis_manager.set_auto_block_status(keyword_setting.id, False)
            await asyncio.sleep(0)
            continue
        if hard_status == 2:
           keyword_stat.status = KeywordStatus.GOOD
           keyword_setting.auto_block = False
           await redis_manager.set_auto_block_status(keyword_setting.id, False)
           await asyncio.sleep(0)
           continue
        elif hard_status == 0:
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
        baes_predict_ctr = keyword_stat.baes_predict_ctr
        if baes_predict_ctr >= min_ctr:
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
    await redis_manager.set_auto_block_statuses(new_statuses)
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


    # async def get_full_df(self, shops: list[WBUserCabinet]):
    #     shops_df_tasks = [self.get_df_for_shop(shop) for shop in shops]
    #     shops_dfs = await asyncio.gather(*shops_df_tasks)
    #     df = pd.concat(shops_dfs)
    #     return df


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


    # async def get_df_for_shop(self, shop: WBUserCabinet) -> pd.DataFrame:
    #     wb_api = WBApi(shop)
    #     companies = await wb_api.advert.get_all_adv_companies()
    #     keywords_dfs = []
    #     for company in companies:
    #         logger.debug('Начинаю получать ключи')
    #         answer = await wb_api.advert.get_keywords_stat(company)
    #         logger.debug('Ключи получены')
    #         await asyncio.sleep(10)
    #         if answer == []:
    #             continue
    #         df = self.__get_df_from_date_answer(answer, company)
    #         keywords_dfs.append(df)
    #     if keywords_dfs == []:
    #         return pd.DataFrame()
    #     df = pd.concat(keywords_dfs)
    #     return df

    # async def get_cards_for_shop(self, shop: WBUserCabinet):
    #     wb_api = WBApi(shop)
    #     cards: list[CardFromWB] = await wb_api.advert.get_cards()
    #     for card in cards:
    #         card.shop_name = shop.name
    #     return cards

    @staticmethod
    def get_nmid_offer_id_df(cards: list[CardFromWB]) -> pd.DataFrame:
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

    @staticmethod
    async def get_item_features_from_redis(nmids_batch):
        result = await redis_manager.get_nmid_vectors(nmids_batch)
        return result

    async def get_keyword_features_from_neo(self, keywords):
        result = await self._gds.get_keywords_vectors_by_keywords(keywords)
        return result

    @staticmethod
    async def get_keyword_features_from_redis(keywords)->list[tuple[str, list[float]]]:
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




async def get_main_photos(nmids: list[int])-> list[str]:
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
        try:
            min_ctr = await get_min_ctr(adv_setting)
            logger.debug('min_ctr получен')
            adv_id_to_min_ctr[adv_setting.adv_id] = min_ctr
        except Exception as e:
            logger.error(f'Ошибка при получении min_ctr {e}', exc_info=True)
            adv_id_to_min_ctr[adv_setting.adv_id] = 0.03
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
    if not adv.new_auto_min_ctr_mode:
        hard_min_ctr = adv.hard_min_ctr
        if not hard_min_ctr:
            return 0.1
        else:
            return adv.hard_min_ctr
    min_ctr = await _get_min_ctr(adv)
    # else:
    #     min_ctr = await _get_new_min_ctr(adv)
    return min_ctr


def get_best_keyword(keywords: list[CalculatedKeyword])-> Optional[CalculatedKeyword]:
    if not keywords:
        return None
    best_keyword = sorted(keywords, key=lambda x: x.rating_by_predict_ctr, reverse=True)[0]
    return best_keyword


async def _get_new_min_ctr(adv: AdvSetting):
    keywords: list[CalculatedKeyword] = await get_keywords_statistic_clickhouse(adv,
                                                                      timedelta(days=7))
    best_keyword = get_best_keyword(keywords)
    if not keywords:
        return 0.05

    for keyword in keywords:
        position = await redis_manager.get_keyword_position(keyword.text, adv.nmids[0])
        if not position or position.base_position == 0:
            continue
        keyword.predict_ctr = await redis_manager.get_predict_ctr(adv.adv_id, keyword.text)

    logger.debug(f'Лучшее ключевое слово {best_keyword.text} с рейтингом {best_keyword.rating_by_predict_ctr}')
    best_predict_ctr = best_keyword.predict_ctr
    if not best_predict_ctr:
        return 0.09
    return best_predict_ctr


async def _get_min_ctr(adv: AdvSetting):
    async with _sm(read_only=True) as session:
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
        query = """
        WITH
            latest_versions AS (
                SELECT
                    text,
                    date,
                    MAX(version) AS latest_version
                FROM
                    default_db.advkeyword
                WHERE
                    adv_id = %(adv_id)s
                    AND text IN %(texts)s
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
                    a.adv_id = %(adv_id)s
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
            total_clicks > 0
        """

        params = {
            "adv_id": adv_id,
            "texts": tuple(texts),
        }

        try:
            async with get_clickhouse_client() as client:
                result = await client.query(query, params)
                rows = result.result_rows
        except Exception:
            logger.error(f'Ошибка получения статистики из ch', exc_info=True)
            raise



        text_to_real_ctr = {row[0]: row[1] for row in rows}
        real_ctrs  = []
        predict_ctrs = []
        for kw in keyword_settings:
            real_ctr = text_to_real_ctr.get(kw.text)
            if real_ctr:
                real_ctrs.append(text_to_real_ctr[kw.text])
            predict_ctr = await redis_manager.get_predict_ctr(adv_id, kw.text)
            if predict_ctr:
                predict_ctrs.append(predict_ctr)
        if predict_ctrs:
            return float(min(predict_ctrs))

        if real_ctrs:
            return float(min(real_ctrs))

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
    async with _sm(read_only=False) as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(need_nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = result.unique().scalars().all()
        await session.delete(wb_cards)
        await session.commit()


async def clear_keywords(need_keywords):
    async with _sm(read_only=False) as session:
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
    async with _sm(read_only=False) as session:
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


async def get_need_nmids_for_parsing(text, adv_id, adv_ids):
    adv_ids_with_text: set[int] = await get_nmids_for_keyword_text(text)
    nmids_need = set()
    not_found_adv_id = set()
    for adv_id_with_text in adv_ids_with_text:
        if adv_id_with_text not in adv_ids:
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
    return nmids_need




# async def get_last_updated_phrases(all_white_phrases):
#     async with _sm() as session:
#         stmt = select(CommonKeyword.text)\
#             .where(CommonKeyword.text.in_(all_white_phrases))\
#             .order_by(CommonKeyword.updated_at)
#         result = await session.execute(stmt)
#         last_updated_phrases = result.scalars().all()
#         return last_updated_phrases


async def get_keywords_positions_dict_by_text(adv_setting: AdvSetting, texts: list[str]) -> dict[str, WBItemPosition]:
    positions =  await redis_manager.get_keywords_positions(adv_setting, texts)
    positions = [position for position in positions if position]
    positions = {position.keyword_text: position for position in positions}
    return positions


async def add_white_phrases(keywords: list[str], adv_setting_id: int):
    async with _sm(read_only=False) as session:
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
    async with _sm(read_only=False) as session:
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


async def get_users_from_nmid(nmid: int):
    try:
        async with _sm() as session:
            # Создаем алиас для AdvSetting
            adv_setting_alias = aliased(AdvSetting)
            # Запрос для получения уникальных пользователей
            stmt = select(User).distinct() \
                .join(WBUserCabinet, WBUserCabinet.user_id == User.id) \
                .join(WBCabinet, WBCabinet.id == WBUserCabinet.wb_cabinet_id) \
                .join(adv_setting_alias, WBCabinet.adv_settings) \
                .where(adv_setting_alias.nmids.contains([nmid])) \
                .options(subqueryload(User.wb_user_cabinets))

            result = await session.execute(stmt)
            users = result.scalars().all()
            return users
    except Exception as e:
        logger.error('Ошибка при получении пользователей по nmid', exc_info=True)
        return []


async def add_relevant_phrases(keywords, adv_setting_id):
    async with _sm(read_only=False) as session:
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
            if keyword_setting.hard_status == 0:
                keyword_setting.hard_status = 1
        await session.commit()


async def get_active_search_advs():
    pattern = r'<!-\[(\d+)\]-!>'
    stmt = select(AdvSetting).where(
        # Проверяем, что name содержит паттерн <!-[цифры]-!>
        AdvSetting.name.op('~')(pattern),
        AdvSetting.bot_active == True,
        AdvSetting.active_status == 'started'
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
    return adv_settings


async def get_all_active_shop_ids_with_active_advs():
    stmt = select(WBCabinet.shop_id)\
        .join(WBCabinet.adv_settings)\
    .where(AdvSetting.bot_active == True)
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return shop_ids



async def get_all_shop_ids()-> list[str]:
    stmt = select(WBCabinet.shop_id).distinct()
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return shop_ids


async def get_active_adv_ids_for_shop(shop_id: str):
    stmt = select(AdvSetting).distinct()\
        .join(AdvSetting.wb_cabinet)\
        .where(WBCabinet.shop_id == shop_id,
               AdvSetting.bot_active == True)\
    .options(load_only(AdvSetting.adv_id, AdvSetting.name,
                       AdvSetting._search_adv_id))
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = result.scalars().all()
    adv_ids = []
    for adv in adv_settings:
        adv_ids.append(adv.adv_id)
        if (search_adv_id := adv.search_adv_id):
            adv_ids.append(search_adv_id)

    return adv_ids


async def get_keywords_statistic(adv_setting)-> list[CalculatedKeyword]:
    keywords = await get_keywords_statistic_clickhouse(adv_setting,
                                                       last_views=3000)
    return keywords


async def get_max_adv_bid(adv_setting: AdvSetting):
    setting_max_bid = adv_setting.max_cpm
    max_pay_for_order = adv_setting.max_pay_for_order
    if not max_pay_for_order:
        return setting_max_bid
    if adv_setting.auto_max_bid:
        keywords: list[CalculatedKeyword] = await get_keywords_statistic(adv_setting)
        full_keyword_stat = await get_full_adv_stat_for_adv_id_from_redis(adv_setting.adv_id)
        if not full_keyword_stat:
            return setting_max_bid
        views = full_keyword_stat.views + 1
        orders = full_keyword_stat.orders + 1
        best_keyword: CalculatedKeyword = get_best_keyword(keywords)
        convert_views_to_order = views / orders
        ctr = best_keyword.predict_ctr
        max_bid_for_1000_views = (max_pay_for_order / convert_views_to_order) * ctr * 1000
        if setting_max_bid < max_bid_for_1000_views:
            setting_max_bid = max_bid_for_1000_views
    return setting_max_bid


async def _get_down_scale_white_list_bust_wb_item_position(adv)-> Optional[int]:
    stmt = select(KeywordSetting.text).where(KeywordSetting.hard_status == 2,
                                             KeywordSetting.adv_setting_id == adv.id)
    async with _sm() as session:
        result = await session.execute(stmt)
        white_phrases = result.scalars().all()
    positions: dict[str, WBItemPosition] = await get_keywords_positions_dict_by_text(adv, white_phrases)
    if positions:
        positions = [position for position in positions.values()]
        positions = [position for position in positions if position.promo_position]
        if positions:
            position: WBItemPosition = sorted(positions, key=lambda x: x.promo_position, reverse=True)[0]
        else:
            return None
    else:
         return None
    return position.promo_position


async def is_adv_in_favorites(adv_setting_original_id: int, user_original_id: int) -> bool:
    stmt = select(favorite_advs_association).where(
        favorite_advs_association.c.user_id == user_original_id,
        favorite_advs_association.c.adv_id == adv_setting_original_id
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.first() is not None


async def set_worst_promo_position(adv_settings: list[AdvSetting]):
    for adv in adv_settings:
        if not adv.bot_active or not adv.active_status == 'started':
            adv.worst_promo_position = None
            continue
        position: int = await _get_down_scale_white_list_bust_wb_item_position(adv)
        if position:
            adv.worst_promo_position = position
        else:
            adv.worst_promo_position = None
    return adv_settings


def __calculate_version(position):
    return int(position.timestamp.timestamp())


import asyncio
from datetime import datetime
from dataclasses import dataclass


async def get_avg_base_positions(nmid: int, start_date: str, end_date: str):
    query = """
    SELECT toDate(timestamp) as date, 
       text,
       AVG(base_position) as avg_base_position
FROM default_db.wbitemposition
WHERE nmid = %(nmid)s 
  AND timestamp >= toDateTime(%(start_date)s)
  AND timestamp <= toDateTime(%(end_date)s)
GROUP BY date, text
ORDER BY date, text

    """  # Removed the semicolon

    parameters = {
        "nmid": nmid,
        "start_date": start_date,
        "end_date": end_date
    }

    async with get_clickhouse_client() as client:
        result = await client.query(query, parameters=parameters)
        result = result.result_rows
        return [WBItemPosition(nmid=nmid, base_position=row[1], timestamp=row[0]) for row in result]


async def add_positions_to_clickhouse(positions: list[WBItemPosition]):
    async with get_clickhouse_client() as client:
        for position in positions:
            try:
                # Генерация версии и подготовка timestamp
                version = __calculate_version(position)
                timestamp_str = position.timestamp.strftime('%Y-%m-%d %H:%M:%S')

                # Всегда вставляем новые данные
                query_insert = f"""
                INSERT INTO default_db.wbitemposition (
                    nmid,
                    text,
                    promo_position,
                    base_position,
                    cpm,
                    adv_type,
                    timestamp,
                    version
                )
                VALUES (
                    {position.nmid},
                    '{position.keyword_text.replace("'", "''")}',  # Экранирование одинарных кавычек
                    {position.promo_position if position.promo_position else 0},
                    {position.base_position if position.base_position else 0},
                    {position.cpm if position.cpm else 0},
                    {int(position.adv_type) if position.adv_type else 0},
                    '{timestamp_str}',
                    {version}
                )
                """
                await client.query(query_insert)
                logger.debug(f"Добавлена запись для nmid={position.nmid}")

            except Exception as e:
                logger.error(f"Ошибка при обработке позиции nmid={position.nmid}: {e}", exc_info=True)





async def get_keyword_positions_from_click_house(nmid) -> List[WBItemPosition]:
    query = f"""
    SELECT
        text,
        toDate(timestamp) AS day,
        AVG(promo_position) AS avg_promo_position,
        AVG(base_position) AS avg_base_position,
        AVG(cpm) AS avg_cpm
    FROM default_db.wbitemposition
    WHERE nmid = {nmid}
    GROUP BY text, day
    ORDER BY day
    """

    async with get_clickhouse_client() as client:
        result = await client.query(query)
        positions_rows = result.result_rows
    positions = []
    for row in positions_rows:
        position = WBItemPosition()
        position.nmid = nmid
        position.keyword_text = row[0]
        position.promo_position = row[2] if row[2] else 6000
        position.base_position = row[3] if row[3] else 6000
        position.cpm = row[4]
        position.timestamp = datetime.combine(row[1], datetime.min.time())
        positions.append(position)

    return positions

async  def set_last_full_stat_update(adv_id: int, timestamp: datetime):
    await redis_manager.set_last_full_stat_update(adv_id, timestamp)


async def get_last_full_stat_update(adv_id: int):
    return await redis_manager.get_last_full_stat_update(adv_id)


async def get_all_keywords_from_ch(last_days=7) -> set[str]:
    ch_query = f"""
    SELECT DISTINCT text FROM default_db.advkeyword 
    WHERE date >= today() - %(last_days)s
    """

    async with get_clickhouse_client() as client:
        result = await client.query(ch_query, parameters={"last_days": last_days})
        keywords = result.result_rows
    return set([keyword[0] for keyword in keywords if keyword])


async def get_sum_bot_balance_from_wb_wb_user_cabinet_original_id(shop_id: str):
    stmt = select(func.sum(coalesce(WBCabinet.balance, 0)\
                           + coalesce(WBCabinet.bonus, 0))) \
        .where(WBCabinet.shop_id  == shop_id)
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.scalar_one()