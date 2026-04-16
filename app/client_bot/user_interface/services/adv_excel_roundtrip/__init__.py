"""Excel export/import для массового просмотра и правки настроек РК."""

from app.client_bot.user_interface.services.adv_excel_roundtrip.deviation import (
    compute_deviation_metrics,
)

__all__ = ["compute_deviation_metrics"]
