from collections.abc import Mapping

from sqlalchemy import select, Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.predict_keywords_target_place import PredictKeywordsTargetPlace
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


class KeywordTargetPlaceUpdater:
    def __init__(self, predict_keyword_target_place: PredictKeywordsTargetPlace):
        self._predict_keyword_target_place = predict_keyword_target_place

    async def update_individual_keyword_target_places(self, adv: WBAdvDTO):
        if adv.complex_adv.bot_active:
            logger.debug(
                "V3 target_place handled in process_adv_v3, adv_id=%s",
                adv.adv_id,
            )
            return None

        target_places = (
            await self._predict_keyword_target_place.get_keywords_target_position(
                adv=adv,
                positions_size=adv.min_target_position,
            )
        )
        await self._set_new_target_places(adv, target_places)
        return None

    @staticmethod
    async def _set_new_target_places(
        adv: WBAdvDTO, target_places: Mapping[str, int | None]
    ) -> None:
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv.adv_setting_original_id
        )
        async with sm(read_only=False) as session:
            result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
            keywords = result.scalars().all()
            for keyword in keywords:
                text = keyword.text
                resolved = target_places.get(text.lower())
                if resolved is None:
                    logger.warning(
                        "No target place data for keyword %s, adv_id=%s; leaving target_place unset",
                        text,
                        adv.adv_id,
                    )
                    keyword.target_place = None
                elif resolved <= 0:
                    logger.error(
                        "Invalid target place %s for keyword %s, adv_id=%s; clearing target_place",
                        resolved,
                        text,
                        adv.adv_id,
                    )
                    keyword.target_place = None
                else:
                    keyword.target_place = resolved
            await session.commit()

        return None
