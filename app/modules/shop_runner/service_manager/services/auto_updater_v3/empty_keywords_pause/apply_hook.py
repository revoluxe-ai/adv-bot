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
    if not should_request_empty_keywords_pause_intent(
        active_count=active_count,
        bot_active=bot_active,
        bot_driven_off_completed=bot_driven_off,
        campaign_is_started=campaign_is_started,
    ):
        return False
    await EmptyKeywordsPauseIntentManager().set_intent(int(adv_id))
    logger.info(
        "[adv_id=%s] empty-keywords: pause intent set (active=%s off=%s started=%s)",
        adv_id,
        active_count,
        bot_driven_off,
        campaign_is_started,
    )
    return True
