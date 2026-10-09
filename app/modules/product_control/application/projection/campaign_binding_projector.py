"""
Read-only проектор CampaignProductBinding из PG-shaped campaign legs.

Не использует main_nmid, search_adv_id linkage как physical Search id, или nmids[0].
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.product_control.application.projection.membership_policy import (
    normalize_leg_nmids,
    resolve_leg_membership_role,
)
from app.modules.product_control.application.projection.sources import (
    AdvLegProjectionSource,
    ComplexAdvProjectionSource,
)
from app.modules.product_control.domain.bindings import CampaignProductBinding
from app.modules.product_control.domain.enums import LegRole


@dataclass(frozen=True, slots=True)
class LegProjectionIssue:
    """Fail-closed проблема на одной ноге (без утечки cross-shop)."""

    leg_role: LegRole
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class BindingProjectionResult:
    """Детерминированный результат проекции комплекса."""

    bindings: tuple[CampaignProductBinding, ...]
    issues: tuple[LegProjectionIssue, ...]


class CampaignProductBindingProjector:
    """Проецирует bindings для Auto и Search как отдельных physical legs."""

    @staticmethod
    def project_complex(
        source: ComplexAdvProjectionSource,
    ) -> BindingProjectionResult:
        shop_id = source.shop_id
        if not shop_id:
            return BindingProjectionResult(
                bindings=(),
                issues=(
                    LegProjectionIssue(
                        leg_role=LegRole.AUTO,
                        code="SHOP_ID_MISSING",
                        detail="shop_id unresolved for complex",
                    ),
                ),
            )

        bindings: list[CampaignProductBinding] = []
        issues: list[LegProjectionIssue] = []

        auto_bindings, auto_issues = CampaignProductBindingProjector._project_leg(
            shop_id,
            source.auto_leg,
        )
        bindings.extend(auto_bindings)
        issues.extend(auto_issues)

        if source.search_leg is not None:
            search_bindings, search_issues = (
                CampaignProductBindingProjector._project_leg(
                    shop_id,
                    source.search_leg,
                )
            )
            bindings.extend(search_bindings)
            issues.extend(search_issues)
        elif source.search_linkage_adv_id is not None:
            issues.append(
                LegProjectionIssue(
                    leg_role=LegRole.SEARCH,
                    code="SEARCH_LEG_UNRESOLVED",
                    detail=(
                        "search_adv_id linkage present but paired Search "
                        "AdvSetting missing"
                    ),
                )
            )

        ordered = tuple(
            sorted(
                bindings,
                key=lambda b: (b.leg_role.value, b.physical_adv_id, b.nmid),
            )
        )
        return BindingProjectionResult(bindings=ordered, issues=tuple(issues))

    @staticmethod
    def _project_leg(
        shop_id: str,
        leg: AdvLegProjectionSource,
    ) -> tuple[list[CampaignProductBinding], list[LegProjectionIssue]]:
        issues: list[LegProjectionIssue] = []
        if leg.physical_adv_id is None:
            issues.append(
                LegProjectionIssue(
                    leg_role=leg.leg_role,
                    code="PHYSICAL_ADV_ID_MISSING",
                    detail="physical_adv_id required for binding",
                )
            )
            return [], issues

        unique_nmids = normalize_leg_nmids(leg.nmids)
        if not unique_nmids:
            issues.append(
                LegProjectionIssue(
                    leg_role=leg.leg_role,
                    code="LEG_NMIDS_EMPTY",
                    detail="no nmids on leg",
                )
            )
            return [], issues

        role, evidence = resolve_leg_membership_role(unique_nmids)
        bindings = [
            CampaignProductBinding(
                shop_id=shop_id,
                nmid=nmid,
                physical_adv_id=leg.physical_adv_id,
                adv_setting_id=leg.adv_setting_id,
                leg_role=leg.leg_role,
                membership_role=role,
                membership_evidence=evidence,
            )
            for nmid in unique_nmids
        ]
        return bindings, issues

