"""DTO scope export: Auto/Search adv_id и main_nmid без shop-runner ComplexAdv."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExportScopeAdv:
    """
    Минимальный in-process scope вместо ``ComplexAdv`` (тот тянет WB API DTO).

    Сохраняет отдельные идентичности auto ``adv_id`` и search ``adv_id``;
    ``main_nmid`` может быть ``None`` при пустых ``nmids`` (incomplete inventory).
    """

    shop_id: str
    auto_adv_id: int
    search_adv_id: int | None
    main_nmid: int | None
    name: str
    active_status: str
    bot_active: bool
