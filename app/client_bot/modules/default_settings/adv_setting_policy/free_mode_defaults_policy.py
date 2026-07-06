"""FREE mode overlay for manual/self-service campaign behavior."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode

from .base_policy import AdvSettingDefaultsPolicy
from .field_policy import FieldPolicy
from .white_list_mode_rules import FREE_SAFE_WHITE_LIST_MODES


class FreeModeDefaultsPolicy(AdvSettingDefaultsPolicy):
    """FREE mode overlay for manual/self-service campaign behavior."""

    name = "free_mode_overlay"

    rules = (
        FieldPolicy(
            field=AdvSetting.automatic_version,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: 2,
            reason="FREE mode работает на updater v2.",
        ),
        FieldPolicy(
            field=AdvSetting.bidder_active,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="FREE mode: ручной bidder стартует выключенным до явного запуска пользователем.",
        ),
        FieldPolicy(
            field=AdvSetting.white_list_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: (
                adv.white_list_mode
                if adv.white_list_mode in FREE_SAFE_WHITE_LIST_MODES
                else WhiteListMode.ABOVE_MIN_RATING
            ),
            reason="Безопасный FREE-режим БС без paid replacement-логики.",
        ),
        FieldPolicy(
            field=AdvSetting.auto_update_white_list,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Paid white-list automation выключена во FREE.",
        ),
        FieldPolicy(
            field=AdvSetting.auto_update_target_place,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Paid auto target-place выключен во FREE.",
        ),
        FieldPolicy(
            field=AdvSetting.bidder_for_auto,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Автосброс ставки в Auto выключен во FREE.",
        ),
    )
