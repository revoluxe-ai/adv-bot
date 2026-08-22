from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO
from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.relevant_phrase_manager import RelevantPhraseManager
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    strategy_mode_for_hard_status_write_v3,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus, KeywordStatusReason
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import KeywordStat
from app.utils.db.session_maker import get_async_session_maker as sm



class KeywordsManager:
    @staticmethod
    async def get_candidates_to_white_list(complex_adv: ComplexAdv):
        """Кандидаты в белый список (авто ``hard_status=1``, не GOOD, …).

        Почему при полках и органике разная логика: ``auto_updater_traffic_policy``.

        Сравнение кликов на стратегию MIN_CPO/MAX_CONV — в ``AdvStrategySelector``, не здесь.
        """
        # TODO: Централизовать отбор кандидатов в БС
        def candidate_filter(keyword: CalculatedKeyword) -> bool | None:
            if keyword.reason == KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID:
                return False
            if keyword.hard_status != 1:
                return False
            if keyword.status == KeywordStatus.GOOD:
                return False
            if complex_adv.auto_add_only_relevant_phrase and not keyword.relevant:
                return False
            if (complex_adv.rec_system_promotion_mode_active
                    and keyword.above_rec_conversion is False
                    and complex_adv.auto_adv_active_status
                    and complex_adv.is_shelf_activation_allowed):
                return False
            return True

        keywords = sorted(
            await complex_adv.get_keywords(),
            key=lambda kw: kw.rating or 0,
            reverse=True,
        )
        candidates = list(filter(candidate_filter, keywords))
        return candidates

    async def create_new_keyword_settings_for_complex_advs(
        self,
        complex_advs: list[ComplexAdv],
        stats: list["NormqueryStatsDTO"],
    ) -> None:
        adv_id_to_complex_adv = {
            adv_id: adv for adv in complex_advs for adv_id in adv.all_adv_ids
        }
        async with sm(read_only=False) as session:
            for stat in stats:
                complex_adv = adv_id_to_complex_adv[stat.adv_id]
                texts: list[str] = [st.norm_query for st in stat.stats]
                await self._add_new_keyword_settings_to_session(
                    session,
                    complex_adv,
                    texts,
                )
            await session.commit()

    async def create_new_keyword_settings(
        self, complex_adv: ComplexAdv, stats: list[KeywordStat]
    ) -> None:
        texts: list[str] = [stat.text for stat in stats]
        async with sm(read_only=False) as session:
            await self._add_new_keyword_settings_to_session(
                session,
                complex_adv,
                texts,
            )
            await session.commit()

    async def _add_new_keyword_settings_to_session(
        self,
        session: AsyncSession,
        complex_adv: ComplexAdv,
        texts: list[str],
    ) -> None:
        """Единая логика: существующие ключевые слова, new_texts, релевантность, добавление KeywordSetting в session."""
        if not texts:
            return
        original_adv_id = complex_adv.original_adv_setting_id
        exists_keywords_text: Sequence[str] = await self.__get_exists_keyword_settings_text(
            session, original_adv_id, texts
        )
        new_texts: set[str] = set(texts) - set(exists_keywords_text)
        adv_setting = complex_adv.adv_setting
        is_v3 = is_v3_campaign(adv_setting.bot_active)
        flags_for = RelevantPhraseManager.build_initial_flags_evaluator(adv_setting)
        for text in new_texts:
            hard_status, relevant = flags_for(text)
            keyword_kwargs: dict[str, object] = {}
            if is_v3:
                keyword_kwargs["strategy_mode"] = strategy_mode_for_hard_status_write_v3(
                    hard_status,
                    adv_strategy=adv_setting.strategy,
                )
            session.add(
                KeywordSetting(
                    text=text,
                    hard_status=hard_status,
                    adv_setting_id=original_adv_id,
                    relevant=relevant,
                    **keyword_kwargs,
                )
            )

    @staticmethod
    async def __get_exists_keyword_settings_text(
        session: AsyncSession,
        original_adv_id: int,
        texts: list[str],
    ) -> Sequence[str]:
        """Run in the same session so uncommitted adds in the same transaction are visible (avoids duplicate inserts when multiple stats map to the same adv_setting_id)."""
        if not texts:
            return ()
        stmt = select(KeywordSetting.text).where(
            KeywordSetting.text.in_(texts),
            KeywordSetting.adv_setting_id == original_adv_id,
        )
        results = await session.execute(stmt)
        return results.scalars().all()
