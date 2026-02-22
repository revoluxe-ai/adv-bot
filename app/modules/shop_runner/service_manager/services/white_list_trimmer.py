from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.db.session_maker import get_async_session_maker as sm
import logging


logger = logging.getLogger(__name__)

class WhiteListTrimmer:

    async def  trim(self, complex_adv: ComplexAdv) -> None:
        # TODO: Централизовать добавление, удаление ключей из БС
        keywords = await complex_adv.get_keywords()
        if complex_adv.auto_add_only_relevant_phrase:
            keywords = [kw for kw in keywords if kw.relevant]
        keywords.sort(key=lambda x: x.rating_by_orders, reverse=True)
        top_key_in_auto_position: int | None = self._get_top_key_in_auto_position(keywords)
        if top_key_in_auto_position is None:
            return None
        keywords_below = keywords[top_key_in_auto_position:]
        candidates_to_auto_ids: list[int] = []
        for kw in keywords_below:
            if kw.hard_status == 2:
                candidates_to_auto_ids.append(kw.keyword_setting_original_id)

        if not candidates_to_auto_ids:
            return None

        replacement_ids: list[int] = []
        if complex_adv.white_list_mode == WhiteListMode.REPLACE_ON_TRIM:
            replacement_ids = self._collect_replacement_candidates(
                complex_adv=complex_adv,
                keywords=keywords,
                removed_ids=set(candidates_to_auto_ids),
                removed_count=len(candidates_to_auto_ids),
            )

        stmt_remove = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(candidates_to_auto_ids))
            .values(hard_status=1)
        )
        async with sm(read_only=False) as session:
            await session.execute(stmt_remove)
            if replacement_ids:
                stmt_add = (
                    update(KeywordSetting)
                    .where(KeywordSetting.id.in_(replacement_ids))
                    .values(hard_status=2)
                )
                await session.execute(stmt_add)
            await session.commit()
        return None

    @staticmethod
    def _get_top_key_in_auto_position(keywords: list[CalculatedKeyword]) -> int | None:
         for n, kw in enumerate(keywords):
             if kw.hard_status == 1:
                 return n
         else:
             return None

    @staticmethod
    def _collect_replacement_candidates(
        complex_adv: ComplexAdv,
        keywords: list[CalculatedKeyword],
        removed_ids: set[int],
        removed_count: int,
    ) -> list[int]:
        if removed_count <= 0:
            return []

        white_indices_after_trim = [
            idx
            for idx, kw in enumerate(keywords)
            if kw.hard_status == 2 and kw.keyword_setting_original_id not in removed_ids
        ]
        # Если БС пуст после отрезки - добираем с начала списка.
        start_index = max(white_indices_after_trim) + 1 if white_indices_after_trim else 0

        replacement_ids: list[int] = []
        # TODO: Централизовать по всему проекту отбор кандидатов в белый список!
        for kw in keywords[start_index:]:
            if kw.hard_status != 1:
                continue
            if complex_adv.auto_add_only_relevant_phrase and not kw.relevant:
                continue
            kw_id = kw.keyword_setting_original_id
            if kw_id in removed_ids:
                continue
            if (complex_adv.rec_system_promotion_mode_active
                    and kw.above_rec_conversion is False
                    and complex_adv.auto_adv_active_status):
                continue
            replacement_ids.append(kw_id)
            if len(replacement_ids) >= removed_count:
                break
        return replacement_ids


