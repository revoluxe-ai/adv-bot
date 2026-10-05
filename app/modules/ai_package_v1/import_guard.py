"""Статическая проверка запрещённых импортов в пакете ai_package_v1."""

from __future__ import annotations

import ast
from pathlib import Path

_FORBIDDEN_PREFIXES = (
    "app.core.mp.wb",
    "app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager",
)


def collect_forbidden_imports(package_root: Path) -> list[str]:
    """
    Сканирует ``.py`` файлы пакета на импорты WB API и WBShopDataManager.

    Returns:
        Список строк вида ``path: module`` для каждого нарушения.
    """
    violations: list[str] = []
    for path in sorted(package_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _check(alias.name, path, violations)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    _check(node.module, path, violations)
    return violations


def _check(module: str, path: Path, violations: list[str]) -> None:
    for prefix in _FORBIDDEN_PREFIXES:
        if module == prefix or module.startswith(prefix + "."):
            violations.append(f"{path}: {module}")
