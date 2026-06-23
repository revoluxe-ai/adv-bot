"""Shared user-facing messages for target place UI flows."""


def get_auto_target_place_manual_change_locked_text() -> str:
    """Return guard text for manual target place changes while auto-update is enabled."""
    return (
        "Автоматическое обновление целевых позиций включено. "
        "Отключите его, чтобы менять целевые позиции вручную."
    )
