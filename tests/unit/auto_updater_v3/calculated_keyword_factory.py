"""Shared CalculatedKeyword factories for auto_updater_v3 unit tests."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def make_calculated_keyword(
    *,
    ks_id: int,
    text: str,
    mode: KeywordStrategyMode,
    hard_status: int = 2,
    conv: float = 0.0,
    cpm_set_bid: int = 200,
) -> CalculatedKeyword:
    """Создать минимальный CalculatedKeyword для unit-тестов V3."""
    stat = make_zero_keyword_stat(text).model_copy(
        update={"conv_views_to_orders": conv, "views": 10, "clicks": 1}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=True,
            hard_status=hard_status,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
        cpm_sources=KeywordCpmSources(cpm_set_bid=cpm_set_bid),
    )
