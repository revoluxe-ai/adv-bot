"""JSON-safe сериализация ответов WB stack для raw JSONL."""

from __future__ import annotations

from typing import Any, cast


def jsonable(value: object) -> object:
    """Привести ответ менеджера/adapter к JSON-safe структуре."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        try:
            return jsonable(value.model_dump(mode="json"))
        except TypeError:
            return jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        try:
            return jsonable(value.to_dict())
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, list):
        return [jsonable(v) for v in cast(list[object], value)]
    if isinstance(value, tuple):
        return [jsonable(v) for v in cast(tuple[object, ...], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {str(k): jsonable(v) for k, v in mapping.items()}
    raw_dict = getattr(value, "__dict__", None)
    if isinstance(raw_dict, dict):
        mapping2 = cast(dict[str, object], raw_dict)
        return {
            k: jsonable(v) for k, v in mapping2.items() if not k.startswith("_")
        }
    return str(value)
