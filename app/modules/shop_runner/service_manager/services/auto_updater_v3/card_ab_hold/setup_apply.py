"""Persist ENTER-мутаций A/B Hold (OFF + ЦП := текущая позиция).

Spec ``card-ab-hold-mode``: FAIL → OFF; PASS → target_place = WB position.
Использует тот же SQLAlchemy update-паттерн, что ``WhiteListTrimmer`` —
без full NORMAL preamble (decision write-path ownership).
"""

from __future__ import annotations

import logging
import math

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    hard_status_for_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    clamp_not_full_target_place,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


def ab_hold_target_place_from_keyword(keyword: CalculatedKeyword) -> int | None:
    """ЦП из фактической позиции ключа (то же округление, что not-full migrate).

    Spec card-ab-hold-mode: PASS → target_place := current WB place.
    """
    pos = float(keyword.position)
    if pos <= 0:
        return None
    return clamp_not_full_target_place(int(math.floor(pos + 0.5)))


async def apply_ab_hold_setup_mutations(
    *,
    adv_id: int,
    adv_setting_id: int,
    keywords: list[CalculatedKeyword],
    max_pay_for_order: float,
) -> tuple[int, int]:
    """Применить ENTER: OFF на FAIL, ЦП на PASS; mode → ACTIVE.

    Returns:
        (pass_count, fail_count)
    """
    fail_ids: list[int] = []
    pass_updates: list[tuple[int, int]] = []
    for kw in keywords:
        action = classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=max_pay_for_order,
        )
        ks_id = int(kw.keyword_setting_original_id)
        if action == AbHoldSetupAction.FAIL_OFF:
            fail_ids.append(ks_id)
            continue
        place = ab_hold_target_place_from_keyword(kw)
        if place is not None:
            pass_updates.append((ks_id, place))

    off_hs = hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    async with sm(read_only=False) as session:
        if fail_ids:
            stmt_off = (
                update(KeywordSetting)
                .where(KeywordSetting.id.in_(fail_ids))
                .values(
                    hard_status=off_hs,
                    strategy_mode=KeywordStrategyMode.OFF,
                    target_place=None,
                )
            )
            _ = await session.execute(stmt_off)
        for ks_id, place in pass_updates:
            stmt_tp = (
                update(KeywordSetting)
                .where(KeywordSetting.id == ks_id)
                .values(target_place=place)
            )
            _ = await session.execute(stmt_tp)
        stmt_mode = (
            update(AdvSetting)
            .where(AdvSetting.id == adv_setting_id)
            .values(card_ab_hold_mode=CardAbHoldMode.ACTIVE.value)
        )
        _ = await session.execute(stmt_mode)
        await session.commit()

    logger.info(
        "[adv_id=%s] ab_setup applied pass=%s fail=%s → ACTIVE",
        adv_id,
        len(pass_updates),
        len(fail_ids),
    )
    return len(pass_updates), len(fail_ids)
