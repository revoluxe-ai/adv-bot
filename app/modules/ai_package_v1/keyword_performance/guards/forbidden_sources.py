"""Verify export path does not import forbidden UI/Telegram keyword sources."""

from __future__ import annotations

import importlib
import sys


FORBIDDEN_MODULES = (
    "app.modules.wb_adv_updater.keyword_daily_history.keyword_daily_history_manager",
    "app.utils.graphic_positions_creator.graphic_positions_creator",
)


def assert_forbidden_sources_not_loaded() -> None:
    """Raise if forbidden modules are imported on export path."""
    loaded = set(sys.modules.keys())
    for mod in FORBIDDEN_MODULES:
        if mod in loaded:
            raise RuntimeError(f"forbidden source imported on export path: {mod}")


def assert_module_not_importable_as_authority(module_path: str) -> bool:
    """Return False if module exists and is the forbidden authority."""
    try:
        _ = importlib.import_module(module_path)
    except ImportError:
        return True
    return module_path not in FORBIDDEN_MODULES
