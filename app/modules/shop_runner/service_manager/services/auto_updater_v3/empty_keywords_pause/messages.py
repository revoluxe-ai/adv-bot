"""Тексты Telegram для empty-keywords pause/resume (spec User notification)."""

from __future__ import annotations

from app.client_bot import const as client_bot_const


def build_empty_keywords_pause_message(
    *,
    campaign_name: str,
    adv_id: int,
    include_support_link: bool = True,
) -> str:
    """Сообщение: пауза из-за отсутствия активных ключей + перепроверка.

    Spec ``User notification on empty-keywords pause``.
    Зачем отдельная функция: Telegram limit tests с worst-case placeholders.
    """
    name = (campaign_name or "").strip() or f"РК {adv_id}"
    lines = [
        f"Кампания «{name}» (id {adv_id}): нога Поиск поставлена на паузу:",
        "бот выключил все активные ключи — выключать больше нечего.",
        "Периодически Поиск будет снова включаться для перепроверки.",
    ]
    if include_support_link:
        lines.append(f"Помощь: {client_bot_const.SUPPORT_LINK}")
    return "\n".join(lines)


def build_empty_keywords_resume_message(
    *,
    campaign_name: str,
    adv_id: int,
    include_support_link: bool = True,
) -> str:
    """Сообщение: Поиск снова включён после empty-keywords pause episode.

    Spec ``User notification on empty-keywords resume/re-enable``.
    Текст MUST быть отличным от pause-entry и от recheck-mention внутри него.
    """
    name = (campaign_name or "").strip() or f"РК {adv_id}"
    lines = [
        f"Кампания «{name}» (id {adv_id}): нога Поиск снова включена.",
        "Активные ключи восстановлены — кампания возобновлена.",
    ]
    if include_support_link:
        lines.append(f"Помощь: {client_bot_const.SUPPORT_LINK}")
    return "\n".join(lines)
