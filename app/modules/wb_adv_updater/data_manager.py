import cProfile
import io
import json
import logging
import pstats
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from PIL import Image  # type: ignore
from sqlalchemy import and_, func, select, case, Float, cast
from sqlalchemy.dialects.postgresql import insert

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy.sql.functions import coalesce

from app.exc import (
    CardNotFoundInDB,
)
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.exceptions import NotItemsInAdvSetting
from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    AdvSetting,
    KeywordSetting,
    WBCabinet,
    WBCard,
    WBCategory,
    WBItemPosition,
    WBUserCabinet,
)
from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat
from app.modules.keywords_query import keywords_query
from app.modules.wb_adv_updater.min_ctr_manager.min_ctr_manager import MinCtrManager
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from app.utils.redis_manager.exc import DataNotFoundError
from . import get_text_to_predict_ctr_dict
from ..common_slaves.wildberries.shops_data_updater import ShopDataUpdater
logger = logging.getLogger(__name__)

_sm = get_async_session_maker


async def get_keyword_statistic_clickhouse(
    client: Any,
    text: str,
    adv_ids: set[int],
    pass_days: int | None = 7,
) -> tuple[int, int, float]:
    """
    Возвращает суммарную статистику по ключевому слову text из агрегирующей таблицы advkeyword_new:
    - total_clicks
    - total_views
    - total_spend

    Таблица хранит агрегаты вида argMaxState(...), которые нужно раскрывать через argMaxMerge().
    """

    today = datetime.now().date()
    start_date_clause = ""
    if pass_days:
        start_date = today - timedelta(days=pass_days)
        start_date_clause = f"AND date >= '{start_date}'"

    adv_ids_str = ", ".join(map(str, adv_ids))
    # TODO: Прикрутить к Pycharm ClickHouse плагин и проверить запрос
    query = f"""

        SELECT
            COALESCE(SUM(total_clicks), 0) AS total_clicks,
            COALESCE(SUM(total_views), 0)  AS total_views,
            COALESCE(SUM(total_spend), 0)  AS total_spend
        FROM (
            SELECT
                argMaxMerge(clicks_state) AS total_clicks,
                argMaxMerge(views_state)  AS total_views,
                argMaxMerge(spend_state)  AS total_spend
            FROM default_db.advkeyword_new
            WHERE
                adv_id IN ({adv_ids_str})
                AND text = %(text)s
                {start_date_clause}
            GROUP BY adv_id, text, date
        ) AS merged
    """

    result = await client.query(query, parameters={"text": text})

    if not result.result_rows:
        return 0, 0, 0.0

    total_clicks, total_views, total_spend = result.result_rows[0]

    # исправляем кейс, когда кликов больше показов (из-за округлений или некорректных данных)
    if total_clicks > total_views:
        total_views = total_clicks

    return int(total_clicks), int(total_views), float(total_spend)


async def get_keywords_statistic_clickhouse(
    adv_setting: AdvSetting,
    pass_time: timedelta | None = timedelta(days=7),
    last_views: int | None = None,
) -> list[CalculatedKeyword]:
    async with get_clickhouse_client() as ch_client:
        advs: set[int] = set()
        auto_adv_id = int(adv_setting.adv_id)
        advs.add(auto_adv_id)
        if search_adv_id := adv_setting.search_adv_id:
            advs.add(search_adv_id)
        query = _build_clickhouse_query(advs, pass_time, last_views)
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
                text=text, clicks=clicks, views=views, spend=spend
            )
            keywords.append(keyword)

    return keywords


async def _get_keyword_settings(
    adv_setting_id: int, hard_statuses: list[int] | None
) -> list[KeywordSetting]:
    async with _sm() as session:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting_id
        )
        if hard_statuses:
            stmt = stmt.where(KeywordSetting.hard_status.in_(hard_statuses))
        result = await session.execute(stmt)
        return list(result.scalars().all())


def _build_clickhouse_query(
    adv_ids: set[int],
    pass_time: timedelta | None = None,
    last_views: int | None = None,
) -> str:
    """
    Запрос для ClickHouse AggregatingMergeTree-таблицы default_db.advkeyword_new
    (fields: adv_id, text, date, clicks_state, views_state, spend_state)
    Возвращает: text, total_clicks, total_views, total_spend, date
    """

    adv_ids_str = ", ".join(str(aid) for aid in adv_ids)

    # --- Внутренний подзапрос: извлекаем агрегаты для каждой кампании ---
    inner = [
        "SELECT",
        "    adv_id,",
        "    text,",
        "    argMaxMerge(clicks_state) AS total_clicks,",
        "    argMaxMerge(views_state)  AS total_views,",
        "    argMaxMerge(spend_state)  AS total_spend,",
        "    date",
        "FROM default_db.advkeyword_new",
        f"WHERE adv_id IN ({adv_ids_str})",
    ]

    if pass_time:
        start_time = datetime.now() - pass_time
        inner.append(f"  AND date >= '{start_time.strftime('%Y-%m-%d')}'")

    inner.append("GROUP BY adv_id, text, date")
    inner_query = "\n".join(inner)

    # --- Внешний уровень: суммируем по text/date ---
    outer = [
        "SELECT",
        "    text,",
        "    SUM(total_clicks) AS total_clicks,",
        "    SUM(total_views)  AS total_views,",
        "    SUM(total_spend)  AS total_spend,",
        "    date",
        "FROM (",
        inner_query,
        ") AS merged",
        "GROUP BY text, date",
    ]
    query = "\n".join(outer)

    # --- Если есть last_views — оборачиваем в CTE ---
    if last_views:
        query = f"""
WITH base AS (
{query}
),
cumulative AS (
    SELECT
        text,
        total_clicks,
        total_views,
        total_spend,
        date,
        SUM(total_views) OVER (PARTITION BY text ORDER BY date DESC) AS cumulative_total_views
    FROM base
)
SELECT
    text,
    SUM(total_clicks) AS total_clicks,
    SUM(total_views)  AS total_views,
    SUM(total_spend)  AS total_spend
FROM cumulative
WHERE cumulative_total_views <= {last_views}
GROUP BY text
""".strip()

    return query


async def get_global_super_wb_user_cabinet() -> WBUserCabinet:
    async with _sm() as session:
        stmt = select(User).options(selectinload(User.wb_tokens))
        result = await session.execute(stmt)
        users: Sequence[User] = list(result.unique().scalars().all())
        all_tokens = [wb_token for user in users for wb_token in user.wb_tokens]
        super_user = User()
        super_user.wb_tokens = all_tokens
        wb_user_cabinet = WBUserCabinet()
        wbcabinet = WBCabinet()
        wb_user_cabinet.wb_cabinet = wbcabinet
        wb_user_cabinet.user = super_user
    return wb_user_cabinet


def __sort_by_update_keyword(keyword: WBItemPosition) -> datetime:
    if not (update := keyword.timestamp):
        update = datetime.now() - timedelta(days=1000)
    return update


async def set_positions(
    keyword_stats: list[CalculatedKeyword], adv_setting: AdvSetting
) -> list[CalculatedKeyword]:
    texts = [keyword.text for keyword in keyword_stats]
    positions = await redis_manager.get_keywords_positions(adv_setting, texts)
    if not positions:
        return keyword_stats
    text_to_position = {position.keyword_text: position for position in positions}
    for keyword_stat in keyword_stats:
        text = keyword_stat.text
        data = await redis_manager.get_cluster_and_preset(text)
        if not data:
            continue
        cluster, preset = data
        keyword_stat.cluster_name = cluster
        keyword_stat.preset = preset
        if position := text_to_position.get(text):
            # После изменений WB у нас одна позиция
            keyword_stat.position = position.position
        else:
            keywords = keyword_stat.childs_keywords
            if keywords:
                texts = [kw.text for kw in keywords]
                positions = await redis_manager.get_keywords_positions(
                    adv_setting, texts
                )  # type: ignore[no-untyped-call]
                if positions:
                    position = max(
                        positions, key=lambda kw: __sort_by_update_keyword(kw)
                    )
                    keyword_stat.position = position.position

    return keyword_stats


async def set_position(
    keyword_stat: CalculatedKeyword, adv_setting: AdvSetting
) -> CalculatedKeyword:
    text = keyword_stat.text
    main_nmid = int(adv_setting.nmids[0])
    position = await redis_manager.get_keyword_position(text, main_nmid)
    if position:
        keyword_stat.position = position.position

    else:
        keywords = keyword_stat.childs_keywords
        if keywords:
            texts = [kw.text for kw in keywords]
            # Type ignore for untyped redis_manager call
            positions = await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call]
            if positions:
                position = max(positions, key=lambda kw: __sort_by_update_keyword(kw))
                assert position
                keyword_stat.position = position.position

    return keyword_stat


async def get_keywords_positions(
    adv_setting: AdvSetting, texts: list[str]
) -> list[WBItemPosition]:
    """Get keywords positions from Redis."""
    # Type ignore for untyped redis_manager call and return type
    return await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call,no-any-return]


def __calculate_clusters(
    preset_to_keywords: dict[Any, list[CalculatedKeyword]],
    preset_to_cluster_name: dict[Any, str],
) -> list[CalculatedKeyword]:
    keyword_stats = []
    for preset in preset_to_keywords:
        keywords = preset_to_keywords[preset]
        keyword_cluster_name = preset_to_cluster_name[preset]
        views = 0
        clicks = 0
        spend = 0
        query: int = 0
        for keyword in keywords:
            views += keyword.views
            clicks += keyword.clicks
            spend += int(keyword.spend)
            if isinstance(keyword.query, int):
                query += keyword.query
            elif isinstance(keyword.query, str) and keyword.query.isdigit():
                query += int(keyword.query)

        cluster_keyword = CalculatedKeyword(
            text=keyword_cluster_name, views=views, clicks=clicks, spend=spend
        )
        cluster_keyword.query = str(query) if query else "<50"
        cluster_keyword.childs_keywords = keywords
        keyword_stats.append(cluster_keyword)

    return keyword_stats


def profile_function(inner_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    inner_func(*args, **kwargs)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(10)


async def convert_keyword_stats_in_clusters(
    keyword_stats: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    preset_to_keywords = defaultdict(list)
    preset_to_cluster_name = {}
    texts = [keyword.text for keyword in keyword_stats]
    try:
        text_to_custer_and_present: dict[str, tuple[str, int]] = (
            await redis_manager.get_clusters_and_presets(texts)
        )
    except Exception as e:
        logger.error(
            f"Ошибк {e} получения кластеров и пресетов: {texts}", exc_info=True
        )
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


# Функции get_cpm_by_nmid и __get_cpm_from_positions удалены,
# так как CPM больше не доступен из позиций парсинга


async def get_full_adv_stat_for_adv_id_from_redis(adv_id: int) -> FullAdvStat | None:
    """Получение Полной статистики из Redis по adv_id"""
    try:
        full_stat_json = await redis_manager.get_full_stat_adv(adv_id)
        full_stat = json.loads(full_stat_json)
        full_stat = FullAdvStat.model_validate(full_stat)
        return full_stat
    except DataNotFoundError:
        return None


async def get_good_bad_phrases(adv: AdvSetting) -> list[CalculatedKeyword]:
    keywords: list[CalculatedKeyword] = await get_good_bad_phrases_for_min_ctr(
        adv, int(adv.max_cpc) if adv.max_cpc is not None else None
    )
    for kw in keywords:
        kw.predict_ctr_exponent = adv.exponent_predict_ctr
    keywords_redis_cache_manager = RedisCalculatedKeywordsCacheManager()
    await keywords_redis_cache_manager.set_calculated_keywords(
        keywords, int(adv.adv_id)
    )
    # Сортировка и возврат результатов
    keywords_with_rating = [kw for kw in keywords if kw.rating_by_predict_ctr > 0]
    keywords_with_rating.sort(key=lambda x: x.rating_by_predict_ctr, reverse=True)
    keywords_without_rating = [kw for kw in keywords if kw.rating_by_predict_ctr == 0]

    keywords_without_rating.sort(key=lambda x: x.predict_ctr, reverse=True)
    keywords = keywords_with_rating + keywords_without_rating
    return keywords


async def get_cached_keyword(adv: AdvSetting, text: str) -> CalculatedKeyword | None:
    """Получить закешированное ключевое слово"""
    cache_key = f"good_bad_phrases:{adv.id}:{adv.updated_at.timestamp()}:{text}" # type: ignore
    cached_data = await redis_manager.get(cache_key)

    if cached_data and isinstance(cached_data, str):
        return CalculatedKeyword.model_validate_json(cached_data)
    return None


def __set_predict_ctr(
    keyword_stats: list[CalculatedKeyword], min_ctr: float, adv_setting: AdvSetting
) -> list[CalculatedKeyword]:
    for keyword_stat in keyword_stats:
        keyword_stat.predict_ctr_exponent = adv_setting.exponent_predict_ctr
        original_predict_ctr = keyword_stat.original_predict_ctr
        if not original_predict_ctr:
            original_predict_ctr = keyword_stat.predict_ctr
        logger.debug("Обрабатываю ключевое слово %s", keyword_stat.text)
        if min_ctr == 0:
            enough_views_calc = 100
        else:
            enough_views_calc = int(1 / min_ctr)
        keyword_stat.enough_views = enough_views_calc
        views = keyword_stat.views
        clicks = keyword_stat.clicks
        if clicks == 0:
            clicks += 1
            views += enough_views_calc
        if views == 0:
            views = 1
        original_baes_ctr = clicks / views
        keyword_stat.baes_ctr = original_baes_ctr
        added_clicks = keyword_stat.added_clicks
        if added_clicks:
            clicks += added_clicks
        if original_predict_ctr:
            predicted_views = int(clicks + 1 / original_predict_ctr)
            predicted_clicks = int(predicted_views * original_predict_ctr)
            views += predicted_views
            clicks += predicted_clicks + 1
        # TODO: тут вылетает ошибка деления  на ноль временно делаю views = 1 если 0
        if views == 0:
            views = 1
        baes_predict_ctr = clicks / views
        keyword_stat.predict_ctr = baes_predict_ctr
        keyword_stat.baes_predict_ctr = baes_predict_ctr
        keyword_stat.calculated_clicks = clicks
        keyword_stat.calculated_views = views
    return keyword_stats


# @profile
async def get_good_bad_phrases_for_min_ctr(
    adv_setting: AdvSetting,
    max_cpc: int | None = None,
    pass_time: timedelta | None = timedelta(days=7),
) -> list[CalculatedKeyword]:
    min_ctr = await get_min_ctr(adv_setting)
    logger.debug("Минимальный ctr получен")
    keyword_stats = await get_keywords_statistic_clickhouse(
        adv_setting,
        pass_time,
    )
    async with _sm() as session:
        logger.debug("Начинаю получать фразы")
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv_setting.id
        )
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
        logger.debug("Получил ключи")
    texts_to_keyword_setting: dict[str, KeywordSetting] = {
        str(kws.text): kws for kws in keyword_settings
    }
    texts_in_keyword_stat = {kw.text for kw in keyword_stats}
    text_to_keyword_setting: dict[str, KeywordSetting] = {
        str(kw.text): kw for kw in keyword_settings
    }

    if adv_setting.clusters_mode:
        logger.debug("Начинаю конвертацию в кластеры")
        keyword_stats = await convert_keyword_stats_in_clusters(keyword_stats)
        logger.debug("В кластеры сконвертировали")
    logger.debug("Начинаю установку позиций")
    try:
        keyword_stats_positioned: list[CalculatedKeyword] = await set_positions(
            keyword_stats, adv_setting
        )
    except Exception as exc:
        raise exc
    async with _sm(read_only=False) as session:
        for keyword_stat in keyword_stats_positioned:
            keyword_text = keyword_stat.text
            keyword_setting = texts_to_keyword_setting.get(keyword_text)
            if not keyword_setting:
                clusters = keyword_stat.childs_keywords or []
                clusters.append(keyword_stat)

                stat_hard_statuses: dict[int, int] = defaultdict(int)
                for kw in clusters:
                    original_text = kw.text
                    if keyword := texts_to_keyword_setting.get(original_text):
                        stat_hard_statuses[keyword.hard_status] += 1

                result_hard_status = (
                    max(stat_hard_statuses.items(), key=lambda x: x[1])[0]
                    if stat_hard_statuses
                    else 1
                )

                insert_stmt = (
                    insert(KeywordSetting)
                    .values(
                        text=keyword_text,
                        adv_setting_id=adv_setting.id,
                        hard_status=result_hard_status,
                    )
                    .on_conflict_do_nothing(index_elements=["text", "adv_setting_id"])
                )
                await session.execute(insert_stmt)

                # теперь получаем из БД (он там точно есть: либо только что вставили, либо уже был)
                keyword_setting = await session.scalar(
                    select(KeywordSetting).where(
                        and_(
                            KeywordSetting.text == keyword_text,
                            KeywordSetting.adv_setting_id == adv_setting.id,
                        )
                    )
                )

                assert keyword_setting is not None
                text_to_keyword_setting[keyword_text] = keyword_setting

        await session.commit()

    for keyword_setting in keyword_settings:
        text = str(keyword_setting.text)
        if text not in texts_in_keyword_stat:
            keyword_setting_for_text = text_to_keyword_setting[text]

            keyword_new = CalculatedKeyword(
                text=text,
                clicks=0,
                views=0,
                spend=0,
                keyword_setting_original_id=keyword_setting_for_text.id,
            )
            position = await redis_manager.get_keyword_position(
                text, adv_setting.nmids[0]
            )
            if position:
                keyword_new.position = position.position
                keyword_new.position_update = position.timestamp
            keyword_new.query = keywords_query.get_queries_of_keyword(text)
            keyword_stats.append(keyword_new)

    texts = [kw.text for kw in keyword_stats]
    try:
        text_to_predict_ctr: dict[str, float | None] = (
            await get_text_to_predict_ctr_dict.get(adv_setting, texts)
        )
    except Exception as e:
        logger.error("Ошибка получения предикта", exc_info=True)
        raise e
    try:
        cpm_now = await get_cpm(adv_setting)
    except Exception as e:
        logger.error(f"Ошибка при получении cpm {e}", exc_info=True)
        cpm_now = None

    for keyword_stat in keyword_stats:
        text = keyword_stat.text
        keyword_setting = text_to_keyword_setting[text]
        added_clicks = keyword_setting.added_clicks
        keyword_stat.relevant = keyword_setting.relevant
        if not added_clicks:
            added_clicks = 0
        keyword_stat.added_clicks = added_clicks
        keyword_stat.keyword_setting_original_id = keyword_setting.id
        keyword_stat.adv_id = adv_setting.adv_id
        if not keyword_setting:
            continue
        original_hard_status: int = int(keyword_setting.hard_status)
        keyword_stat.hard_status = original_hard_status
        original_predict_ctr: float | None = text_to_predict_ctr.get(text, None)
        keyword_stat.original_predict_ctr = original_predict_ctr

    keyword_stats: list[CalculatedKeyword] = __set_predict_ctr(
        keyword_stats, min_ctr, adv_setting
    )

    best_keyword: CalculatedKeyword | None = get_best_keyword(keyword_stats)
    if best_keyword:
        best_keyword.best_keyword_status = True

    for keyword_stat in keyword_stats:
        clicks = keyword_stat.calculated_clicks
        assert clicks is not None
        views = keyword_stat.calculated_views
        assert views is not None
        enough_views = keyword_stat.enough_views
        assert enough_views is not None
        original_predict_ctr = keyword_stat.original_predict_ctr
        hard_status = int(keyword_stat.hard_status)
        keyword_setting = text_to_keyword_setting.get(keyword_stat.text)
        """TODO: Выпилить из кода reason max_position, т.е. больше функции отключения позиции, если база больше
         или равна целевой - нет. """
        if max_cpc:
            if cpm_now:
                cpc = (cpm_now / 1000) / keyword_stat.predict_ctr
            elif clicks > 0:
                cpc = views / clicks
            else:
                cpc = None
            if cpc and cpc > max_cpc:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = "max_cpc"
                if keyword_setting and keyword_setting.id:
                    if keyword_setting.id:
                        await redis_manager.set_auto_block_status(
                            int(keyword_setting.id), True # type: ignore
                        )
                continue
        if (
            not original_predict_ctr
            and enough_views / 2 > keyword_stat.views
            and not adv_setting.min_views_for_ml_predict
            and keyword_stat.hard_status in [1, 2]
        ):
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
            continue

        if hard_status == 3:
            keyword_stat.status = KeywordStatus.BAD
            keyword_stat.reason = "turn_off"
            continue
        if hard_status == 2:
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = "white_list"
            continue
        elif hard_status == 0:
            keyword_stat.status = KeywordStatus.BAD
            keyword_stat.reason = "black_list"
            continue
        if min_ctr == 0:
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = "min_ctr_is_zero"
            continue
        baes_predict_ctr = keyword_stat.baes_predict_ctr
        assert baes_predict_ctr is not None
        if baes_predict_ctr >= min_ctr:
            keyword_stat.status = KeywordStatus.GOOD
            keyword_stat.reason = "baes_ctr_more_than_min_ctr"
        else:
            assert keyword_stat.views is not None
            if keyword_stat.views < adv_setting.min_views_for_ml_predict:
                keyword_stat.status = KeywordStatus.GOOD
                keyword_stat.reason = KeywordStatus.VIEWS_IS_NOT_ENOUGH
            else:
                keyword_stat.status = KeywordStatus.BAD
                keyword_stat.reason = "min_ctr"
        assert keyword_stat.predict_ctr
    logger.debug("Проверяю статусы ключевых слов с assert")

    for keyword_stat in keyword_stats:
        try:
            assert keyword_stat.status
            assert keyword_stat.status in [
                KeywordStatus.GOOD,
                KeywordStatus.BAD,
                KeywordStatus.VIEWS_IS_NOT_ENOUGH,
                KeywordStatus.MAX_CPC,
            ]
        except Exception as e:
            raise e

    for keyword_stat in keyword_stats:
        for property_ in keyword_stat.__dict__:
            if property_ in [
                "position_update",
                "k",
                "k",
                "best_keyword_status",
                "childs_keywords",
                "cpm",
                "promo_position",
                "original_predict_ctr",
                "real_position",
                "base_position",
                "cluster_name",
                "preset",
                "position",
            ]:
                continue
            # TODO: Критичный код, не стал трогать, так то надо переделать, чтобы не было shadow  переменных  property
            value = getattr(keyword_stat, property_) # type: ignore
            try:
                assert value is not None
            except AssertionError:
                # TODO: Удалить из всего проекта f-строки из логирования
                logger.error(
                    f"Ошибка в значении {property_} для {keyword_stat.text}: {value}"
                )

    logger.debug("Слова по assert проверены")
    logger.debug("Возвращаю итоговую статистику")
    return keyword_stats


async def get_wb_category(adv_setting: AdvSetting) -> WBCategory | None:
    try:
        nmid = adv_setting.nmids[0]
    except Exception as e:
        raise NotItemsInAdvSetting("У кампании в базе нет товаров") from e
    async with _sm() as session:
        smtp = (
            select(WBCard)
            .where(WBCard.nmid == int(nmid))
            .options(selectinload(WBCard.wb_category))
        )
        result = await session.execute(smtp)
    wb_card: WBCard | None = result.scalar_one_or_none()
    if wb_card is not None:
        wb_category = wb_card.wb_category
    else:
        raise CardNotFoundInDB("В базе не найдена карточка товара: " + str(nmid))
    return wb_category


async def get_main_photos(nmids: list[int]) -> list[str]:
    async with _sm() as session:
        smtp = select(WBCard).where(WBCard.nmid.in_(nmids))
        result = await session.execute(smtp)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
    main_photos: list[str] = [wb_card.photos[0] for wb_card in wb_cards]
    return main_photos


async def __download_and_resize_image(
    url: str, session: Any, max_size: int = 1280
) -> bytes | None:
    while True:
        async with session.get(url) as response:
            if response.status != 200:
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


async def get_adv_keyword_text_in_black_list() -> list[tuple[int, str]]:
    async with _sm() as session:
        stmt = (
            select(KeywordSetting)
            .options(selectinload(KeywordSetting.adv_setting))
            .where(KeywordSetting.hard_status == 0)
        )
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
    adv_keyword_text_in_black_list: list[tuple[int, str]] = []
    for keyword_setting in keyword_settings:
        adv_setting = keyword_setting.adv_setting
        adv_keyword_text_in_black_list.append(
            (adv_setting.adv_id, keyword_setting.text)
        )

    return adv_keyword_text_in_black_list


async def get_all_shops_for_user(user: User) -> list[WBUserCabinet]:
    async with _sm() as session:
        stmt = select(WBUserCabinet).where(WBUserCabinet.user_id == user.id)
        result = await session.execute(stmt)
        wb_user_cabinets = result.scalar()
        if wb_user_cabinets:
            return list(wb_user_cabinets.all())
        else:
            return []


async def get_adv_id_to_min_ctr(adv_ids: list[int]) -> dict[int, float]:
    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(adv_ids))
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.unique().scalars())
    adv_id_to_min_ctr = {}

    for adv_setting in adv_settings:
        logger.debug("Получаю min_ctr")
        try:
            min_ctr = await get_min_ctr(adv_setting)
            logger.debug("min_ctr получен")
            adv_id_to_min_ctr[adv_setting.adv_id] = min_ctr
        except Exception as e:
            logger.error(f"Ошибка при получении min_ctr {e}", exc_info=True)
            adv_id_to_min_ctr[adv_setting.adv_id] = 0.03
    return adv_id_to_min_ctr


async def get_adv_id_keyword_text_to_status(
    adv_ids: list[int],
) -> dict[tuple[int, str], int]:
    async with _sm() as session:
        # Используем только необходимые колонки и убираем лишние алиасы
        stmt = (
            select(AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status)
            .join(KeywordSetting, AdvSetting.id == KeywordSetting.adv_setting_id)
            .where(AdvSetting.adv_id.in_(adv_ids))
        )

        # Выполняем запрос
        result = await session.execute(stmt)

        # Извлекаем данные в виде словаря сразу в процессе итерации по результату
        adv_id_keyword_text_to_status = {
            (row.adv_id, row.text): row.hard_status for row in result
        }

    return adv_id_keyword_text_to_status


@dataclass
class ReferralStatistic:
    name: str
    referrals_count: int
    total_payments: float


@dataclass
class ReferralLink:
    name: str
    link: str


async def get_mean_ctr(adv: AdvSetting) -> float:
    keywords: list[CalculatedKeyword] = await get_good_bad_phrases(adv)
    goods = [kw for kw in keywords if kw.status == "good"]
    good_texts: list[str] = [kw.text for kw in goods]
    async with _sm() as session:
        stmt = (
            select(
                case(
                    ( # noqa
                        func.sum(AdvKeyword.views) == 0,
                        0,
                    ),  # Условие, если показов нет, возвращаем 0
                    else_=cast(
                        func.sum(AdvKeyword.clicks) / func.sum(AdvKeyword.views), Float
                    ),  # Иначе вычисляем CTR
                ).label("average_ctr")
            )
        ).where(
            and_(AdvKeyword.adv_setting_id == adv.id, AdvKeyword.text.in_(good_texts))
        )
        result = await session.execute(stmt)
        mean_ctr = result.scalar_one()
        return mean_ctr  # Возвращаем значение mean_ctr вместо pass


async def get_min_ctr(adv: AdvSetting) -> float:
    ctr_manager = MinCtrManager(adv)
    min_ctr = await ctr_manager.get_min_ctr()
    return min_ctr


# TODO: Улучшить автоуправление РК
# TODO: Сделать более точным прогноз продаж и себеса

def get_best_keyword(keywords: list[CalculatedKeyword]) -> CalculatedKeyword | None:
    # TODO: Функция упала бы на Smoke-тесте при пустом списке ключевых слов и упала на полной фильтрации
    if not keywords:
        return None
    keywords = [kw for kw in keywords if kw.position is not None and kw.position >= 0]
    if not keywords:
        return None
    best_keyword = sorted(
        keywords, key=lambda x: x.rating_by_predict_ctr, reverse=True
    )[0]

    return best_keyword


async def clear_cards(need_nmids: list[int]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(need_nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
        await session.delete(wb_cards)
        await session.commit()


async def clear_keywords(need_keywords: list[str]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(KeywordSetting).where(KeywordSetting.text.notin_(need_keywords))
        result = await session.execute(stmt)
        keyword_settings: list[KeywordSetting] = list(result.unique().scalars().all())
        await session.delete(keyword_settings)
        await session.commit()


async def get_expired_cabinets(session: AsyncSession) -> list[WBCabinet]:
    delete_expired_time = datetime.now() - timedelta(days=30)
    stmt = (
        select(WBCabinet)
        .options(selectinload(WBCabinet.adv_settings))
        .where(WBCabinet.expiration_time < delete_expired_time)
    )
    result = await session.execute(stmt)
    wb_cabinets: list[WBCabinet] = list(result.unique().scalars().all())
    return wb_cabinets


async def clear_cards_in_db(nmids: list[int]) -> None:
    async with _sm(read_only=False) as session:
        stmt = select(WBCard).where(WBCard.nmid.notin_(nmids))
        result = await session.execute(stmt)
        wb_cards: list[WBCard] = list(result.unique().scalars().all())
        for card in wb_cards:
            await session.delete(card)
            await session.commit()


async def get_sum_bot_balance_from_wb_wb_user_cabinet_original_id(
    shop_id: str,
) -> float | None:
    stmt = select(
        func.sum(coalesce(WBCabinet.balance, 0) + coalesce(WBCabinet.bonus, 0))
    ).where(WBCabinet.shop_id == shop_id)
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_keywords_positions_dict_by_text(
    adv_setting: AdvSetting, texts: list[str]
) -> dict[str, WBItemPosition]:
    # Type ignore for untyped redis_manager call
    positions = await redis_manager.get_keywords_positions(adv_setting, texts)  # type: ignore[no-untyped-call]
    positions = [position for position in positions if position]
    positions = {position.keyword_text: position for position in positions}
    return positions


async def add_white_phrases(keywords: list[str], adv_setting_id: int) -> None:
    async with _sm(read_only=False) as session:
        for text in keywords:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    and_(KeywordSetting.text == text, AdvSetting.id == adv_setting_id)
                )
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            if not keyword_setting:
                adv_keyword = AdvKeyword(
                    text=text,
                    adv_setting_id=adv_setting_id,
                    views=0,
                    clicks=0,
                    spend=0,
                    date=datetime.now().date(), # noqa
                )

                keyword_setting = KeywordSetting(
                    text=text,
                    adv_setting_id=adv_setting_id,
                )
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            keyword_setting.hard_status = 2
        await session.commit()


async def update_black_phrases(adv_setting_id: int, keywords: list[str]) -> None:
    await redis_manager.set_black_phrases(adv_setting_id, keywords)  # type: ignore[attr-defined]
    async with _sm(read_only=False) as session:
        stmt = (
            select(KeywordSetting)
            .join(KeywordSetting.adv_setting)
            .where(
                AdvSetting.id == int(adv_setting_id), KeywordSetting.hard_status != 0
            )
        )
        result = await session.execute(stmt)
        keyword_settings = result.scalars().all()
        for keyword_setting in keyword_settings:
            for black_phrase in keywords:
                black_phrase_text = black_phrase.lower().strip()
                if "'" in black_phrase_text or '"' in black_phrase_text:
                    black_phrase_text = black_phrase_text.replace("'", "''").replace(
                        '"', '""'
                    )
                    if black_phrase_text == keyword_setting.text:
                        keyword_setting.hard_status = 0
                        break
                else:
                    if black_phrase_text in keyword_setting.text:
                        keyword_setting.hard_status = 0
                        break

        await session.commit()


async def check_by_black_list_template(keyword_text: str, adv_setting_id: int) -> bool:
    black_keywords = await redis_manager.get_black_phrases(adv_setting_id)  # type: ignore[attr-defined]
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


async def reset_black_phrases(adv_setting_id: int) -> None:
    await redis_manager.set_black_phrases(adv_setting_id, [])  # type: ignore[attr-defined]


async def add_relevant_phrases(keywords: list[str], adv_setting_id: int) -> None:
    async with _sm(read_only=False) as session:
        for text in keywords:
            stmt = (
                select(KeywordSetting)
                .join(KeywordSetting.adv_setting)
                .where(
                    and_(KeywordSetting.text == text, AdvSetting.id == adv_setting_id)
                )
            )
            result = await session.execute(stmt)
            keyword_setting = result.scalar()
            if keyword_setting:
                keyword_setting.relevant = True
            else:
                adv_keyword = AdvKeyword(
                    text=text,
                    adv_setting_id=adv_setting_id,
                    views=0,
                    clicks=0,
                    spend=0,
                    date=datetime.now().date(), # noqa
                )

                keyword_setting = KeywordSetting(
                    text=text,
                    adv_setting_id=adv_setting_id,
                )
                keyword_setting.relevant = True
                keyword_setting.adv_keywords.append(adv_keyword)
                session.add(keyword_setting)
            if keyword_setting.hard_status == 0:
                keyword_setting.hard_status = 1
        await session.commit()


async def get_active_search_advs() -> list[AdvSetting]:
    pattern = r"<!-\[(\d+)\]-!>"
    stmt = select(AdvSetting).where(
        # Проверяем, что name содержит паттерн <!-[цифры]-!>
        AdvSetting.name.op("~")(pattern),
        AdvSetting.bot_active.is_(True),
        AdvSetting.active_status == "started",
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings = result.scalars().all()
    return list(adv_settings)


async def get_all_active_shop_ids_with_active_advs() -> list[str]:
    stmt = (
        select(WBCabinet.shop_id)
        .join(WBCabinet.adv_settings)
        .where(AdvSetting.bot_active)
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return list(shop_ids)


async def get_all_shop_ids() -> list[str]:
    stmt = select(WBCabinet.shop_id).distinct()
    async with _sm() as session:
        result = await session.execute(stmt)
        shop_ids = result.scalars().all()
    return list(shop_ids)


async def get_active_adv_ids_for_shop(shop_id: str) -> Sequence[int]:
    stmt = (
        select(AdvSetting)
        .distinct()
        .join(AdvSetting.wb_cabinet)
        .where(WBCabinet.shop_id == shop_id, AdvSetting.bot_active.is_(True))
        .options(
            load_only(AdvSetting.adv_id, AdvSetting.name, AdvSetting._search_adv_id) # noqa
        )
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        adv_settings: list[AdvSetting] = list(result.scalars().all())
    adv_ids = []
    for adv in adv_settings:
        adv_ids.append(adv.adv_id)
        if search_adv_id := adv.search_adv_id:
            adv_ids.append(search_adv_id)

    return adv_ids


async def get_keywords_statistic(adv_setting: AdvSetting) -> list[CalculatedKeyword]:
    keywords = await get_keywords_statistic_clickhouse(adv_setting, last_views=3000)
    return keywords


async def get_max_adv_bid(adv_setting: AdvSetting) -> int | float:
    setting_max_bid = adv_setting.max_cpm
    max_pay_for_order = adv_setting.max_pay_for_order
    if not max_pay_for_order:
        return setting_max_bid
    if adv_setting.auto_max_bid:
        keywords: list[CalculatedKeyword] = await get_keywords_statistic(adv_setting)
        full_keyword_stat = await get_full_adv_stat_for_adv_id_from_redis(
            adv_setting.adv_id
        )
        if not full_keyword_stat:
            return setting_max_bid
        views = float(full_keyword_stat.views + 1)
        orders = float(full_keyword_stat.orders + 1)
        best_keyword: CalculatedKeyword | None = get_best_keyword(keywords)
        if not best_keyword:
            return setting_max_bid
        convert_views_to_order = views / orders
        ctr: float | None = best_keyword.predict_ctr
        if ctr is None:
            raise ValueError("predict_ctr cannot be None for max_adv_bid calculation")
        assert ctr is not None  # Утверждение, что ctr теперь не None
        max_bid_for_1000_views = (
            (max_pay_for_order / convert_views_to_order) * ctr * 1000
        )
        if setting_max_bid < max_bid_for_1000_views:
            setting_max_bid = max_bid_for_1000_views
    return setting_max_bid


async def is_adv_in_favorites(
    adv_setting_original_id: int, user_original_id: int
) -> bool:
    stmt = select(favorite_advs_association).where(
        and_(
            favorite_advs_association.c.user_id == user_original_id,
            favorite_advs_association.c.adv_id == adv_setting_original_id,
        )
    )
    async with _sm() as session:
        result = await session.execute(stmt)
        return result.first() is not None


def __calculate_version(position: WBItemPosition) -> int:
    if position.timestamp is None:
        return int(datetime.now().timestamp())
    return int(position.timestamp.timestamp())


async def get_avg_base_positions(
    nmid: int, start_date: str, end_date: str
) -> list[WBItemPosition]:
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

    parameters = {"nmid": nmid, "start_date": start_date, "end_date": end_date}

    async with get_clickhouse_client() as client:
        result = await client.query(query, parameters=parameters)
        result = result.result_rows
        return [
            WBItemPosition(nmid=nmid, position=row[1], timestamp=row[0])
            for row in result  # type: ignore[attr-defined]
        ]


async def add_positions_to_clickhouse(positions: list[WBItemPosition]) -> None:
    async with get_clickhouse_client() as client:
        for position in positions:
            try:
                # Генерация версии и подготовка timestamp
                version = __calculate_version(position)
                timestamp_str = position.timestamp.strftime("%Y-%m-%d %H:%M:%S")

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
                    {position.position if position.position else 0},
                    {position.position if position.position else 0},
                    {0},
                    {int(position.adv_type) if position.adv_type else 0},
                    '{timestamp_str}',
                    {version}
                )
                """
                await client.query(query_insert)
                logger.debug(f"Добавлена запись для nmid={position.nmid}")

            except Exception as e:
                logger.error(
                    f"Ошибка при обработке позиции nmid={position.nmid}: {e}",
                    exc_info=True,
                )


async def get_keyword_positions_from_click_house(nmid: int) -> list[WBItemPosition]:
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
        avg_promo = row[2] if row[2] else 0
        avg_base = row[3] if row[3] else 0
        position.position = int(avg_base or avg_promo or 6000)
        position.timestamp = datetime.combine(row[1], datetime.min.time())
        positions.append(position)

    return positions


async def set_last_full_stat_update(adv_id: int, timestamp: datetime) -> None:
    await redis_manager.set_last_full_stat_update(adv_id, timestamp)


async def get_last_full_stat_update(adv_id: int) -> datetime | None:
    return await redis_manager.get_last_full_stat_update(adv_id)


async def get_all_keywords_from_ch(last_days: int = 7) -> set[str]:
    ch_query = """
    SELECT DISTINCT text FROM default_db.advkeyword_new 
    WHERE date >= today() - %(last_days)s
    """

    async with get_clickhouse_client() as client:
        result = await client.query(ch_query, parameters={"last_days": last_days})
        keywords = result.result_rows
    return set([keyword[0] for keyword in keywords if keyword])


async def get_cpm(auto_adv: AdvSetting) -> float | None:
    # CPM из парсинга больше недоступен, используем только настройки кампаний
    # Проверяем, есть ли CPM из аукциона
    auction_adv_id: int | None = auto_adv.search_adv_id
    cpm_from_auction = None
    if auction_adv_id:
        stmt = (
            select(AdvSetting)
            .options(load_only(AdvSetting.cpm))
            .where(AdvSetting.adv_id == auction_adv_id)
        )
        async with _sm() as session:
            result = await session.execute(stmt)
            auction_adv: AdvSetting | None = result.scalar_one_or_none()
            if auction_adv:
                cpm_from_auction = auction_adv.cpm

    # CPM из настроек рекламного объявления
    cpm_from_auto = auto_adv.cpm
    cpm_values = [cpm for cpm in [cpm_from_auction, cpm_from_auto] if cpm is not None]

    if not cpm_values:
        return None

    return max(cpm_values)


async def update_advs_data_from_wb_to_pg(wb_api):
    shop_data_updater = ShopDataUpdater(wb_api)
    await shop_data_updater.update_advs_data()
