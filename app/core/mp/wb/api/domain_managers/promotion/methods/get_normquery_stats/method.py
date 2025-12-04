from datetime import date

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import (NormqueryStatsAdapter,
                                                                         GetNormqueryStatsCommand)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from . import convertor


async def get_normquery_stats(normquery_stats_adapter: NormqueryStatsAdapter,
                              complex_advs: list[ComplexAdv] ,
                              date_from: date,
                              date_to: date):

    command:  GetNormqueryStatsCommand = convertor.dto_to_command(complex_advs,
                                                                  date_from,
                                                                  date_to=date_to)

    return await normquery_stats_adapter.get_adv_v0_normquery_stats(command)
 