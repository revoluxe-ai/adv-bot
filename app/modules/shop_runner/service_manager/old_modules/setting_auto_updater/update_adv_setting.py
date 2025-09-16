from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.target_place_updater import (
    TargetPlaceUpdater,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.modules.white_list_updater import (
    WhiteListUpdateManager,
)


async def update_adv_setting(
    adv: AdvSetting,
    keywords: list[CalculatedKeyword],
    plan_data: PlanData,
    fact_data: FactData,
) -> bool:
    white_list_update_manager = WhiteListUpdateManager(adv)
    target_place_update_manager = TargetPlaceUpdater(adv)
    if fact_data.pay_for_order > plan_data.max_pay_for_order:
        (
            change_success_delete_phrase,
            touch_setting_limit_delete_last_white_phrase,
        ) = await white_list_update_manager.delete_last_white_phrase(keywords)
        if touch_setting_limit_delete_last_white_phrase:
            (
                change_success_target_place,
                _,
            ) = await target_place_update_manager.set_down()

            return change_success_delete_phrase or change_success_target_place
        else:
            return change_success_delete_phrase
    if fact_data.pay_for_order == plan_data.max_pay_for_order:
        change_success_target_place, _ = await target_place_update_manager.set_down()
        return change_success_target_place
    if fact_data.predict_orders >= plan_data.orders:
        any_change = False
        if fact_data.pay_for_order > plan_data.target_pay_for_order:
            (
                change_success_target_place,
                touch_setting_limit_success_target_place,
            ) = await target_place_update_manager.set_down()
            if change_success_target_place:
                any_change = True
            if touch_setting_limit_success_target_place:
                (
                    change_success_delete_phrase,
                    touch_setting_limit_success_delete_phrase,
                ) = await white_list_update_manager.delete_last_white_phrase(keywords)
                if not any_change and change_success_delete_phrase:
                    any_change = True
            return any_change
        return any_change

    (
        change_success_add_white_list,
        _,
    ) = await white_list_update_manager.add_phrase_to_white_list(keywords)
    change_success_change_target_place, _ = await target_place_update_manager.set_up()
    return change_success_add_white_list or change_success_change_target_place
