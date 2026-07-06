"""Static guard against direct bot_active toggles outside transition helpers."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_APP_ROOT = _REPO_ROOT / "app"
_TRANSITION_HELPERS = {
    _APP_ROOT / "client_bot" / "user_interface" / "services" / "auto_management_mode.py",
    _APP_ROOT / "client_bot" / "modules" / "default_settings" / "adv_setting_policy" / "__init__.py",
}
_BILLING_MODULE = _APP_ROOT / "modules" / "billing" / "billing.py"


def _is_direct_bot_active_bool_assignment(node: ast.Assign | ast.AnnAssign) -> bool:
    if isinstance(node, ast.Assign):
        value = node.value
        targets = node.targets
    else:
        value = node.value
        targets = [node.target]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, bool):
        return False
    return any(
        isinstance(target, ast.Attribute) and target.attr == "bot_active"
        for target in targets
    )


def test_business_code_does_not_assign_bot_active_directly() -> None:
    offenders: list[str] = []
    for path in _APP_ROOT.rglob("*.py"):
        if path in _TRANSITION_HELPERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and _is_direct_bot_active_bool_assignment(node):
                offenders.append(
                    f"{path.relative_to(_REPO_ROOT)}:{getattr(node, 'lineno', '?')}"
                )

    assert offenders == [], (
        "Use apply_paid_auto_management_transition/apply_free_mode_transition "
        f"instead of direct bot_active assignment: {offenders}"
    )


def test_billing_auto_disable_uses_free_transition_helper() -> None:
    tree = ast.parse(_BILLING_MODULE.read_text(encoding="utf-8-sig"), filename=str(_BILLING_MODULE))
    helper_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "apply_free_mode_transition"
    ]

    assert helper_calls, "billing auto-disable must use apply_free_mode_transition(...)"
