import logging
from datetime import date
from typing import Sequence
from typing import TYPE_CHECKING

from app.utils.ch_semaphore import anti_ch_crash_semaphore

if TYPE_CHECKING:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO

from app.modules.shop_runner.service_manager.services.clusters_adv_stat_updater.convertor import \
    norn_query_dto_to_raw_stat_dto
from app.modules.shop_runner.service_manager.services.clusters_adv_stat_updater.row_stat_dto import RowStatDTO
from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)


async def get_existing_adv_nmid_dates(
    adv_nmid_pairs: list[tuple[int, int]],
    start_date: date,
    end_date: date
) -> set[tuple[int, int, date]]:
    """
    Возвращает множество (adv_id, nmid, date) для которых уже есть данные в ClickHouse.

    Args:
        adv_nmid_pairs: Список пар (adv_id, nmid) для проверки
        start_date: Начальная дата диапазона
        end_date: Конечная дата диапазона

    Returns:
        Множество кортежей (adv_id, nmid, date) с существующими данными
    """
    if not adv_nmid_pairs:
        return set()

    # ClickHouse не поддерживает параметризацию для IN с кортежами,
    # поэтому формируем запрос с подстановкой
    pairs_str = ", ".join(
        "(%d, %d)" % (adv_id, nmid) for adv_id, nmid in adv_nmid_pairs
    )

    query = """
        SELECT DISTINCT adv_id, nmid, date
        FROM default_db.clusters_adv_stats
        WHERE (adv_id, nmid) IN (%s)
          AND date BETWEEN toDate('%s') AND toDate('%s')
    """ % (pairs_str, start_date.isoformat(), end_date.isoformat())

    try:
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result = await client.query(query)
                rows = result.result_rows

                existing: set[tuple[int, int, date]] = set()
                for row in rows:
                    adv_id = int(row[0])
                    nmid = int(row[1])
                    row_date = row[2]
                    if isinstance(row_date, date):
                        existing.add((adv_id, nmid, row_date))
                    else:
                        # Если вернулась строка, парсим
                        from datetime import datetime
                        parsed_date = datetime.strptime(str(row_date), "%Y-%m-%d").date()
                        existing.add((adv_id, nmid, parsed_date))

            return existing
    except Exception:
        logger.error("Ошибка получения существующих дат из ClickHouse", exc_info=True)
        return set()


async def _insert_stats_to_clickhouse(stats: Sequence[RowStatDTO]) -> None:
    if not stats:
        return

    column_names = [
        'adv_id', 'nmid', 'wb_category', 'norm_query', 'views', 'clicks', 'ctr',
        'cpm', 'add_to_cart', 'orders', 'cpc', 'avr_pos', 'date'
    ]

    # clickhouse_connect ожидает список списков/кортежей при использовании column_names
    data = [
        [
            row.adv_id,
            row.nmid,
            row.wb_category,
            row.norm_query,
            row.views,
            row.clicks,
            row.ctr,
            row.cpm if row.cpm is not None else 0.0,
            row.add_to_cart if row.add_to_cart is not None else 0,
            row.orders,
            row.cpc if row.cpc is not None else 0.0,
            row.avr_pos if row.avr_pos is not None else 0.0,
            row.date,
        ]
        for row in stats
    ]

    async with get_clickhouse_client() as client:
        await client.insert('default_db.clusters_adv_stats', data, column_names=column_names)


async def update_clusters_adv_stats(stats: Sequence["NormqueryStatsDTO"]) -> None:
    # TODO: Добавить реальные ставка по ключам Авто и Поиск
    row_dtos = await norn_query_dto_to_raw_stat_dto(stats)
    await _insert_stats_to_clickhouse(row_dtos)




