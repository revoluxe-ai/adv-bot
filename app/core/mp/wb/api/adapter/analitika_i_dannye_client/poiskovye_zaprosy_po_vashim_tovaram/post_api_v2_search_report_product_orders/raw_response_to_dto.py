import json
from datetime import datetime
from typing import Any

from app.core.mp.wb.api.generated.analitika_i_dannye_client.types import Response
from app.core.mp.wb.dto import KeywordPosition

# TODO: Сделать упоминалки об окончании баланса
# TODO: Проверить, кажется не работает уведомление об истечении работы токенов


def convert(nmid: int, raw_response: Response[Any]) -> list[KeywordPosition]:
    content_bytes = raw_response.content
    content_str = content_bytes.decode('UTF-8')
    content = json.loads(content_str)
    try:
       items = content['data']['items']
    except KeyError:
        raise
    positions: list[KeywordPosition] = []

    for item in items:
        text = item['text']
        date_items: list[Any] = item['dateItems']
        if not date_items:
            continue
        total_views_avr_for_day = int(item['frequency'] / len(date_items))
        for date_item in date_items:
            dt = date_item['dt']
            dt_date = datetime.strptime(dt, '%Y-%m-%d')
            dt_date = dt_date.date()
            try:
                avg_position = date_item['avgPosition']
            except KeyError as e:
                raise e
            orders = date_item['orders']
            kw_position = KeywordPosition(nmid=nmid,
                                          text=text,
                                          date=dt_date,
                                          average_position=avg_position,
                                          orders=orders,
                                          total_views_avr_for_day=total_views_avr_for_day)

            positions.append(kw_position)

    return positions