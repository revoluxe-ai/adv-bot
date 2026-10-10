"""Task 4.2A: configured/effective Telegram surface and dry-run previews."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ControlPathKind,
    HierarchicalEnrollment,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ResolverContext,
    ShopFeatureSlot,
)
from app.modules.ad_control_settings.telegram.callbacks import AdcPrev
from app.modules.ad_control_settings.telegram.context import build_settings_context
from app.modules.ad_control_settings.ui.dry_run_preview import (
    preview_clear_to_inherit,
    preview_disable,
    preview_override_from_shop_payload,
    validate_ad_control_changeset,
)
from app.modules.ad_control_settings.ui.format import (
    format_campaign_detail,
    format_dry_run,
    format_shop_screen,
)
from app.modules.ad_control_settings.ui.labels import feature_from_code
from app.modules.ad_control_settings.ui.view_models import (
    FeatureControlLine,
    describe_campaign_features,
    describe_shop_features,
    summarize_campaign_modes,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent
from app.modules.shop_menu.message import build_shop_main_keyboard
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    AdControlCampaignFeatureSnapshotV1,
    AdControlValidationResult,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetV1,
    ClearCampaignAdControlFeatureOperation,
)

_ROOT = Path(__file__).resolve().parents[3]
_UI_ROOTS = (
    _ROOT / "app/modules/ad_control_settings/ui",
    _ROOT / "app/modules/ad_control_settings/telegram",
)
_BANNED = (
    "apply_shop_mutation",
    "apply_campaign_override",
    "apply_campaign_disable",
    "clear_campaign_feature",
    "ApplyAuthority",
    "wb_manager",
    "WildberriesAPI",
    "ActualDrrObservation",
    "ShopHeadroomState",
    "BoundedCpoProposal",
    "evaluate_shop_headroom_state",
)


def _drr(target: str, maximum: str) -> DrrPolicyParamsV1:
    return DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal(target), Decimal(maximum)),
    )


def _enrolled(
    shop: dict[AdControlFeatureId, ShopFeatureSlot],
    campaign: dict[AdControlFeatureId, CampaignFeatureSlot],
    *,
    advert_id: int = 4242,
) -> ResolverContext:
    return ResolverContext(
        enrollment=HierarchicalEnrollment.ENROLLED,
        control_path=ControlPathKind.HIERARCHICAL,
        shop_id="shop-1",
        shop_features=shop,
        campaign=CampaignRef(shop_id="shop-1", advert_id=advert_id),
        campaign_features=campaign,
    )


def _shop_slot(payload: DrrPolicyParamsV1 | None) -> ShopFeatureSlot:
    if payload is None:
        return ShopFeatureSlot(activation=ShopFeatureActivation.DISABLED, payload=None)
    return ShopFeatureSlot(activation=ShopFeatureActivation.ENABLED, payload=payload)


def _line(context: ResolverContext) -> FeatureControlLine:
    lines = describe_campaign_features(context)
    return next(
        line for line in lines if line.feature_id == AdControlFeatureId.DRR_POLICY
    )


@pytest.mark.unit
def test_shop_settings_render_all_registry_features() -> None:
    lines = describe_shop_features({})
    text = format_shop_screen(shop_id="shop-1", lines=lines)
    assert "shop_id: shop-1" in text
    assert "RUNTIME_ECONOMICS_NOT_AVAILABLE" in text
    for feature_id in (
        AdControlFeatureId.DRR_POLICY,
        AdControlFeatureId.DYNAMIC_DRR_CONTROL,
        AdControlFeatureId.CPO_INCREASE_ON_HEADROOM,
        AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND,
        AdControlFeatureId.CPO_SAFETY_BOUNDS,
    ):
        assert feature_id.value in text
    assert all(line.activation == ShopFeatureActivation.DISABLED for line in lines)


@pytest.mark.unit
def test_campaign_text_uses_advert_id_not_nmid() -> None:
    context = _enrolled({}, {})
    text = format_campaign_detail(
        shop_id="shop-1",
        advert_id=4242,
        name="label-only",
        lines=describe_campaign_features(context),
    )
    assert "advert_id: 4242" in text
    assert "DRR_POLICY=INHERIT" in summarize_campaign_modes({})
    assert "nmId" not in text
    assert "main_nmid" not in text


@pytest.mark.unit
def test_inherit_override_disabled_and_provenance() -> None:
    shop_payload = _drr("15", "20")
    override_payload = _drr("9", "12")
    inherited = _line(
        _enrolled(
            {AdControlFeatureId.DRR_POLICY: _shop_slot(shop_payload)},
            {},
        )
    )
    assert inherited.campaign_mode == AdControlFeatureMode.INHERIT
    assert inherited.campaign_payload_text == "—"
    assert "15" in inherited.effective_text
    assert inherited.provenance_text == "SHOP_POLICY/SHOP"
    assert inherited.blocked is False

    overridden = _line(
        _enrolled(
            {AdControlFeatureId.DRR_POLICY: _shop_slot(shop_payload)},
            {
                AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                    mode=AdControlFeatureMode.OVERRIDE,
                    payload=override_payload,
                )
            },
        )
    )
    assert overridden.campaign_mode == AdControlFeatureMode.OVERRIDE
    assert "9" in overridden.campaign_payload_text
    assert "15" not in overridden.effective_text
    assert overridden.provenance_text == "CAMPAIGN_OVERRIDE/CAMPAIGN"

    disabled = _line(
        _enrolled(
            {AdControlFeatureId.DRR_POLICY: _shop_slot(shop_payload)},
            {
                AdControlFeatureId.DRR_POLICY: CampaignFeatureSlot(
                    mode=AdControlFeatureMode.DISABLED,
                    payload=None,
                )
            },
        )
    )
    assert disabled.campaign_mode == AdControlFeatureMode.DISABLED
    assert disabled.campaign_payload_text == "—"
    assert disabled.effective_text == "inactive"
    assert disabled.provenance_text == "CAMPAIGN_DISABLED/CAMPAIGN"
    assert "FEATURE_DISABLED_AT_CAMPAIGN" in disabled.status_text


@pytest.mark.unit
def test_live_ui_context_fails_closed_when_enrollment_missing() -> None:
    context = build_settings_context(
        shop_id="shop-1",
        advert_id=7,
        shop_features={AdControlFeatureId.DRR_POLICY: _shop_slot(_drr("15", "20"))},
        campaign_features={},
    )
    line = _line(context)
    assert line.campaign_mode == AdControlFeatureMode.INHERIT
    assert line.effective_text == "—"
    assert line.blocked is True
    assert "NOT_ENROLLED_FAIL_CLOSED" in line.status_text


@pytest.mark.unit
def test_clear_to_inherit_is_clear_op_without_shop_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[AdControlChangeSetV1] = []
    real = validate_ad_control_changeset

    def _capture(
        changeset: AdControlChangeSetV1,
        *,
        shop_snapshots: dict[AdControlFeatureId, object],
        campaign_snapshots: dict[tuple[str, int, AdControlFeatureId], object],
    ) -> AdControlValidationResult:
        seen.append(changeset)
        return real(
            changeset,
            shop_snapshots=shop_snapshots,  # type: ignore[arg-type]
            campaign_snapshots=campaign_snapshots,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(
        "app.modules.ad_control_settings.ui.dry_run_preview.validate_ad_control_changeset",
        _capture,
    )
    snap = AdControlCampaignFeatureSnapshotV1(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        mode=AdControlFeatureMode.OVERRIDE,
        payload_json={"kind": "DrrPolicyParamsV1"},
        revision=4,
        state_token="acs_test",
    )
    preview = preview_clear_to_inherit(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        expected_revision=4,
        shop_snapshots={},
        campaign_snapshots={("shop-1", 4242, AdControlFeatureId.DRR_POLICY): snap},
    )
    operation = seen[0].operations[0]  # type: ignore[attr-defined]
    assert isinstance(operation, ClearCampaignAdControlFeatureOperation)
    assert operation.op == "campaign.clear_ad_control_feature"
    dumped = operation.model_dump()
    assert set(dumped["payload"]) == {"feature_id", "schema_version"}
    assert "target_drr" not in str(dumped)
    assert preview.validation_status == "ok"
    assert any("CLEAR_TO_INHERIT" in line for line in preview.diff_lines)
    assert preview.persisted is False
    text = format_dry_run(preview)
    assert text.startswith("PREVIEW / DRY RUN")
    assert "НЕ изменено" in text


@pytest.mark.unit
def test_clear_absent_row_is_no_op() -> None:
    preview = preview_clear_to_inherit(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        expected_revision=None,
        shop_snapshots={},
        campaign_snapshots={},
    )
    assert preview.validation_status == "no_op"
    text = format_dry_run(preview)
    assert "NO_OP" in text
    assert "PREVIEW / DRY RUN" in text


@pytest.mark.unit
def test_revision_conflict_is_shown() -> None:
    snap = AdControlCampaignFeatureSnapshotV1(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        mode=AdControlFeatureMode.DISABLED,
        payload_json=None,
        revision=3,
        state_token="acs_test",
    )
    preview = preview_disable(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        expected_revision=1,
        shop_snapshots={},
        campaign_snapshots={("shop-1", 4242, AdControlFeatureId.DRR_POLICY): snap},
    )
    assert preview.validation_status == "rejected"
    assert any("REVISION_CONFLICT" in line for line in preview.error_lines)
    assert preview.persisted is False


@pytest.mark.unit
def test_override_preview_uses_shop_payload_and_empty_shop_fails_closed() -> None:
    created = preview_override_from_shop_payload(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        expected_revision=None,
        shop_payload=_drr("15", "20"),
        shop_snapshots={},
        campaign_snapshots={},
    )
    assert created.operation == "campaign.set_ad_control_override"
    assert created.validation_status == "ok"
    assert any("OVERRIDE" in line for line in created.diff_lines)
    assert any(
        "не путать" in note.lower() or "OVERRIDE" in note for note in created.notes
    )

    rejected = preview_override_from_shop_payload(
        shop_id="shop-1",
        advert_id=4242,
        feature_id=AdControlFeatureId.DRR_POLICY,
        expected_revision=None,
        shop_payload=None,
        shop_snapshots={},
        campaign_snapshots={},
    )
    assert rejected.validation_status == "rejected"
    assert "NO_CONFIGURED_SHOP_PAYLOAD" in rejected.error_lines


@pytest.mark.unit
def test_unknown_feature_code_fails_closed() -> None:
    assert feature_from_code("nope") is None
    packed = AdcPrev(cab=1, aid=2, f="zz", op="clr").pack()
    assert len(packed.encode("utf-8")) <= 64


@pytest.mark.unit
def test_callback_data_fits_telegram_limit() -> None:
    packed = AdcPrev(cab=2_147_483_647, aid=2_147_483_647, f="dp", op="ovr").pack()
    assert len(packed.encode("utf-8")) <= 64


@pytest.mark.unit
def test_shop_menu_has_ad_control_entry() -> None:
    cabinet = type("C", (), {"id": 9, "user": None, "wb_cabinet": None})()
    wb = type("W", (), {"id": 3, "active": True})()
    keyboard = build_shop_main_keyboard(cabinet, wb)  # type: ignore[arg-type]
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "Рекламный контроль" in texts


@pytest.mark.unit
def test_ui_package_has_no_writes_or_economics() -> None:
    blob = "\n".join(
        path.read_text(encoding="utf-8")
        for root in _UI_ROOTS
        for path in root.rglob("*.py")
    )
    for banned in _BANNED:
        assert banned not in blob
