"""Статус-текст после ENTER (poll LastAbort / PG mode).

Вынесено для unit-тестов enable UX без Telegram Runtime.
"""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.minus_freeze import (
    is_ab_hold_ready_for_tests,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)


def build_enter_poll_status_lines(
    *,
    mode: CardAbHoldMode | str | None,
    abort_safe: bool | None,
    abort_can_continue: bool | None,
    degraded: bool = False,
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
        lines.append(
            "Подготовка… setup на ближайшем тике shop-runner "
            "(ordinary V3 прервётся до apply)."
        )
        lines.append(
            "Пока статус не ACTIVE — не запускайте A/B-тест: "
            "набор фраз ещё не зафиксирован."
        )
    return "\n".join(lines)
