"""Ревизии MCP, которые заявляет read-only адаптер WB Sky.

Канонический список — ``SUPPORTED_PROTOCOL_VERSIONS``. Сейчас это только
Streamable HTTP ревизия ``2025-03-26``. Сессия (``Mcp-Session-Id``) не
выдаётся: в этой ревизии она необязательна, сервер остаётся stateless.
``server/discover`` ревизии ``2026-07-28`` не реализуется.

Согласование версии — по lifecycle ``2025-03-26``: запрошенная поддержанная
ревизия возвращается как есть; любая другая непустая строка получает
последнюю поддержанную ревизию, а не отказ и не эхо чужой версии.
Заголовок ``MCP-Protocol-Version`` на запросах после initialize: отсутствие
означает ``2025-03-26`` (правило совместимости из ревизии ``2025-06-18``,
которым пользуются клиенты, говорящие со старым сервером). Неподдержанное
значение заголовка — HTTP 400. Сам заголовок не добавляет ревизию в список
поддержанных.
"""

from __future__ import annotations

from typing import cast

SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = ("2025-03-26",)


def latest_supported_protocol_version() -> str:
    """Последняя ревизия из канонического списка."""
    return SUPPORTED_PROTOCOL_VERSIONS[-1]


def negotiate_protocol_version(params: object) -> str:
    """Согласовать ``initialize.params.protocolVersion``.

    Args:
        params: Объект ``initialize.params``.

    Returns:
        Ревизия, которую сервер реально будет использовать.

    Raises:
        ValueError: params отсутствуют или не содержат строковую ревизию,
            capabilities и clientInfo.
    """
    if not isinstance(params, dict):
        raise ValueError("invalid params")
    payload = cast(dict[str, object], params)
    version = payload.get("protocolVersion")
    capabilities = payload.get("capabilities")
    client_info = payload.get("clientInfo")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("invalid params")
    if not isinstance(capabilities, dict):
        raise ValueError("invalid params")
    if not isinstance(client_info, dict):
        raise ValueError("invalid params")
    info = cast(dict[str, object], client_info)
    name = info.get("name")
    client_version = info.get("version")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("invalid params")
    if not isinstance(client_version, str) or not client_version.strip():
        raise ValueError("invalid params")
    if version in SUPPORTED_PROTOCOL_VERSIONS:
        return version
    return latest_supported_protocol_version()


def protocol_header_is_supported(header_value: str | None) -> bool:
    """Проверить заголовок ``MCP-Protocol-Version`` на запросе после initialize.

    Отсутствие заголовка допустимо и означает ``2025-03-26``.
    """
    if header_value is None:
        return True
    return header_value in SUPPORTED_PROTOCOL_VERSIONS
