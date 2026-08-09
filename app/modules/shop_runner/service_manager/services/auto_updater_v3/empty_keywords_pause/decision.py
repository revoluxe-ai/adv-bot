"""Чистые решения для pause-on-empty-keywords (spec + 7d proof).

Spec: ``pause-on-empty-keywords``.
Зачем: отделить detect/ordering от WB pause (pause = следующий шаг в activity-control).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AuctionReasonCode,
    AutoReasonCode,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

# Продуктовый лимит окна статистики; recheck MUST NOT требовать больше.
STATS_WINDOW_DAYS_MAX = 7

# Поле Redis hash ``calculated_keywords:{adv_id}`` — warmup/empty marker
# (см. RedisCalculatedKeywordsCacheManager._CALCULATED_KEYWORDS_EMPTY_FIELD).
REDIS_CALCULATED_KEYWORDS_EMPTY_FIELD = "__empty__"


def is_adv_warmup_empty_marker_signal(adv: object) -> bool:
    """True если ComplexAdv/seam помечен как Redis warmup ``__empty__`` false-empty.

    Production ``ComplexAdv`` обычно не выставляет эти атрибуты — тогда сигнал
    берётся из Redis HEXISTS (см. ``redis_has_calculated_keywords_empty_marker``).
    Unit-seam ROOT-001 выставляет ``redis_keywords_empty_marker`` /
    ``keywords_source``.
    """
    if bool(getattr(adv, "redis_keywords_empty_marker", False)):
        return True
    return getattr(adv, "keywords_source", None) == "redis_warmup_empty_marker"


async def redis_has_calculated_keywords_empty_marker(
    redis_client: Any,
    adv_id: int,
) -> bool:
    """True если в Redis hash keywords есть warmup-маркер ``__empty__``.

    Args:
        redis_client: async Redis client (``hexists``).
        adv_id: id авто-РК комплекта (ключ ``calculated_keywords:{adv_id}``).

    Returns:
        True при наличии поля ``__empty__`` — transient/warmup false-empty,
        не bot-driven settled empty с OFF-ключевыми объектами в hash.
    """
    key = f"calculated_keywords:{int(adv_id)}"
    return bool(
        await redis_client.hexists(key, REDIS_CALCULATED_KEYWORDS_EMPTY_FIELD)
    )


async def is_warmup_false_empty_keywords(
    *,
    adv: object,
    redis_client: Any,
    adv_id: int,
) -> bool:
    """Warmup/transient false-empty: Adv-сигнал или Redis ``__empty__`` маркер.

    Spec «Settled empty vs Redis warmup false-empty» / tasks §7.2: no-prior-intent
    arm MUST NOT считать это settled empty.
    """
    if is_adv_warmup_empty_marker_signal(adv):
        return True
    return await redis_has_calculated_keywords_empty_marker(redis_client, adv_id)


def count_active_keywords(keywords: Iterable[CalculatedKeyword]) -> int:
    """Число ключей не в OFF после apply (spec: empty = 0 активных).

    Spec ``Pause campaign after last keyword off by bot``: активный =
    ``strategy_mode != OFF``.
    """
    return sum(
        1
        for kw in keywords
        if kw.strategy_mode != KeywordStrategyMode.OFF
    )


def had_force_off_action(actions: Iterable[V3Action] | None) -> bool:
    """Был ли в тике bot-driven FORCE_OFF (текущий шаг = OFF ключа)."""
    if not actions:
        return False
    return any(a.action == V3ActionType.FORCE_OFF for a in actions)


def should_request_empty_keywords_pause_intent(
    *,
    active_count: int,
    bot_active: bool,
    bot_driven_off_completed: bool,
    campaign_is_started: bool,
    is_warmup_false_empty: bool = False,
) -> bool:
    """Нужен ли one-shot intent на pause как **следующий** шаг.

    Spec: OFF = текущий шаг; когда выключать больше нечего — следующий шаг pause.
    Intent ставит V3 после OFF/flush; pause исполняет activity-control позже.

    - ``bot_driven_off_completed`` и ``active_count==0`` — только что опустошили набор
      (settled empty; warmup-флаг не отменяет bot-driven OFF).
    - ``campaign_is_started`` и ``active_count==0`` — recheck / no-prior-intent empty;
      при ``is_warmup_false_empty`` MUST NOT arm (ROOT-001 / tasks §7.2).
    Пока кампания уже на паузе и OFF в этом тике не было — intent не ставим,
    чтобы не блокировать периодический recheck-start.
    """
    if not bot_active or active_count != 0:
        return False
    if bot_driven_off_completed:
        return True
    if is_warmup_false_empty:
        return False
    return campaign_is_started


def is_empty_keywords_reason(reason_code: Any) -> bool:
    """True если reason = empty_keywords (не schedule/budget/cost).

    INC-PAUSE-02: durable reason пишется на Search-lane
    (``AuctionReasonCode.EMPTY_KEYWORDS``); value совпадает с Auto enum.
    """
    if reason_code is None:
        return False
    if reason_code in (
        AutoReasonCode.EMPTY_KEYWORDS,
        AuctionReasonCode.EMPTY_KEYWORDS,
    ):
        return True
    return getattr(reason_code, "value", None) == (
        AuctionReasonCode.EMPTY_KEYWORDS.value
    )


def stats_window_compatible_with_recheck(available_stats_days: int) -> bool:
    """True, если окно доступной статистики совместимо с recheck (≤7 дней).

    Продуктовый инвариант spec Seven-day statistics / ADL: recheck и pause
    path для empty-keywords не требуют окна статы больше
    ``STATS_WINDOW_DAYS_MAX`` (7). Отрицательные значения — несовместимы.
    """
    if available_stats_days < 0:
        return False
    return available_stats_days <= STATS_WINDOW_DAYS_MAX
