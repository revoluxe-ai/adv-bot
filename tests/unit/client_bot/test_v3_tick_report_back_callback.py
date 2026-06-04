"""V3TickReportBack несёт adv_setting_original_id в callback_data."""

from app.client_bot.user_interface.views.callbacks import V3TickReportBack


def test_v3_tick_report_back_packs_adv_id() -> None:
    packed = V3TickReportBack(adv_setting_original_id=12345).pack()
    parsed = V3TickReportBack.unpack(packed)
    assert parsed.adv_setting_original_id == 12345
