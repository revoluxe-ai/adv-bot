from app.client_bot.user_interface.views.messages.strategy_display import (
    format_adv_strategy,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


def test_format_adv_strategy_min_cpo() -> None:
    assert format_adv_strategy(Strategy.MIN_CPO) == "Мин себес"


def test_format_adv_strategy_max_conv() -> None:
    assert format_adv_strategy(Strategy.MAX_CONV) == "Макс конв"


def test_format_adv_strategy_optimum() -> None:
    assert format_adv_strategy(Strategy.OPTIMUM) == "Оптимум"


def test_format_adv_strategy_none_uses_min_cpo_fallback() -> None:
    assert format_adv_strategy(None) == "Мин себес"
