from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    keyword_strategy_mode_for_adv_strategy,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.db.session_maker import get_async_session_maker as sm
import logging


logger = logging.getLogger(__name__)

class WhiteListTrimmer:
    async def  trim(self, complex_adv: ComplexAdv) -> None:
        if is_v3_campaign(complex_adv.bot_active):
            logger.debug(
                "[adv_id=%s] white_list_trimmer skip for v3 campaign",
                complex_adv.adv_id,
            )
            return None
        # TODO: Централизовать добавление, удаление ключей из БС
        keywords = await complex_adv.get_keywords()
        if complex_adv.auto_add_only_relevant_phrase:
            keywords = [kw for kw in keywords if kw.relevant]
        keywords.sort(key=lambda x: x.rating or 0, reverse=True)
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

        stmt_remove = update(KeywordSetting).where(
            KeywordSetting.id.in_(candidates_to_auto_ids)
        )
        if is_v3_campaign(complex_adv.bot_active):
            stmt_remove = stmt_remove.values(
                hard_status=1,
                strategy_mode=KeywordStrategyMode.OFF,
            )
        else:
            stmt_remove = stmt_remove.values(hard_status=1)
        async with sm(read_only=False) as session:
            _ = await session.execute(stmt_remove)
            if replacement_ids:
                stmt_add = update(KeywordSetting).where(
                    KeywordSetting.id.in_(replacement_ids)
                )
                if is_v3_campaign(complex_adv.bot_active):
                    stmt_add = stmt_add.values(
                        hard_status=2,
                        strategy_mode=keyword_strategy_mode_for_adv_strategy(
                            complex_adv.strategy
                        ),
                    )
                else:
                    stmt_add = stmt_add.values(hard_status=2)
                _ = await session.execute(stmt_add)
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
        """Замены в БС после trim; те же правила полок, что в ``KeywordsManager`` (``is_shelf_activation_allowed``)."""
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
                    and complex_adv.auto_adv_active_status
                    and complex_adv.is_shelf_activation_allowed):
                continue
            replacement_ids.append(kw_id)
            if len(replacement_ids) >= removed_count:
                break
        # Если из "хвоста" не удалось добрать до removed_count, делаем второй проход
        # по всему списку: это закрывает кейс, когда валидные auto-кандидаты есть
        # выше start_index и БС иначе монотонно уменьшается.
        if len(replacement_ids) < removed_count:
            already_selected = set(replacement_ids)
            for kw in keywords:
                if len(replacement_ids) >= removed_count:
                    break
                if kw.hard_status != 1:
                    continue
                if complex_adv.auto_add_only_relevant_phrase and not kw.relevant:
                    continue
                kw_id = kw.keyword_setting_original_id
                if kw_id in removed_ids or kw_id in already_selected:
                    continue
                if (
                    complex_adv.rec_system_promotion_mode_active
                    and kw.above_rec_conversion is False
                    and complex_adv.auto_adv_active_status
                    and complex_adv.is_shelf_activation_allowed
                ):
                    continue
                replacement_ids.append(kw_id)
                already_selected.add(kw_id)
        return replacement_ids


