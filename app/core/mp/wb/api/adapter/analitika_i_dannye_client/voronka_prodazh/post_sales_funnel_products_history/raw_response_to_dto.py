from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.core.mp.wb.api.generated.analitika_i_dannye_client.models import (
    ProductHistoryResponseItem,
)


def convert(parsed_response: list[ProductHistoryResponseItem]) -> list[CommonSaleStatRow]:
    """
    Конвертирует типизированный ответ API (List[ProductHistoryResponseItem])
    в список строк для вставки в ClickHouse.
    """
    rows: list[CommonSaleStatRow] = []

    for item in parsed_response:
        nmid = item.product.nm_id
        for history_item in item.history:
            row = CommonSaleStatRow(
                nmid=nmid,
                day=history_item.date,
                open_card=history_item.open_count,
                add_to_cart=history_item.cart_count,
                orders=history_item.order_count,
                orders_sum=float(history_item.order_sum),
                buy_outs=history_item.buyout_count,
            )
            rows.append(row)

    return rows


