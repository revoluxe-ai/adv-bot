from aiogram.filters.callback_data import CallbackData


class SettingAuctionBoostMode(CallbackData,
                              prefix='setting_auction_boos_mode'):
    new_mode: bool
    adv_id: int