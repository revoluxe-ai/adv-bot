"""Shared user-facing messages for target place UI flows."""


def get_auto_target_place_manual_change_locked_text() -> str:
    """Return guard text for manual target place changes while auto-update is enabled."""
    return (
        "Ручное изменение целевых позиций сейчас заблокировано, потому что "
        "включено автообновление target_place. "
        "Max CPM остаётся доступным для ручного изменения."
    )
