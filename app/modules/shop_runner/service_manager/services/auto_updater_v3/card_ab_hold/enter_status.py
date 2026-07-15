"""Статус-текст после ENTER (poll LastAbort / PG mode).

Вынесено для unit-тестов enable UX без Telegram Runtime.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    is_ab_hold_ready_for_tests,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldSetupBlockKind,
    normalize_card_ab_hold_mode,
)

_GENERIC_PENDING_LINE = (
    "Подготовка… setup на ближайшем тике shop-runner "
    "(ordinary V3 прервётся до apply)."
)


def setup_block_reason_line(
    block_kind: CardAbHoldSetupBlockKind | str | None,
) -> str | None:
    """Actionable строка причины детерминированного блока setup (decision §14b).

    Возвращает конкретную причину + действие для PENDING_SETUP, когда setup не может
    прогрессировать по детерминированной причине (spec «PENDING_SETUP setup blockers
    are surfaced and recoverable»). ``None`` — причина транзиентная / неизвестная, и
    допустим generic «Подготовка…».

    Args:
        block_kind: причина блока из Redis-канала ``CardAbHoldSetupBlock`` или None.
    """
    if block_kind is None:
        return None
    try:
        kind = CardAbHoldSetupBlockKind(str(block_kind))
    except ValueError:
        return None
    if kind == CardAbHoldSetupBlockKind.MISSING_MAX_CPO:
        return (
            "Setup приостановлен: не задан положительный план max CPO. "
            "Задайте план (макс. CPO) в настройках РК — setup продолжится "
            "автоматически — или отключите A/B Hold."
        )
    if kind == CardAbHoldSetupBlockKind.EMPTY_ALLOWED_SET:
        return (
            "Setup приостановлен: нет подходящих ключей для теста "
            "(все ключи исключены/BAD). Проверьте ключи и статистику РК "
            "или отключите A/B Hold."
        )
    return None


def build_enter_poll_status_lines(
    *,
    mode: CardAbHoldMode | str | None,
    abort_safe: bool | None,
    abort_can_continue: bool | None,
    degraded: bool = False,
    block_kind: CardAbHoldSetupBlockKind | str | None = None,
) -> str:
    """Собрать строки статуса после poll LastAbort / ACTIVE.

    Spec card-ab-hold-mode: «можно запускать A/B» только при ACTIVE (decision §8).
    PENDING / «запрос принят» без ACTIVE — не ready-to-test.

    Args:
        mode: durable A/B Hold mode кампании.
        abort_safe: LastAbort safe-флаг (ordinary updater остановлен безопасно).
        abort_can_continue: LastAbort can-continue флаг.
        degraded: честная деградация hold (decision §8, spec scenario «Enforcement
            exceeding the WB minus cap degrades visibly»). При ACTIVE + degraded UI
            MUST NOT заявлять чистый hold — вместо ready-текста отдаётся честный
            статус, что чистота фиксации не гарантируется.
        block_kind: детерминированная причина блока setup (decision §14b). При
            PENDING_SETUP с известной причиной статус показывает конкретную причину
            и действие вместо generic «Подготовка…» — кампания не должна молча
            висеть в вечном PENDING (spec «PENDING_SETUP setup blockers are surfaced
            and recoverable»).
    """
    m = normalize_card_ab_hold_mode(mode)
    lines = [f"Статус: {m.value}"]
    if abort_safe is True and abort_can_continue is True:
        lines.append(
            "Ordinary updater остановлен безопасно — setup может продолжаться."
        )
    if is_ab_hold_ready_for_tests(m):
        lines.append("Setup завершён, режим ACTIVE (HOLD).")
        if degraded:
            lines.append(
                "Внимание: чистота фиксации набора фраз не гарантируется для этой РК "
                "(превышен лимит минус-слов WB или открытый матчинг) — "
                "результаты A/B-теста могут быть неточными."
            )
        else:
            lines.append(
                "Можно запускать A/B-тесты: набор фраз и целевые позиции зафиксированы."
            )
    elif m == CardAbHoldMode.PENDING_SETUP:
        block_line = setup_block_reason_line(block_kind)
        lines.append(block_line if block_line is not None else _GENERIC_PENDING_LINE)
        lines.append(
            "Пока статус не ACTIVE — не запускайте A/B-тест: "
            "набор фраз ещё не зафиксирован."
        )
    return "\n".join(lines)
