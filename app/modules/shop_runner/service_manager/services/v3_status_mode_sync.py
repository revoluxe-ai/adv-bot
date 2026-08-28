"""Синхронизация ``hard_status`` и ``strategy_mode`` для V3-кампаний.

Контракт V3:
- ручные/массовые смены ``hard_status`` должны сразу выставлять согласованный
  ``strategy_mode``;
- для БС и фикс.фраз активный mode берётся из ``AdvSetting.strategy`` (MIN_CPO →
  ``MIN_CPA``, MAX_CONV → ``MAX_CONVERSION``);
- изменения ``strategy_mode`` через V3 ladder в ``applier`` уже синхронизируют
  ``hard_status`` в обратную сторону.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import (
    KeywordStrategyMode,
    campaign_strategy_to_keyword_strategy_mode,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy

_HARD_STATUS_BLACK_LIST = 0
_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2
_HARD_STATUS_TURN_OFF = 3
_HARD_STATUS_ALWAYS_ON = 4


def is_v3_campaign(bot_active: bool) -> bool:
    """True для кампаний с включённым ботом (единственный auto-updater runtime — V3)."""
    return bot_active


def keyword_strategy_mode_for_adv_strategy(
    adv_strategy: Strategy | str | None,
) -> KeywordStrategyMode:
    """Активный ``strategy_mode`` при входе в БС/фикс.фразы по стратегии РК."""
    return campaign_strategy_to_keyword_strategy_mode(adv_strategy)


def strategy_mode_for_hard_status_write_v3(
    hard_status: int,
    *,
    adv_strategy: Strategy | str | None = None,
) -> KeywordStrategyMode:
    """Целевой ``strategy_mode`` при явной смене ``hard_status`` в V3.

    Используется в write-путях, где ``hard_status`` задается напрямую:
    - БС / фикс.фразы → mode по ``AdvSetting.strategy``;
    - авто / ЧС / отключено → ``OFF``.
    """
    hs = int(hard_status)
    if hs in (_HARD_STATUS_WHITE_LIST, _HARD_STATUS_ALWAYS_ON):
        return keyword_strategy_mode_for_adv_strategy(adv_strategy)
    if hs in (
        _HARD_STATUS_AUTO_MODE,
        _HARD_STATUS_BLACK_LIST,
        _HARD_STATUS_TURN_OFF,
    ):
        return KeywordStrategyMode.OFF
    raise ValueError(f"Unsupported hard_status for V3 sync: {hard_status}")


def is_v3_keyword_eligible_for_cluster_bidding(
    *,
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    adv_strategy: Strategy | str | None = None,
) -> bool:
    """Может ли V3-ключ участвовать в ``update_cluster_bids``.

    Только белый список (2) или фикс.фразы (4) с ``strategy_mode != OFF``.
    Авто (1), ЧС, отключённые и OFF-mode не торгуются.

    ``adv_strategy`` не используется: cluster bids живёт отдельно от V2
    ``AdvSetting.strategy`` и V3 updater-тика; для cap/матрицы важен
    ``strategy_mode`` ключа из Redis, а не стратегия РК.
    """
    _ = adv_strategy
    hs = int(hard_status)
    if hs not in (_HARD_STATUS_WHITE_LIST, _HARD_STATUS_ALWAYS_ON):
        return False
    return strategy_mode != KeywordStrategyMode.OFF


def is_v3_status_mode_consistent(
    *,
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    adv_strategy: Strategy | str | None = None,
) -> bool:
    """Проверка инварианта для существующих V3-записей.

    Допускает ``hard_status=2`` с любым активным mode (MIN/OPT/MAX), т.к. это
    нормальное состояние после работы лестницы V3.
    Фикс.фразы (4) должны совпадать с mode по стратегии РК.
    """
    hs = int(hard_status)
    if hs in (
        _HARD_STATUS_BLACK_LIST,
        _HARD_STATUS_AUTO_MODE,
        _HARD_STATUS_TURN_OFF,
    ):
        return strategy_mode == KeywordStrategyMode.OFF
    if hs == _HARD_STATUS_WHITE_LIST:
        return strategy_mode != KeywordStrategyMode.OFF
    if hs == _HARD_STATUS_ALWAYS_ON:
        return strategy_mode == keyword_strategy_mode_for_adv_strategy(adv_strategy)
    return True


def repaired_strategy_mode_for_v3(
    *,
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    adv_strategy: Strategy | str | None = None,
) -> KeywordStrategyMode:
    """Возвращает mode после repair, если пара ``hard_status``/``strategy_mode`` невалидна."""
    if is_v3_status_mode_consistent(
        hard_status=hard_status,
        strategy_mode=strategy_mode,
        adv_strategy=adv_strategy,
    ):
        return strategy_mode
    if int(hard_status) == _HARD_STATUS_WHITE_LIST:
        return keyword_strategy_mode_for_adv_strategy(adv_strategy)
    return strategy_mode_for_hard_status_write_v3(
        int(hard_status), adv_strategy=adv_strategy
    )


def sync_keyword_setting_mode_for_v3(
    keyword_setting: KeywordSetting,
    *,
    bot_active: bool,
    hard_status_override: int | None = None,
    adv_strategy: Strategy | str | None = None,
) -> bool:
    """Синхронизировать mode у ``KeywordSetting`` после изменения ``hard_status``.

    ``adv_strategy`` передаётся явно из загруженного ``AdvSetting`` (без lazy-load
    relationship в async-контуре). Для V3 при ``hard_status`` 2 (БС) и 4 (фикс.фразы)
    вызывающий код должен передать стратегию РК; для 0/1/3 можно ``None`` (режим OFF).

    Returns:
        ``True``, если ``strategy_mode`` был изменен.
    """
    if not is_v3_campaign(bot_active):
        return False
    hard_status = (
        int(hard_status_override)
        if hard_status_override is not None
        else int(keyword_setting.hard_status)
    )
    expected = strategy_mode_for_hard_status_write_v3(
        hard_status, adv_strategy=adv_strategy
    )
    if keyword_setting.strategy_mode == expected:
        return False
    keyword_setting.strategy_mode = expected
    return True
