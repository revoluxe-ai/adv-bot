"""Authoritative ``WBCabinet.shop_id`` для AI Package v1 без числового coercion.

PG хранит идентификатор магазина как ``str`` (UUID и иные валидные значения).
Manifest, dataset rows, PACKAGE_SUMMARY и keyword payloads обязаны нести ту же
строку. Отдельный numeric/hash surrogate запрещён.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator


def require_authoritative_shop_id(value: object) -> str:
    """
    Принимает только непустую строку и возвращает её без нормализации.

    Args:
        value: Кандидат shop identity (JSON, модель или вход export).

    Returns:
        Та же строка, что пришла, включая значимые символы.

    Raises:
        ValueError: не-str (в том числе int), пустая или whitespace-only строка.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError(
            "shop_id must be an authoritative string; numeric coercion is forbidden"
        )
    if value.strip() == "":
        raise ValueError("shop_id must be a non-blank authoritative string")
    return value


AuthoritativeShopId = Annotated[str, BeforeValidator(require_authoritative_shop_id)]


def manifest_shop_id(pg_shop_id: str) -> str:
    """
    Возвращает authoritative PG ``shop_id`` для manifest и payload rows.

    Не приводит десятичные строки к ``int`` и не обрезает идентификатор:
    whitespace внутри или по краям легитимного значения сохраняется.
    Пустая строка fail-closed.

    Args:
        pg_shop_id: Значение ``WBCabinet.shop_id``.

    Returns:
        Та же строка.

    Raises:
        ValueError: пустой идентификатор или попытка передать не-str.
    """
    return require_authoritative_shop_id(pg_shop_id)
