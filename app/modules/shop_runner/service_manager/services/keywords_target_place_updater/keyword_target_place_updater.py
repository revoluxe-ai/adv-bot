from collections.abc import Mapping

from sqlalchemy import select, Result

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.predict_keywords_target_place import PredictKeywordsTargetPlace
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

logger = logging.getLogger(__name__)


class KeywordTargetPlaceUpdater:
    def __init__(self, predict_keyword_target_place: PredictKeywordsTargetPlace):
        self._predict_keyword_target_place = predict_keyword_target_place

    async def update_individual_keyword_target_places(self, adv: WBAdvDTO):
        ver = (
            adv.complex_adv.auto_updater_version
            if adv.complex_adv.auto_updater_version is not None
            else 2
        )
        if ver == 3:
            bid_profiles = (
                await self._predict_keyword_target_place.get_keyword_bid_profiles(
                    adv=adv,
                    positions_size=adv.min_target_position,
                )
            )
            await self._set_new_target_places_v3(adv, bid_profiles)
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
                    logger.error(
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

    async def _set_new_target_places_v3(
        self,
        adv: WBAdvDTO,
        bid_profiles: dict[str, list[BidPosition]],
    ) -> None:
        """Пересчёт target_place по профилю для каждого кроме OFF.

        Для OFF не трогаем сохранённый target_place: при переходе в OFF торги
        отрезаются в ``UpdateClusterBidsManager`` (исключение из map_datas), поэтому
        устаревшее значение не ведёт к активным ставкам.
        """
        stmt = select(KeywordSetting).where(
            KeywordSetting.adv_setting_id == adv.adv_setting_original_id
        )
        async with sm(read_only=False) as session:
            result: Result[tuple[KeywordSetting]] = await session.execute(stmt)
            keywords = result.scalars().all()
            for keyword in keywords:
                if keyword.strategy_mode == KeywordStrategyMode.OFF:
                    logger.debug(
                        "Skip target_place update for OFF keyword=%s adv_id=%s",
                        keyword.text,
                        adv.adv_id,
                    )
                    continue
                profile = bid_profiles.get(keyword.text.lower())
                if not profile:
                    logger.error(
                        "No bid profile for keyword %s, adv_id=%s; clearing target_place",
                        keyword.text,
                        adv.adv_id,
                    )
                    keyword.target_place = None
                    continue
                keyword.target_place = self._predict_keyword_target_place.get_target_position_for_strategy_mode(
                    profile,
                    keyword.strategy_mode,
                )
            await session.commit()
