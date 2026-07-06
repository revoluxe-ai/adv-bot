"""PAID mode overlay for explicit auto-management enable."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

from .base_policy import AdvSettingDefaultsPolicy
from .field_policy import FieldPolicy


class PaidModeDefaultsPolicy(AdvSettingDefaultsPolicy):
    """PAID mode overlay for explicit auto-management enable."""

    name = "paid_mode_overlay"

    rules = (
        FieldPolicy(
            field=AdvSetting.automatic_version,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: 3,
            reason="PAID mode: включаем V3 updater.",
        ),
        FieldPolicy(
            field=AdvSetting.bidder_active,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: True,
            reason="PAID mode: bidder активен как часть auto-management режима.",
        ),
        FieldPolicy(
            field=AdvSetting.white_list_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: WhiteListMode.REPLACE_ON_TRIM,
            reason="PAID mode: срез ключей с замещением.",
        ),
        FieldPolicy(
            field=AdvSetting.auto_update_white_list, # TODO: это сейчас легаси, но надо перделать эту настройку, как возможность отключения апдейста включей для V3 updater
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Не включаем paid white-list automation автоматически без отдельного product-решения.",
        ),
        FieldPolicy(
            field=AdvSetting.auto_update_target_place,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: True,
            reason="Не включаем auto target-place автоматически без отдельного product-решения.",
        ),
        FieldPolicy(
            field=AdvSetting.bidder_for_auto,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Автосброс ставки в Auto не часть paid-start.",
        ),
    )
