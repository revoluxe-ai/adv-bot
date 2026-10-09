"""
DTO-источники для проектора и адаптер ComplexAdv (read-only).

Search physical adv id берётся только из paired ``search_adv.adv_id``,
не из ``AdvSetting.search_adv_id`` (linkage).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.product_control.domain.enums import LegRole

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.complex_adv import (
        ComplexAdv,
    )


@dataclass(frozen=True, slots=True)
class AdvLegProjectionSource:
    """Одна физическая нога для проекции binding."""

    adv_setting_id: int
    physical_adv_id: int | None
    leg_role: LegRole
    nmids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ComplexAdvProjectionSource:
    """Комплекс Auto (+ optional Search) без runtime mutation."""

    shop_id: str | None
    auto_leg: AdvLegProjectionSource
    search_leg: AdvLegProjectionSource | None
    search_linkage_adv_id: int | None = None


def _shop_id_from_complex(complex_adv: ComplexAdv) -> str | None:
    explicit = complex_adv.shop_id
    if explicit:
        return explicit
    cabinet = getattr(complex_adv._adv_setting, "wb_cabinet", None)
    if cabinet is not None:
        sid = getattr(cabinet, "shop_id", None)
        if sid:
            return str(sid)
    return None


def _nmids_tuple(raw: list[int] | None) -> tuple[int, ...]:
    if not raw:
        return ()
    return tuple(sorted(dict.fromkeys(raw)))


def complex_adv_to_projection_source(complex_adv: ComplexAdv) -> ComplexAdvProjectionSource:
    """Собрать projection source из runtime ComplexAdv (read-only)."""
    auto_setting = complex_adv._adv_setting
    auto_leg = AdvLegProjectionSource(
        adv_setting_id=int(auto_setting.id),
        physical_adv_id=int(auto_setting.adv_id) if auto_setting.adv_id else None,
        leg_role=LegRole.AUTO,
        nmids=_nmids_tuple(list(auto_setting.nmids or [])),
    )
    search_leg: AdvLegProjectionSource | None = None
    search_setting = complex_adv.search_adv
    if search_setting is not None:
        search_leg = AdvLegProjectionSource(
            adv_setting_id=int(search_setting.id),
            physical_adv_id=(
                int(search_setting.adv_id) if search_setting.adv_id else None
            ),
            leg_role=LegRole.SEARCH,
            nmids=_nmids_tuple(list(search_setting.nmids or [])),
        )
    linkage_id = getattr(auto_setting, "search_adv_id", None)
    return ComplexAdvProjectionSource(
        shop_id=_shop_id_from_complex(complex_adv),
        auto_leg=auto_leg,
        search_leg=search_leg,
        search_linkage_adv_id=int(linkage_id) if linkage_id else None,
    )


def project_complex_adv(complex_adv: ComplexAdv):
    """Удобная обёртка: ComplexAdv → результат проектора."""
    from app.modules.product_control.application.projection.campaign_binding_projector import (
        CampaignProductBindingProjector,
    )

    source = complex_adv_to_projection_source(complex_adv)
    return CampaignProductBindingProjector.project_complex(source)
