"""Post-apply хук: детект empty-set и one-shot intent (без WB pause).

Spec: ``pause-on-empty-keywords``. ADL: ``empty-keywords-pause-write-path``.
Pause исполняет activity-control как следующий шаг после OFF.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
    count_active_keywords,
    had_force_off_action,
    is_warmup_false_empty_keywords,
    should_request_empty_keywords_pause_intent,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

logger = logging.getLogger(__name__)


async def maybe_set_empty_keywords_pause_intent(
    *,
    adv_id: int,
    bot_active: bool,
    keywords: Iterable[CalculatedKeyword],
    post_gate_actions: Iterable[V3Action] | None,
    campaign_status: WBAdvActiveStatus | str | None,
) -> bool:
    """После OFF/apply: при пустом наборе поставить Redis intent (не pause).

    ``campaign_status`` — статус **Search**-ноги (INC-PAUSE-02 recheck).
    Intent keyed по ``adv_id`` комплекта; исполнение pause — Search adapters.

    Redis ``__empty__`` warmup / transient false-empty (без FORCE_OFF) MUST NOT
    arm intent — тот же gate, что ROOT-001 no-prior arm (tasks §7.2).
    Bot-driven FORCE_OFF + empty set по-прежнему arms (settled empty).

    Returns:
        True если intent записан.
    """
    active_count = count_active_keywords(keywords)
    bot_driven_off = had_force_off_action(post_gate_actions)
    campaign_is_started = False
    if isinstance(campaign_status, WBAdvActiveStatus):
        campaign_is_started = campaign_status == WBAdvActiveStatus.STARTED
    elif campaign_status is not None:
        try:
            campaign_is_started = (
                WBAdvActiveStatus(str(campaign_status)) == WBAdvActiveStatus.STARTED
            )
        except ValueError:
            campaign_is_started = False

    intent_mgr = EmptyKeywordsPauseIntentManager()
    # Apply_hook не получает ComplexAdv; Redis HEXISTS ``__empty__`` — канон
    # (ROOT-001 helper ``is_warmup_false_empty_keywords``).
    warmup_false_empty = await is_warmup_false_empty_keywords(
        adv=object(),
        redis_client=intent_mgr.client,
        adv_id=int(adv_id),
    )
    if not should_request_empty_keywords_pause_intent(
        active_count=active_count,
        bot_active=bot_active,
        bot_driven_off_completed=bot_driven_off,
        campaign_is_started=campaign_is_started,
        is_warmup_false_empty=warmup_false_empty,
    ):
        if (
            warmup_false_empty
            and not bot_driven_off
            and active_count == 0
            and campaign_is_started
            and bot_active
        ):
            logger.info(
                "[adv_id=%s] empty-keywords: skip intent arm — Redis __empty__ "
                "warmup / transient false-empty (not settled empty; no FORCE_OFF) "
                "active=%s started=%s",
                adv_id,
                active_count,
                campaign_is_started,
            )
        return False
    await intent_mgr.set_intent(int(adv_id))
    logger.info(
        "[adv_id=%s] empty-keywords: pause intent set (active=%s off=%s started=%s)",
        adv_id,
        active_count,
        bot_driven_off,
        campaign_is_started,
    )
    return True
