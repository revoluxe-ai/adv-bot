"""Гейт свежести статы на enable A/B Hold (spec ``card-ab-hold-mode``).

Decision ``card-ab-hold-write-path-ownership`` §2a/2b: при проблемах получения /
свежести статы (тот же класс ``StatsFreshnessGuard``) enable → PENDING запрещён;
UI MUST показать причину, ограничение и ``const.SUPPORT_LINK``.
После PENDING/ACTIVE freshness не режет setup/hold scheduling (см. manager).
"""

from __future__ import annotations

from sqlalchemy import select

from app.settings import settings
from app.client_bot import const
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessState,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_manager import (
    StatsFreshnessManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.utils.db.session_maker import get_async_session_maker as sm


def allows_ab_hold_enable_for_stats_state(
    state: StatsFreshnessState | None,
    *,
    guard_enabled: bool,
) -> bool:
    """True, если enable разрешён по состоянию свежести.

    При выключенном guard — всегда True. При ``state is None`` (нет оценки) —
    fail-closed для enable (в отличие от runner fail-open на cache miss):
    без уверенности в здоровой стате тест не стартуем.
    """
    if not guard_enabled:
        return True
    if state is None:
        return False
    return bool(state.is_fresh)


def user_facing_stats_block_reason(reason: str | None) -> str:
    """Человекочитаемая причина для UI (как в AdvSettingMenu)._stale_reason_to_display."""
    if not reason:
        return "Статистика кампании недоступна или не свежая"
    if "full_adv_stat_update" in reason:
        name = "Рекламная стата"
    elif "common_stat_update" in reason:
        name = "Общая стата"
    elif "cluster_stat_update" in reason:
        name = "Кластерная стата"
    else:
        name = "Стата"
    if "not yet collected" in reason:
        return f"{name} ещё не собрана"
    if "stale over 6h" in reason:
        return f"{name} устарела более чем на 6 часов"
    return f"{name} не свежая"


def build_ab_hold_enable_blocked_by_stats_message(reason: str | None) -> str:
    """Полный текст отказа enable: причина + ограничение + SUPPORT_LINK.

    Spec: enable shows reason, restriction, and support link.
    """
    why = user_facing_stats_block_reason(reason)
    return (
        f"Включение режима A/B теста ограничено.\n\n"
        f"Причина: {why}.\n\n"
        f"Пока есть проблемы с получением статистики по РК, "
        f"включать тест нельзя — дождитесь обновления статы "
        f"или обратитесь в поддержку: {const.SUPPORT_LINK}"
    )


def build_ab_hold_enable_blocked_alert(reason: str | None) -> str:
    """Короткий ``answerCallbackQuery`` (лимит Telegram ≤200)."""
    why = user_facing_stats_block_reason(reason)
    text = f"A/B: {why}. Поддержка: {const.SUPPORT_LINK}"
    if len(text) <= 200:
        return text
    return "Включение A/B ограничено: проблемы со статой. См. экран."


async def evaluate_ab_hold_enable_stats(
    adv: AdvSetting,
) -> tuple[bool, str | None]:
    """Оценить свежесть статы кампании для enable (ClickHouse / StatsFreshnessManager).

    Returns:
        (allowed, raw_reason_or_None). allowed=False → enable MUST NOT.
    """
    guard_enabled = bool(settings.STATS_FRESHNESS_GUARD_ENABLED)
    if not guard_enabled:
        return True, None

    search_adv: AdvSetting | None = None
    search_adv_id = getattr(adv, "search_adv_id", None)
    if search_adv_id:
        async with sm() as session:
            search_adv = await session.scalar(
                select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
            )

    complex_adv = ComplexAdv(adv, search_adv)
    state = await StatsFreshnessManager().evaluate(complex_adv)
    allowed = allows_ab_hold_enable_for_stats_state(
        state, guard_enabled=True
    )
    return allowed, state.reason
