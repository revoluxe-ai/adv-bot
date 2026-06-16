"""Совместимая обёртка для утилит пагинации дневной статистики.

Истинная реализация переехала в `app.modules.wb_adv_updater.keyword_daily_history`
чтобы бизнес-слой не зависел от глубокой UI-папки. Этот модуль оставлен для
обратной совместимости с существующими UI-импортами.
"""

from app.modules.wb_adv_updater.keyword_daily_history.date_pagination import (
    get_total_pages,
    page_to_date_range,
)
