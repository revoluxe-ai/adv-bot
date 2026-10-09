"""Контракт CampaignProductBinding (vocabulary Slice A; проектор — Slice B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.product_control.domain.enums import LegRole, MembershipRole


@dataclass(frozen=True, slots=True)
class MembershipEvidence:
    """
    Явное evidence для роли membership.

    ``main_nmid`` и сортировка nmids не являются authority и не должны
    заполнять это поле без отдельной политики проектора.
    """

    source: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignProductBinding:
    """
    Связь nmID с физической ногой кампании.

    ``adv_setting_id`` — логическая ссылка на AdvSetting/комплекс в PG.
    ``physical_adv_id`` — WB physical adv id для конкретной ноги.
    """

    shop_id: str
    nmid: int
    physical_adv_id: int
    adv_setting_id: int
    leg_role: LegRole
    membership_role: MembershipRole
    membership_evidence: MembershipEvidence | None
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    def __post_init__(self) -> None:
        if self.membership_role == MembershipRole.PRIMARY:
            if self.membership_evidence is None:
                raise ValueError(
                    "PRIMARY membership_role requires explicit membership_evidence"
                )
