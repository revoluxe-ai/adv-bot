from aiogram import Bot

from app.client_bot.user_interface.message_templates import Text
from app.utils.pricer.pricer import Pricer


class WaitingForAmount(Text):
    DISABLE_WEBPAGE_PREVIEW = True

    def __init__(
        self,
        bot: Bot,
        chat_id,
        master_sum: float,
        current_balance: float = None,
        current_bonus: float = None,
    ):
        super().__init__(bot, chat_id)
        self.master_sum = master_sum
        self._pricer = Pricer()
        self.current_balance = current_balance
        self.current_bonus = current_bonus

    @property
    def text(self):
        text = self._pricer.text
        # Добавляем информацию о текущем балансе, если она доступна
        if self.current_balance is not None:
            text = f"💰 Текущий баланс: {self.current_balance:.0f} руб.\n"

            if self.current_bonus is not None and self.current_bonus > 0:
                text += f"🎁 Текущие бонусы: {self.current_bonus:.0f} руб.\n"

            text += "\n" + self._pricer.text

        text += "\nУкажите сумму пополнения:"
        return text


class BalanceUpdated(Text):
    def __init__(self, bot: Bot, chat_id, added_balance: float, bonus: float):
        super().__init__(bot, chat_id)
        self.__balance = added_balance
        self.__bonus = bonus
        self._image = None

    @property
    def text(self):
        return f"Баланс успешно пополнен на {self.__balance} рублей + бонус {self.__bonus} рублей"
