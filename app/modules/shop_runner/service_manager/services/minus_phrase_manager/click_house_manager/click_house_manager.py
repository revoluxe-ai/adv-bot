from app.core.clikhouse_client_manager import get_clickhouse_client
from app.core.clickhouse_manager import BaseClickHouseManager
import logging

logger = logging.getLogger(__name__)

class ClickHouseManager(BaseClickHouseManager):

    async def get_cluster_texts_for_adv(self, adv_id: int) -> list[str]:
        # TODO: Тут попала ошибка в RUNTIME
        query = self._get_query('get_cluster_texts')
        try:
            async with get_clickhouse_client() as client:
                response = await client.query(query, parameters={'adv_id': adv_id})
            texts_rows = response.result_rows
        except Exception as e:
            logger.error('Ошибка получения ключей из статистики кластера: %s', e, exc_info=True)
            raise e
        texts = [text[0] for text in texts_rows]
        return texts


