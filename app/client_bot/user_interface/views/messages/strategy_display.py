from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy


def format_adv_strategy(strategy: Strategy | None) -> str:
    """Return user-friendly strategy label with MIN_CPO fallback."""
    value = strategy or Strategy.MIN_CPO
    labels = {
        Strategy.MIN_CPO: "Мин себес",
        Strategy.OPTIMUM: "Оптимум",
        Strategy.MAX_CONV: "Макс конв",
    }
    return labels.get(value, "Мин себес")
