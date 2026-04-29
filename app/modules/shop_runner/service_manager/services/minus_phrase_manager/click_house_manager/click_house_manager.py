from collections import defaultdict

from app.core.clikhouse_client_manager import get_clickhouse_client
from app.core.clickhouse_manager import BaseClickHouseManager
import logging

from app.utils.ch_semaphore import anti_ch_crash_semaphore

logger = logging.getLogger(__name__)

class ClickHouseManager(BaseClickHouseManager):

    async def get_cluster_texts_for_adv_ids(self, adv_ids: list[int]) -> dict[int, set[str]]:
        """Один round-trip в ClickHouse по всем adv_id (get_cluster_texts_many).

        Без anti_ch_crash_semaphore: read-only, один запрос: иначе этот путь стоит
        в общей очереди Semaphore(1) со всеми прочими CH-операциями и сильно
        задерживается. Риск: несколько корутин могут одновременно выполнять этот
        запрос — нагрузка на ClickHouse выше, следить за соединениями/сервером.
        """
        if not adv_ids:
            return {}
        query = self._get_query("get_cluster_texts_many")
        try:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query, parameters={"adv_ids": adv_ids}
                )
            rows = response.result_rows
        except Exception as e:
            logger.error(
                "Ошибка получения ключей из статистики кластера (batch): %s",
                e,
                exc_info=True,
            )
            raise e
        by_adv: dict[int, set[str]] = defaultdict(set)
        for adv_id, norm_query in rows:
            by_adv[int(adv_id)].add(norm_query)
        return dict(by_adv)

    async def get_cluster_texts_for_adv_nmid(self, adv_id: int, nmid: int) -> list[str]:
        # TODO: Тут попала ошибка в RUNTIME
        query = self._get_query('get_cluster_texts')
        try:
            async with anti_ch_crash_semaphore:
                async with get_clickhouse_client() as client:
                    response = await client.query(
                        query, parameters={"adv_id": adv_id, "nmid": nmid}
                    )
                texts_rows = response.result_rows
        except Exception as e:
            logger.error('Ошибка получения ключей из статистики кластера: %s', e, exc_info=True)
            raise e
        texts = [text[0] for text in texts_rows]
        return texts


