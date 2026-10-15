"""Процессный брокер MCP без импорта экспортёра на обычном пути бота.

Сборка PostgreSQL/Redis/ExportService происходит только при первом обращении,
когда канал уже включён или тест подменил брокер.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.wb_sky_mcp.broker import McpBroker

_broker: McpBroker | None = None


def set_mcp_broker(broker: McpBroker | None) -> None:
    """Подменить брокер в тестах. ``None`` возвращает ленивую сборку."""
    global _broker
    _broker = broker


def get_mcp_broker() -> McpBroker:
    """Вернуть брокер процесса, собрав его при первом вызове."""
    global _broker
    if _broker is None:
        from app.modules.wb_sky_mcp.config import load_mcp_config
        from app.modules.wb_sky_mcp.http import build_production_broker

        _broker = build_production_broker(load_mcp_config())
    return _broker
