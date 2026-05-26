"""Синхронизация ``hard_status`` и ``strategy_mode`` для V3-кампаний.

Контракт V3:
- ручные/массовые смены ``hard_status`` должны сразу выставлять согласованный
  ``strategy_mode``;
- изменения ``strategy_mode`` через V3 ladder в ``applier`` уже синхронизируют
  ``hard_status`` в обратную сторону.
"""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode

_V3_AUTOMATIC_VERSION = 3

_HARD_STATUS_BLACK_LIST = 0
_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2
_HARD_STATUS_TURN_OFF = 3
_HARD_STATUS_ALWAYS_ON = 4


def is_v3_campaign(automatic_version: int | None) -> bool:
    """True только для кампаний с ``automatic_version == 3``."""
    return automatic_version == _V3_AUTOMATIC_VERSION


def strategy_mode_for_hard_status_write_v3(hard_status: int) -> KeywordStrategyMode:
    """Целевой ``strategy_mode`` при явной смене ``hard_status`` в V3.

    Используется в write-путях, где ``hard_status`` задается напрямую:
    - БС / фикс.фразы -> ``MIN_CPA``;
    - авто / ЧС / отключено -> ``OFF``.
    """
    hs = int(hard_status)
    if hs in (_HARD_STATUS_WHITE_LIST, _HARD_STATUS_ALWAYS_ON):
        return KeywordStrategyMode.MIN_CPA
    if hs in (
        _HARD_STATUS_AUTO_MODE,
        _HARD_STATUS_BLACK_LIST,
        _HARD_STATUS_TURN_OFF,
    ):
        return KeywordStrategyMode.OFF
    raise ValueError(f"Unsupported hard_status for V3 sync: {hard_status}")


def is_v3_status_mode_consistent(
    *, hard_status: int, strategy_mode: KeywordStrategyMode
) -> bool:
    """Проверка инварианта для существующих V3-записей.

    Допускает ``hard_status=2`` с любым активным mode (MIN/OPT/MAX), т.к. это
    нормальное состояние после работы лестницы V3.
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
        return strategy_mode == KeywordStrategyMode.MIN_CPA
    return True


def repaired_strategy_mode_for_v3(
    *, hard_status: int, strategy_mode: KeywordStrategyMode
) -> KeywordStrategyMode:
    """Возвращает mode после repair, если пара ``hard_status``/``strategy_mode`` невалидна."""
    if is_v3_status_mode_consistent(
        hard_status=hard_status, strategy_mode=strategy_mode
    ):
        return strategy_mode
    if int(hard_status) == _HARD_STATUS_WHITE_LIST:
        return KeywordStrategyMode.MIN_CPA
    return strategy_mode_for_hard_status_write_v3(int(hard_status))


def sync_keyword_setting_mode_for_v3(
    keyword_setting: KeywordSetting,
    *,
    automatic_version: int | None,
    hard_status_override: int | None = None,
) -> bool:
    """Синхронизировать mode у ``KeywordSetting`` после изменения ``hard_status``.

    Returns:
        ``True``, если ``strategy_mode`` был изменен.
    """
    if not is_v3_campaign(automatic_version):
        return False
    hard_status = (
        int(hard_status_override)
        if hard_status_override is not None
        else int(keyword_setting.hard_status)
    )
    expected = strategy_mode_for_hard_status_write_v3(hard_status)
    if keyword_setting.strategy_mode == expected:
        return False
    keyword_setting.strategy_mode = expected
    return True
