"""Regression ROOT-001: confirm_handlers must not re-answer CallbackQuery.

Policy (app/client_bot/callback_helpers.py, docks/CALLBACK_ANSWER_POLICY.md):
``ImmediateCallbackAnswerUpdateMiddleware`` already answers CallbackQuery on the
Dispatcher. Handlers must not call ``query.answer()`` / ``callback.answer()``.
``query.message.answer`` (chat message) remains allowed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_CONFIRM_HANDLERS = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "modules"
    / "shop_runner"
    / "service_manager"
    / "services"
    / "auto_updater_v3"
    / "card_ab_hold"
    / "telegram"
    / "confirm_handlers.py"
)

_CALLBACK_QUERY_NAMES = frozenset({"query", "callback"})


def _callback_query_answer_sites(source: str) -> list[tuple[int, str]]:
    """Собирает вызовы query.answer / callback.answer (не query.message.answer)."""
    tree = ast.parse(source)
    sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "answer":
            continue
        # Только прямой CallbackQuery.answer: Name(query|callback).answer(...)
        if isinstance(func.value, ast.Name) and func.value.id in _CALLBACK_QUERY_NAMES:
            sites.append((node.lineno, f"{func.value.id}.answer"))
    return sites


@pytest.mark.unit
def test_confirm_handlers_must_not_call_callback_query_answer() -> None:
    """Хендлеры card_ab_hold confirm не должны вызывать CallbackQuery.answer.

    Без фикса AST находит десятки query.answer в confirm_handlers.py — RED для
    ROOT-001 (двойной answer после ImmediateCallbackAnswerUpdateMiddleware).
    """
    assert _CONFIRM_HANDLERS.is_file(), f"missing {_CONFIRM_HANDLERS}"
    source = _CONFIRM_HANDLERS.read_text(encoding="utf-8")
    sites = _callback_query_answer_sites(source)
    assert sites == [], (
        "Policy: ImmediateCallbackAnswerUpdateMiddleware already answers "
        "CallbackQuery; handlers must NOT call query.answer()/callback.answer(). "
        f"Found {len(sites)} CallbackQuery.answer call site(s) in "
        f"confirm_handlers.py: {sites[:12]}{'...' if len(sites) > 12 else ''}"
    )
