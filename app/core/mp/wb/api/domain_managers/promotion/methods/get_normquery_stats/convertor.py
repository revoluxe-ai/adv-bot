from datetime import date

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import (GetNormqueryStatsCommand,
                                                                        GetNormqueryStatsCommandBatchForAdv)

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


def dto_to_command(complex_advs: list[ComplexAdv],
                   date_from: date,
                   date_to: date
                   ) -> GetNormqueryStatsCommand:
    batchs: list[GetNormqueryStatsCommandBatchForAdv] = []
    for adv in complex_advs:
        nmids = adv.nmids
        for nmid in nmids:
            auto_adv_id = adv.auto_adv_id
            batch = GetNormqueryStatsCommandBatchForAdv(
            adv_id=auto_adv_id,
                nmid=nmid,
            )
            batchs.append(batch)

            if search_adv:= adv.search_adv:
                search_adv_id = search_adv.adv_id
                batch = GetNormqueryStatsCommandBatchForAdv(
                    adv_id=search_adv_id,
                    nmid=nmid,
                )
                batchs.append(batch)
    command = GetNormqueryStatsCommand(
        date_from=date_from,
        date_to=date_to,
        batchs=batchs
    )
    return command

