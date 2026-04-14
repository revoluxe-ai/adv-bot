"""Human-readable WB campaign status labels for connect-existing flow."""

# Статус (код WB int или строка active_status) → текст для пользователя
STATUS_DISPLAY_RU: dict[int | str, str] = {
    4: "готова к старту",
    7: "завершена",
    8: "отклонена",
    9: "запущена",
    11: "пауза",
    "ready_for_start": "готова к старту",
    "done": "завершена",
    "refused": "отклонена",
    "started": "запущена",
    "pause": "пауза",
}


def format_status_for_display(status: int | str | None) -> str:
    """Числовой код WB (4,7,8,9,11) или строка active_status → строка для отображения."""
    if status is None:
        return "—"
    return STATUS_DISPLAY_RU.get(status, str(status))
