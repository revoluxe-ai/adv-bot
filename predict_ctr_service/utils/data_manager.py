from datetime import timedelta, datetime
from collections import defaultdict

from .clickhouse_client import get_clickhouse_client
from ..dto.adv_setting import AdvSetting
from shared_lib.models.calculated_keyword import CalculatedKeyword
from ..dto.keyword_setting import KeywordSetting
from .session_maker import get_async_session_maker as _sm
from .min_ctr import get_min_ctr
from sqlalchemy import select
from . import redis_manager

import logging


logger = logging.getLogger(__name__)

async def get_keywords_statistic_clickhouse(
    adv_setting: AdvSetting,
    pass_time: timedelta | None = timedelta(days=7),
    last_views=None,
) -> list[CalculatedKeyword]:
    """
    Получение статистики ключевых слов из ClickHouse (реализация из легаси).
    """

    import predict_ctr_service.utils.redis_manager as redis_manager
    async with get_clickhouse_client() as ch_client:
        advs: set[int] = set()
        auto_adv_id = int(adv_setting.adv_id)
        advs.add(auto_adv_id)
        search_adv_id = adv_setting.adv_id
        if search_adv_id:
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
    keywords = await redis_manager.set_predict_ctrs(adv_setting.adv_id, keywords)
    return keywords

async def convert_keyword_stats_in_clusters(
    keyword_stats: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    preset_to_keywords = defaultdict(list)
    preset_to_cluster_name = {}
    texts = [keyword.text for keyword in keyword_stats]
    try:
        text_to_custer_and_present = await redis_manager.get_clusters_and_presets(texts)
    except Exception:
        logger.error(f"Ошибка получения кластеров и пресетов: {texts}", exc_info=True)
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
    # __calculate_clusters должен быть реализован или импортирован
    keyword_stats =  redis_manager.__calculate_clusters(preset_to_keywords, preset_to_cluster_name)
    return keyword_stats

async def get_adv_id_to_min_ctr(adv_ids: list[int]) -> dict[int, float]:
    async with _sm() as session:
        stmt = AdvSetting.__table__.select().where(AdvSetting.adv_id.in_(adv_ids))
        result = await session.execute(stmt)
        adv_settings = result.fetchall()
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

async def get_adv_id_keyword_text_to_status(adv_ids: list[int]) -> dict[tuple[int, str], int]:
    async with _sm() as session:
        # Используем только необходимые колонки и убираем лишние алиасы
        stmt = (
            select(AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status)

            .where(AdvSetting.adv_id.in_(adv_ids))
        )
        result = await session.execute(stmt)
        adv_id_keyword_text_to_status = {
            (row.adv_id, row.text): row.hard_status for row in result
        }
    return adv_id_keyword_text_to_status

def _build_clickhouse_query(
    adv_ids: set[int],
    pass_time: timedelta | None,
    last_views: int | None = None,
) -> str:
    adv_ids_str = ", ".join(str(aid) for aid in adv_ids)

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
                adv_id IN ({adv_ids_str})
                AND (text, date, version) IN (
                    SELECT
                        text, date, MAX(version) AS version
                    FROM
                        default_db.advkeyword
                    WHERE
                        adv_id IN ({adv_ids_str})
                    GROUP BY
                        text, date
                )
    """
    if pass_time:
        start_time = datetime.now() - pass_time
        query += f" AND date >= '{start_time.strftime('%Y-%m-%d')}'"
    query += """
            GROUP BY
                text, date
        ) AS latest_records
        GROUP BY text, date
    """
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
