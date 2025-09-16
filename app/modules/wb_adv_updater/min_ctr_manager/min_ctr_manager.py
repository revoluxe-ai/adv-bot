import logging

from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.settings import settings
from app.utils import redis_manager
from app.utils.click_house.client import get_clickhouse_client
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

class MinCtrManager:

    def __init__(self, adv: AdvSetting):
        self._adv = adv
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
            texts = result.all()

        texts = [text[0] for text in texts if text[0]]

        if texts:
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
            WITH
                latest_versions AS (
                    SELECT
                        text,
                        date,
                        MAX(version) AS latest_version
                    FROM
                        default_db.advkeyword
                    WHERE
                        adv_id IN %(adv_ids)s
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
                        a.adv_id IN %(adv_ids)s
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

            try:
                async with get_clickhouse_client() as client:
                    result_from_click_house = await client.query(query, params)
                    rows = result_from_click_house.result_rows
            except Exception:
                logger.error("Ошибка получения статистики из ch", exc_info=True)
                raise

            text_to_real_ctr = {row[0]: row[1] for row in rows}
            real_ctrs = []
            predict_ctrs = []
            for text in texts:
                real_ctr = text_to_real_ctr.get(text)
                if real_ctr:
                    real_ctrs.append(text_to_real_ctr[text])
                predict_ctr = await redis_manager.get_predict_ctr(auto_adv_id, text)
                if predict_ctr:
                    predict_ctrs.append(predict_ctr)
            if predict_ctrs:
                return float(min(predict_ctrs))
            if real_ctrs:
                return float(min(real_ctrs))
            return settings.DEFAULT_MIN_CTR


