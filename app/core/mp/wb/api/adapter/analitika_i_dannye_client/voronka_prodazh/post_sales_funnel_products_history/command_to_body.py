from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import (
    Level,
    ProductHistoryRequest,
    ProductHistoryRequestSelectedPeriod,
)

from .command import SalesFunnelProductsHistoryCommand


def convert(command: SalesFunnelProductsHistoryCommand) -> ProductHistoryRequest:
    period = ProductHistoryRequestSelectedPeriod(
        start=command.start,
        end=command.end,
    )

    level = Level(command.aggregation_level)

    return ProductHistoryRequest(
        selected_period=period,
        nm_ids=command.nmids,
        skip_deleted_nm=command.skip_deleted_nm,
        aggregation_level=level,
    )


