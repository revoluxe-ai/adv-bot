"""Regression: check_subscribe must not re-answer CallbackQuery.

Policy (``app/client_bot/callback_helpers.py``, ``docks/CALLBACK_ANSWER_POLICY.md``):
``ImmediateCallbackAnswerUpdateMiddleware`` on Dispatcher already ACKs callbacks.
Handlers must not call ``callback.answer()``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_HANDLER = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "client_bot"
    / "user_interface"
    / "handlers"
    / "user_subscribe_on_channel.py"
)

_CALLBACK_QUERY_NAMES = frozenset({"query", "callback"})


def _callback_query_answer_sites(source: str) -> list[tuple[int, str]]:
    """Collect ``query.answer`` / ``callback.answer`` call sites (not message.answer)."""
    tree = ast.parse(source)
    sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "answer":
            continue
        if isinstance(func.value, ast.Name) and func.value.id in _CALLBACK_QUERY_NAMES:
            sites.append((node.lineno, f"{func.value.id}.answer"))
    return sites


@pytest.mark.unit
def test_check_subscribe_must_not_call_callback_query_answer() -> None:
    """``check_subscribe`` не должен вызывать ``CallbackQuery.answer``."""
    assert _HANDLER.is_file(), f"missing {_HANDLER}"
    source = _HANDLER.read_text(encoding="utf-8")
    sites = _callback_query_answer_sites(source)
    assert sites == [], (
        "Policy: ImmediateCallbackAnswerUpdateMiddleware already answers "
        "CallbackQuery; handlers must NOT call callback.answer(). "
        f"Found {len(sites)} call site(s) in user_subscribe_on_channel.py: "
        f"{sites[:12]}{'...' if len(sites) > 12 else ''}"
    )
