"""Тексты confirm-экранов A/B Hold (storyboard RU, ux contract §§5–11).

Факт-позиция и целевая позиция всегда подписаны отдельно («факт» / «цель»);
внутренние имена полей PG не показываются пользователю.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.client_bot import const
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.epoch_lifecycle import (
    DEFAULT_WARMUP_HOURS,
    is_warmup_elapsed,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldPhase,
    normalize_card_ab_hold_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.confirm_callbacks import (
    ConfirmStep,
)

STALE_TOAST = "Экран обновился — показываю актуальный шаг."
_W3_EXCLUSION_SECTION_TITLE = "Исключены из подтверждения:"
_W3_EXCLUSION_OMISSION_NOTICE = "Остальные исключения не показаны."


def phase_label(phase: CardAbHoldPhase | str | None) -> str:
    """Человекочитаемая метка текущего шага для summary/S0."""
    p = normalize_card_ab_hold_phase(phase)
    labels = {
        CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM: "Подтверждение набора ключей",
        CardAbHoldPhase.WARM_UP: "Прогрев (WARM_UP)",
        CardAbHoldPhase.AWAITING_TP_CONFIRM: "Подтверждение целевых позиций",
        CardAbHoldPhase.AWAITING_AUTO_PARTICIPATION_CONFIRM: "Участие Auto",
        CardAbHoldPhase.AWAITING_AUTO_BID_CONFIRM: "Ставка Auto",
        CardAbHoldPhase.PENDING_INTENT: "Синхронизация с Wildberries",
        CardAbHoldPhase.WB_SYNC: "Синхронизация с Wildberries",
        CardAbHoldPhase.READY_ACTIVE: "Активный hold",
    }
    if p is None:
        return "Подготовка A/B теста"
    return labels.get(p, "Подготовка A/B теста")


def build_summary_text(*, phase: CardAbHoldPhase | str | None) -> str:
    """Summary после Back (§7): черновик сохранён, можно вернуться к шагу."""
    label = phase_label(phase)
    return (
        "Подготовка A/B теста\n\n"
        f"Текущий шаг: {label}\n\n"
        "Черновик текущего шага сохранён. Нажмите «Открыть текущий шаг», "
        "чтобы продолить с того же места."
    )


def build_cancel_dialog_text(*, step: ConfirmStep | str) -> str:
    """Текст поддиалога Cancel (§8)."""
    step_val = str(step)
    if step_val == ConfirmStep.S1B.value:
        return (
            "Отменить изменение набора ключей?\n\n"
            "Черновик правок будет утрачен. Подтверждённый набор и таймер "
            "прогрева останутся без изменений."
        )
    return (
        "Отменить запуск A/B теста?\n\n"
        "Черновик текущего шага будет утрачен, режим останется выключен."
    )


def build_s1_text(
    *,
    keywords: list[str],
    page: int,
    total_pages: int,
    draft: dict[str, Any],
    is_s1b: bool = False,
    freeze_banner: str | None = None,
) -> str:
    """S1 / S1b — подтверждение набора ключей (storyboard §S1)."""
    header = (
        "Изменение набора ключей во время прогрева\n\n"
        "Подтверждение этого набора перезапустит таймер прогрева с нуля.\n\n"
        if is_s1b
        else ""
    )
    page_line = f"Подтверждение набора ключей для A/B теста (стр. {page + 1}/{total_pages})\n\n"
    body = (
        "Ниже — ключи, прошедшие проверку (pay_for_order ≤ план max CPO, "
        "≥100 показов). Отметьте, какие ключи войдут в тест. Новые ключи не "
        "добавляются автоматически, а исключённые вручную не возвращаются "
        "автоматически, пока идёт этот шаг и последующий прогрев.\n\n"
    )
    lines: list[str] = []
    for kw in keywords:
        included = draft.get("keyword_included", {}).get(kw, True)
        mark = "✅" if included else "❌"
        hint = "[нажать, чтобы исключить]" if included else "[нажать, чтобы включить]"
        suffix = " (исключена вручную)" if not included else ""
        lines.append(f"{mark} {kw}{suffix} {hint}")
    freeze = f"\n\n{freeze_banner}" if freeze_banner else ""
    return header + page_line + body + "\n".join(lines) + freeze


def build_s2_text(*, duration_hours: int) -> str:
    """S2 — конфигурация длительности WARM_UP (storyboard §S2)."""
    return (
        "Длительность прогрева (WARM_UP)\n\n"
        "По умолчанию — 24 часа (минимум). Вы можете увеличить длительность, "
        "но не можете уменьшить её ниже 24 часов.\n\n"
        "Пороги «≥100 показов на ключ» и «≥1000 показов по кампании» — "
        "это условия допуска ключа/кампании к тесту, а не длительность "
        "прогрева: они не заменяют и не сокращают 24-часовой таймер.\n\n"
        f"Текущий выбор: {duration_hours} часов"
    )


def format_warmup_remaining(
    started_at: datetime.datetime | None,
    duration_hours: int,
    *,
    now: datetime.datetime | None = None,
) -> str:
    """Оставшееся время WARM_UP для S3."""
    if started_at is None:
        return f"≈ {duration_hours} ч (из {duration_hours} ч)"
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    if is_warmup_elapsed(started_at, duration_hours, now=now):
        return "завершён"
    elapsed = now - started_at
    total = datetime.timedelta(hours=int(duration_hours))
    remaining = total - elapsed
    if remaining.total_seconds() <= 0:
        return "завершён"
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return f"≈ {hours} ч {minutes} мин (из {duration_hours} ч)"


def build_s3_text(
    *,
    started_at: datetime.datetime | None,
    duration_hours: int = DEFAULT_WARMUP_HOURS,
    freeze_banner: str | None = None,
) -> str:
    """S3 — прогресс WARM_UP (storyboard §S3)."""
    remaining = format_warmup_remaining(started_at, duration_hours)
    freeze = (
        f"\n\n{freeze_banner}"
        if freeze_banner
        else ""
    )
    return (
        f"Прогрев идёт: осталось {remaining}\n\n"
        "Во время прогрева: без автоматического добавления новых ключей и без "
        "автоматического возврата исключённых; целевая позиция ещё не "
        "фиксируется. Защитное исключение ключа при риске перерасхода "
        "по-прежнему возможно."
        f"{freeze}\n\n"
        "Статистика иногда временно недоступна или устаревает — в эти моменты "
        "бот не меняет состав ключей и ставки «наугад»; тест продолжается. "
        "Вы следите за ходом теста.\n\n"
        "Суточный бюджет кампании продолжает работать как обычно (порог "
        "остановки, не жёсткий лимит; без гарантированной границы перерасхода; "
        "сброс на следующие сутки)."
    )


def build_w3_propose_text(
    *,
    rows: list[tuple[str, int, int]],
    page: int,
    total_pages: int,
    exclusions: list[tuple[str, str]] | None = None,
) -> str:
    """W3-propose — факт vs цель и причины исключения ключей.

    Args:
        rows: ключи с finite positive factual position.
        page: текущая страница валидного набора.
        total_pages: общее число страниц валидного набора.
        exclusions: ключи, исключённые до подтверждения, с user-facing reason.

    Returns:
        Текст в пределах лимита Telegram; если все причины исключения не
        помещаются, сохраняется начало списка и добавляется уведомление.
    """
    header = (
        f"Подтверждение целевых позиций (стр. {page + 1}/{total_pages})\n\n"
        "По каждому ключу показаны два отдельных значения: факт (текущая "
        "наблюдаемая позиция) и предложенная цель (рассчитана по факт-позиции "
        "после прогрева). Совпадение чисел после округления — не повод считать "
        "поля одним значением.\n\n"
    )
    lines: list[str] = []
    for keyword, fact, target in rows:
        match_note = ""
        if fact == target:
            match_note = " (совпали после округления — это два разных поля)"
        lines.append(
            f"{keyword}\n  факт: {fact}   →   предложенная цель: {target}{match_note}"
        )
    body = "\n".join(lines)
    if not rows:
        body = "Нет валидных ключей для подтверждения."
    if exclusions:
        body = _append_w3_exclusions(
            base_text=header + body,
            exclusions=exclusions,
        )
        return body
    return header + body


def _append_w3_exclusions(
    *,
    base_text: str,
    exclusions: list[tuple[str, str]],
) -> str:
    """Добавить причины исключений в доступный Telegram-бюджет.

    Сначала проверяется полный список. При переполнении сохраняется
    детерминированный префикс списка, включая первую помещающуюся запись, и
    добавляется явное уведомление об остальных исключениях.
    """
    section_prefix = f"\n\n{_W3_EXCLUSION_SECTION_TITLE}\n"
    exclusion_lines = [
        f"• {keyword}: исключён — {reason}" for keyword, reason in exclusions
    ]
    full_text = base_text + section_prefix + "\n".join(exclusion_lines)
    if len(full_text) <= const.MAX_MESSAGE_LENGTH:
        return full_text

    omission_suffix = f"\n{_W3_EXCLUSION_OMISSION_NOTICE}"
    if len(base_text + section_prefix + omission_suffix) > const.MAX_MESSAGE_LENGTH:
        return base_text

    visible_lines: list[str] = []
    for line in exclusion_lines:
        candidate = (
            base_text
            + section_prefix
            + "\n".join([*visible_lines, line])
            + omission_suffix
        )
        if len(candidate) > const.MAX_MESSAGE_LENGTH:
            break
        visible_lines.append(line)

    return (
        base_text
        + section_prefix
        + "\n".join(visible_lines)
        + omission_suffix
    )


def build_w3_confirmed_text(
    *,
    rows: list[tuple[str, int, int]],
    page: int,
    total_pages: int,
) -> str:
    """W3-confirmed — read-only зафиксированные цели."""
    header = (
        f"Целевые позиции зафиксированы для текущей эпохи "
        f"(стр. {page + 1}/{total_pages})\n\n"
    )
    lines: list[str] = []
    for keyword, fact, target in rows:
        lines.append(
            f"{keyword}\n  факт: {fact} (текущая, может дрейфовать)   →   "
            f"цель: {target} (зафиксирована)"
        )
    footer = (
        "\n\nДрейф факт-позиции после фиксации не переоткрывает подтверждение "
        "и не пересчитывает цель этой эпохи."
    )
    return header + "\n".join(lines) + footer


def build_a1_text(
    *,
    auto_ctr: float | None = None,
    auto_cpo: float | None = None,
) -> str:
    """A1 — участие Auto (storyboard §Auto participation)."""
    metrics = ""
    if auto_ctr is not None and auto_cpo is not None:
        metrics = (
            f"\n\n[для справки, не как решение] Показатели Auto за последний "
            f"период: CTR {auto_ctr:.1f}%, CPO {auto_cpo:.0f} ₽ — это "
            "информация, а не автоматическое решение; выбор ниже принимаете вы."
        )
    return (
        "Участие Auto в тесте\n\n"
        "Search-ключи и целевые позиции уже подтверждены отдельно — это не "
        "подразумевает решение по Auto. Подтвердите отдельно: участвует ли "
        f"реклама типа Auto в этой эпохе теста.{metrics}"
    )


def build_a2_text(*, auto_bid: float) -> str:
    """A2 — подтверждение ставки Auto."""
    return (
        "Ставка Auto для этой эпохи\n\n"
        "Отдельно от участия Auto подтвердите ставку. После перехода в активный "
        "hold обычное автообновление ставки Auto не будет менять подтверждённое "
        "здесь значение до новой эпохи (после отключения и повторного включения "
        "теста, либо после изменения набора ключей во время прогрева).\n\n"
        f"Ставка Auto: {auto_bid:.0f} ₽"
    )


def build_p1_text() -> str:
    """P1 — синхронизация WB в процессе."""
    return (
        "Синхронизация с Wildberries\n\n"
        "Все подтверждения получены. Параметры этой эпохи сохранены. "
        "Выполняется однократная синхронизация с Wildberries. Режим станет "
        "активным только после полного успеха синхронизации."
    )


def build_p2_text() -> str:
    """P2 — частичная синхронизация."""
    return (
        "Синхронизация выполнена частично\n\n"
        "Часть подтверждённых параметров применена в Wildberries, часть — ещё нет. "
        "Режим пока не активен. Повторная попытка использует те же параметры этой "
        "же эпохи без пересчёта целевых позиций и ставки Auto и без создания "
        "новой эпохи."
    )


def build_h1_text(*, degraded: bool = False) -> str:
    """H1 — активный hold."""
    if degraded:
        lead = (
            "A/B Hold активен (режим деградации: часть enforcement может быть "
            "ограничена — см. статус кампании)."
        )
    else:
        lead = (
            "A/B Hold активен\n\n"
            "Можно запускать A/B-тест: набор ключей и целевые позиции зафиксированы, "
            "биддер продолжает работать к подтверждённым целям."
        )
    return (
        f"{lead}\n\n"
        "Auto-ставка и участие зафиксированы на эту эпоху. Структурные изменения "
        "(whitelist, разгон, пересчёт минус-фраз) заморожены на время hold.\n\n"
        "Статистика иногда временно недоступна или устаревает — в эти моменты "
        "бот не меняет состав ключей и ставки «наугад»; тест продолжается. "
        "Вы следите за ходом теста.\n\n"
        "Суточный бюджет кампании продолжает работать как обычно (порог "
        "остановки, не жёсткий лимит; сброс на следующие сутки; без "
        "гарантированной границы перерасхода)."
    )
