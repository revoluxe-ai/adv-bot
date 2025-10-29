import logging

from dependency_injector.wiring import inject, Provide
from sqlalchemy import select
import typing

from app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.di import PredictCTRManagerContainer

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.predict_ctr_update_manager.redis_manager import \
        PredictCTRRedisManager

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.settings import settings
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


class MinCtrManager:
    @inject
    def __init__(self, adv: AdvSetting, redis_manager: 'PredictCTRRedisManager' = Provide[
        PredictCTRManagerContainer.redis_manager
    ]):
        self._adv = adv
        self._redis_manager = redis_manager

    async def get_min_ctr(self) -> float:
        adv = self._adv
        if not adv.new_auto_min_ctr_mode:
            hard_min_ctr = adv.hard_min_ctr
            if not hard_min_ctr:
                return settings.DEFAULT_MIN_CTR
            else:
                return float(adv.hard_min_ctr)
        min_ctr = await self._get_min_ctr()
        if not min_ctr:
            min_ctr = settings.DEFAULT_MIN_CTR
        return min_ctr

    async def _get_min_ctr(self) -> float:
        adv = self._adv
        async with sm(read_only=True) as session:
            stmt = select(KeywordSetting.text).where(
                KeywordSetting.hard_status == 2,
                KeywordSetting.adv_setting_id == adv.id,
            )
            result = await session.execute(stmt)
            texts_row = result.all()

        texts = [str(text[0]) for text in texts_row if text[0]]

        if not texts:
            return settings.DEFAULT_MIN_CTR
        adv_ids: set[int] = set()
        auto_adv_id = adv.adv_id
        adv_ids.add(auto_adv_id)
        if search_adv_id := adv.search_adv_id:
            adv_ids.add(search_adv_id)

        adv_ids_tuple = tuple(adv_ids)  # (27081773, 27081775)
        params = {
            "adv_ids": adv_ids_tuple,
            "texts": tuple(texts),
        }
        query = """
            WITH stats AS (
                SELECT
                    text,
                    argMaxMerge(clicks_state) AS clicks,
                    argMaxMerge(views_state) AS views
                FROM default_db.advkeyword_new
                    WHERE adv_id IN %(adv_ids)s
                        GROUP BY adv_id, text, date    
            ),
         total_stats AS ( 
         SELECT
            text,
            SUM(clicks) AS total_clicks,
            SUM(views) AS total_views
                FROM stats
                    GROUP BY text
        )
        SELECT
            text,
            total_clicks / CASE
                WHEN total_views = 0 THEN 1
                ELSE total_views
            END AS ctr,
            total_views AS views
        FROM
            total_stats
        WHERE
            total_clicks > 0
        """

        try:
            async with get_clickhouse_client() as client:
                result_from_click_house = await client.query(query, params)
                rows = result_from_click_house.result_rows
        except Exception:
            logger.error("Ошибка получения статистики из ch", exc_info=True)
            raise

        text_to_real_ctr = {str(row[0]): row[1] for row in rows}
        text_to_predict_ctr = {}
        for text in texts:
            predict_ctr = await self._redis_manager.get_predict_ctr(self._adv, text)
            text_to_predict_ctr[text] = predict_ctr

        ctrs = set()
        for text in texts:
            ctr: float | None = text_to_predict_ctr.get(text, text_to_real_ctr.get(text))
            if ctr:
                ctrs.add(ctr)
        if ctrs:
            min_ctr = min(ctrs)
            return min_ctr
        else:
            return settings.DEFAULT_MIN_CTR
