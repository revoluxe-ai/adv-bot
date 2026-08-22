"""Unit-тесты сортировки ключей V3 в UI (pay_for_order asc)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyboards import sorting_keywords_for_v3
from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
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
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.enum import KeywordRatingMode
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


def _kw(ks_id: int, orders_per_1000: float) -> CalculatedKeyword:
    text = f"k{ks_id}"
    cpm = 100.0
    conv = orders_per_1000 * cpm / 1_000_000.0
    stat = make_zero_keyword_stat(text).model_copy(
        update={"conv_views_to_orders": conv}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=True,
            hard_status=1,
            id=ks_id,
            strategy_mode=KeywordStrategyMode.OFF,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=orders_per_1000,
        rating_mode=KeywordRatingMode.BY_MIN_CPO,
        target_pay_for_order=None,
        cpm_sources=KeywordCpmSources(cpm_set_bid=100),
    )


@pytest.mark.unit
def test_v3_sort_pay_for_order_asc() -> None:
    """Сортировка по ``pay_for_order`` asc (дешёвые сверху)."""
    kws = [_kw(1, 5.0), _kw(2, 50.0), _kw(3, 20.0)]
    sorted_kws = sorting_keywords_for_v3(kws)
    ids = [k.keyword_setting.id for k in sorted_kws]
    assert ids == [2, 3, 1]


@pytest.mark.unit
def test_v3_sort_pay_for_order_none_at_tail() -> None:
    """Ключи без ``pay_for_order`` — в конец, tie-break по ``keyword_setting_id``."""
    with_pfo = _kw(10, 30.0)
    no_pfo = _kw(11, 0.0).model_copy(
        update={
            "cluster_stat": with_pfo.cluster_stat.model_copy(
                update={"conv_views_to_orders": 0.0}
            )
        }
    )
    sorted_kws = sorting_keywords_for_v3([no_pfo, with_pfo])
    assert [k.keyword_setting.id for k in sorted_kws] == [10, 11]


@pytest.mark.unit
def test_create_pre_calculated_keywords_v3_forces_min_cpo_rating() -> None:
    adv = MagicMock()
    adv.bot_active = True
    complex_adv = MagicMock()
    complex_adv.strategy = Strategy.MAX_CONV
    complex_adv.adv_setting = adv
    complex_adv.adv_id = 1

    assert (
        CalculatedKeywordsManager.resolve_keyword_rating_mode(complex_adv)
        == KeywordRatingMode.BY_MIN_CPO
    )
