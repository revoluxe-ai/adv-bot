from app.modules.common_slaves.wildberries.models import AdvSetting

class Keyboards:

    def __init__(self, adv: AdvSetting):
        self._adv = adv


    def setting_plan_for_sales_for_day_button(self):
        adv = self._adv
        adv.