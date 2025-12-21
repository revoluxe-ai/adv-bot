import json
from datetime import date
from typing import Any

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import Response


def convert(raw_response: Response[Any]) -> list[CommonSaleStatRow]:
    content_bytes = raw_response.content
    content_str = content_bytes.decode("UTF-8")
    content = json.loads(content_str)

    rows: list[CommonSaleStatRow] = []

    # Ответ: список объектов [{ product: {...}, history: [...] }, ...]
    for item in content:
        product = item.get("product", {})
        nmid = product.get("nmid")
        if not nmid:
            continue
        nmid = int(nmid)
        history = item.get("history", [])
        for h in history:
            day = date.fromisoformat(h.get("date"))
            row = CommonSaleStatRow(
                nmid=nmid,
                day=day,
                open_card=int(h.get("openCount", 0)),
                add_to_cart=int(h.get("cartCount", 0)),
                orders=int(h.get("orderCount", 0)),
                orders_sum=float(h.get("orderSum", 0)),
                buy_outs=int(h.get("buyoutCount", 0)),
            )
            rows.append(row)

    return rows


