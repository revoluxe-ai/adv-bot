"""Writer adapter safety boundary tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from app.modules.common_slaves.wildberries.models.models import AdvSetting

from app.modules.wb_sky_control_plane.apply.writer.pg_campaign_settings_policy_v1 import (
    apply_plan_to_adv_settings,
)
from app.modules.wb_sky_control_plane.models.plan import PlanEffectV1, PlanV1, SemanticDiffEntryV1

pytestmark = pytest.mark.unit


def test_writer_rejects_wrong_bucket_in_field_path() -> None:
    row = SimpleNamespace(auto_budget_daily_limit=1)
    plan = PlanV1(
        effects=[
            PlanEffectV1(
                resource_id="cmp_x",
                operation="campaign.set_budget_policy",
                operation_index=0,
                semantic_changes=[
                    SemanticDiffEntryV1(
                        field_path="cmp_x.sales.auto_budget_daily_limit",
                        resource_id="cmp_x",
                        current=1,
                        desired=2,
                        normalized=2,
                        intent="set",
                    )
                ],
            )
        ]
    )
    with pytest.raises(ValueError, match="bucket"):
        apply_plan_to_adv_settings(
            plan,
            adv_by_resource=cast(dict[str, AdvSetting], {"cmp_x": row}),
        )


def test_writer_rejects_no_op_effect() -> None:
    plan = PlanV1(
        effects=[
            PlanEffectV1(
                resource_id="cmp_x",
                operation="campaign.set_budget_policy",
                operation_index=0,
                is_no_op=True,
                semantic_changes=[],
            )
        ]
    )
    with pytest.raises(ValueError, match="NO_OP"):
        apply_plan_to_adv_settings(
            plan,
            adv_by_resource=cast(
                dict[str, AdvSetting], {"cmp_x": SimpleNamespace()}
            ),
        )
