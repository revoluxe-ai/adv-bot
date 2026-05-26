"""Общие фабрики для unit-тестов V3 transition ranking."""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
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


def sample_profile(
    *,
    min_pay: float = 25.0,
    high_pay: float = 40.0,
) -> list[PositionProfilePoint]:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        PositionProfilePoint(
            position=1,
            bid=100,
            predicted_conversion=0.01,
            pay_for_cart=high_pay,
            timestamp=ts,
        ),
        PositionProfilePoint(
            position=2,
            bid=80,
            predicted_conversion=0.02,
            pay_for_cart=min_pay,
            timestamp=ts,
        ),
    ]


def calc_kw(
    *,
    ks_id: int,
    text: str,
    mode: KeywordStrategyMode,
    hard_status: int = 1,
    above_rec: bool | None = True,
    views: int = 50,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(text).model_copy(
        update={"views": views, "clicks": 10, "orders": 2, "conv_views_to_orders": 0.05}
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
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=True,
        ),
        rating=1.0,
        target_pay_for_order=None,
        above_rec_conversion=above_rec,
        cpm_sources=KeywordCpmSources(cpm_set_bid=200),
    )


def ctx(
    *,
    ks_id: int,
    mode: KeywordStrategyMode,
    profile: list[PositionProfilePoint] | None,
    above_rec: bool | None = True,
) -> KeywordV3Context:
    return KeywordV3Context(
        keyword=calc_kw(
            ks_id=ks_id,
            text=f"kw{ks_id}",
            mode=mode,
            above_rec=above_rec,
        ),
        position_profile=profile,
    )
