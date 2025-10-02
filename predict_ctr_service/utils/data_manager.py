import logging
from datetime import timedelta
from collections import defaultdict
from typing import cast

from ..dto.adv_setting import AdvSetting
from ..dto.calculated_keyword import CalculatedKeyword
from ..dto.keyword_setting import KeywordSetting
from .session_maker import get_async_session_maker as _sm
from .min_ctr import get_min_ctr

from .redis_manager import get_clickhouse_client, set_predict_ctrs, get_clusters_and_presets, __calculate_clusters, _build_clickhouse_query

__all__ = ["get_clickhouse_client", "set_predict_ctrs", "get_clusters_and_presets", "__calculate_clusters", "_build_clickhouse_query", "get_keywords_statistic_clickhouse", "convert_keyword_stats_in_clusters", "get_adv_id_to_min_ctr", "get_adv_id_keyword_text_to_status"]

logger = logging.getLogger(__name__)

async def get_keywords_statistic_clickhouse(
    adv_setting: AdvSetting,
    pass_time: timedelta | None = timedelta(days=7),
    last_views: int | None = None,
) -> list[CalculatedKeyword]:
    async with get_clickhouse_client() as ch_client:
        advs: set[int] = set()
        auto_adv_id = int(adv_setting.adv_id)
        advs.add(auto_adv_id)
        if getattr(adv_setting, 'search_adv_id', None):
            advs.add(adv_setting.search_adv_id)
        query = _build_clickhouse_query(advs, pass_time, last_views)
        result = await ch_client.query(query)
        rows = result.result_rows
        keywords = []
        for row in rows:
            text = cast(str, row[0]) if row[0] is not None else ""
            clicks = row[1]
            views = row[2]
            spend = row[3]
            if clicks > views:
                views = clicks
            keyword = CalculatedKeyword(
                text=text, clicks=clicks, views=views, spend=spend
            )
            keywords.append(keyword)
    keywords = await set_predict_ctrs(adv_setting.adv_id, keywords)
    return keywords

async def convert_keyword_stats_in_clusters(
    keyword_stats: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    preset_to_keywords = defaultdict(list)
    preset_to_cluster_name = {}
    texts = [keyword.text for keyword in keyword_stats]
    try:
        text_to_custer_and_present = await get_clusters_and_presets(texts)
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
    keyword_stats = __calculate_clusters(preset_to_keywords, preset_to_cluster_name)
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
        stmt = (
            AdvSetting.__table__.join(KeywordSetting.__table__, AdvSetting.id == KeywordSetting.adv_setting_id)
            .select()
            .with_only_columns([AdvSetting.adv_id, KeywordSetting.text, KeywordSetting.hard_status])
            .where(AdvSetting.adv_id.in_(adv_ids))
        )
        result = await session.execute(stmt)
        adv_id_keyword_text_to_status = {
            (row.adv_id, row.text): row.hard_status for row in result.fetchall()
        }
    return adv_id_keyword_text_to_status
