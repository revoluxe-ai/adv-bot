from sqlalchemy import select, Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.predict_keywords_target_place import PredictKeywordsTargetPlace
from app.settings import settings
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


class KeywordTargetPlaceUpdater:

    def __init__(self, predict_keyword_target_place: PredictKeywordsTargetPlace):
        self._predict_keyword_target_place = predict_keyword_target_place


    async def update_individual_keyword_target_places(self, adv: WBAdvDTO):
        target_places: dict[str, int] = await self._predict_keyword_target_place.get_keywords_target_position(
        adv=adv,
        positions_size=adv.min_target_position)
        await self._set_new_target_places(adv, target_places)
        return None

    @staticmethod
    async def _set_new_target_places(adv: WBAdvDTO, target_places: dict[str, int | None]) -> None:
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv.adv_setting_original_id)
        async with sm(read_only=False) as session:
            result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
            keywords = result.scalars().all()
            for keyword in keywords:
                text = keyword.text
                target_place = target_places.get(text.lower())
                if target_place is None:
                    # TODO: Продумать уведомление об ошибке (срочно настроить сбор логов)
                    logger.error("No target place found for %s , adv_id: %s Set Default place = 2" ,
                                 text, adv.adv_id)
                    target_place = settings.GLOBAL_DEFAULT_KEYWORD_TARGET_PLACE  # 2 - по опыту чаще всего наиболее рентабельное место
                keyword.target_place = target_place
            await session.commit()

        return None



