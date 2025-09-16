import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.client_bot import const
from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views.callbacks import (
    AddBalance,
    ChoiceAdvPaginator,
    DeleteWbUserCabinet,
    Start,
    TurnBot,
    TurnWhiteListUpdate,
)
from app.modules.adv_creator.telegram.into_callback import CreateNewAdvs
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBCabinet,
    WBToken,
    WBUserCabinet,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.pricer.pricer import Pricer
from app.utils.suffixes import get_day_suffix

logger = logging.getLogger(__name__)


class ShopMenu(TextWithKeyboard):
    parse_mode = ParseMode.HTML

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        state: FSMContext,
        wb_user_cabinet_original_id: int,
    ):
        self._user_telegram_id = chat_id
        self._state = state
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._pricer = Pricer()
        super().__init__(bot, chat_id)

    async def _is_active_adv(self):
        """Метод оставлен для обратной совместимости, но больше не используется
        так как данные получаем сразу при основной загрузке"""
        logger.debug(
            "_is_active_adv больше не используется, и будет удален в будущих версиях"
        )
        return self.is_active_adv

    async def _load_all_data(self):
        """Оптимизированная загрузка всех данных в одной транзакции"""
        start_time = datetime.now()
        logger.debug(
            f"Начало оптимизированной загрузки данных для кабинета {self._wb_user_cabinet_original_id}"
        )

        # Сохраняем ID в состояние
        await self._state.update_data(
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id
        )

        try:
            async with sm(read_only=True) as session:
                # 1. Основной запрос с загрузкой WBUserCabinet и связанных данных
                stmt = (
                    select(WBUserCabinet)
                    .join(WBUserCabinet.wb_cabinet)
                    .options(
                        # Загружаем WBCabinet со всеми необходимыми связями
                        selectinload(WBUserCabinet.wb_cabinet),
                        selectinload(WBUserCabinet.wb_cabinet).selectinload(
                            WBCabinet.bonus_payments
                        ),
                        selectinload(WBUserCabinet.wb_cabinet).selectinload(
                            WBCabinet.balance_payments
                        ),
                        # Загружаем пользователя
                        selectinload(WBUserCabinet.user),
                        # Предзагружаем активные рекламные кампании
                        selectinload(WBUserCabinet.wb_cabinet).selectinload(
                            WBCabinet.adv_settings.and_(AdvSetting.bot_active == True)
                        ),
                    )
                    .where(WBUserCabinet.id == self._wb_user_cabinet_original_id)
                )

                result = await session.execute(stmt)
                self._wb_user_cabinet = result.scalar_one()
                self._wb_cabinet = self._wb_user_cabinet.wb_cabinet

                # 2. Получаем сразу активные рекламные кампании
                active_advs = [
                    adv for adv in self._wb_cabinet.adv_settings if adv.bot_active
                ]
                self.count_active_advs = len(active_advs)
                self.is_active_adv = self.count_active_advs > 0

                # 3. Расчет метрик кабинета
                self._now = datetime.now()
                self._expiration_time = self._wb_cabinet.expiration_time
                self._expiration_time_str = self._expiration_time.strftime(
                    "%d-%m-%Y-%H:%M"
                )
                self.days_left = (self._expiration_time - self._now).days + 1
                self.bonus_days = self.days_left * 2

                # 4. Получаем данные баланса
                self._balance = self._wb_cabinet.calculated_balance
                self._bonus = self._wb_cabinet.calculated_bonus

                # 5. Расчет метрик для тарификации
                if self.is_active_adv:
                    shop_id = self._wb_cabinet.shop_id
                    self.price_for_month_for_shop = (
                        await self._pricer.get_month_tariff_for_count_advs(shop_id)
                    )
                    self.total_amount_for_day = (
                        await self._pricer.get_price_for_day_for_shop(shop_id)
                    )
                else:
                    self.price_for_month_for_shop = 0
                    self.total_amount_for_day = 0

                # 6. Сохраняем данные в состояние
                await self._state.update_data(
                    last_wb_cabinet_original_id=self._wb_cabinet.id
                )

                logger.debug(
                    f"Данные успешно загружены за {(datetime.now() - start_time).total_seconds():.2f} сек"
                )
                return True
        except Exception as e:
            logger.error(
                f"Ошибка при оптимизированной загрузке данных: {e}", exc_info=True
            )
            await self.bot.send_message(
                self.chat_id,
                "Произошла ошибка при загрузке данных. Пожалуйста, попробуйте позже.",
            )
            raise e

    async def _process_tokens(self):
        """Обработка токенов для магазина"""
        # Получаем пользователя до обработки токенов для корректной проверки админа
        user: User = self._wb_user_cabinet.user
        shop_id = self._wb_cabinet.shop_id
        logger.debug(
            f"Обработка токенов для пользователя {user.user_telegram_id}, магазин {shop_id}"
        )

        # Оптимизированная загрузка токенов - фильтруем сразу на уровне SQL
        try:
            token_start_time = datetime.now()
            async with sm(read_only=True) as session:
                # Сразу фильтруем токены для конкретного магазина
                stmt = select(WBToken).where(WBToken.shop_id == shop_id)
                result = await session.execute(stmt)
                work_tokens: list[WBToken] = result.scalars().all()
                logger.debug(
                    f"Найдено токенов для магазина {shop_id}: {len(work_tokens)} (запрос выполнен за {(datetime.now() - token_start_time).total_seconds():.2f} сек)"
                )
        except Exception as e:
            logger.error(f"Ошибка при загрузке токенов из БД: {e}", exc_info=True)
            work_tokens = []

        # Проверка наличия токенов
        if not work_tokens:
            logger.warning(f"Токены не найдены для магазина {shop_id}")
            # Для админов делаем исключение
            if user.user_telegram_id in const.ADMINS:
                logger.debug(f"Админ {user.user_telegram_id} получает временный токен")
                expiration_time = datetime.now() + timedelta(days=30)
                self.expiration_time = expiration_time
                self.last_days_for_token = 30
                return True
            else:
                await self.bot.send_message(
                    self.chat_id,
                    "Не найдены токены для этого магазина. Пожалуйста, добавьте новый токен.",
                )
                return False

        # Сортировка токенов по сроку действия
        sort_start_time = datetime.now()
        shops_tokens = work_tokens
        shops_tokens.sort(key=lambda token: token.expires, reverse=True)
        logger.debug(
            f"Сортировка токенов выполнена за {(datetime.now() - sort_start_time).total_seconds():.2f} сек"
        )

        # Определение срока действия
        if user.user_telegram_id in const.ADMINS:
            expiration_time = datetime.now() + timedelta(days=30)
            logger.debug(
                "Пользователь - админ, установлен временный срок действия токена"
            )
        else:
            try:
                expiration_time = shops_tokens[0].expires
                logger.debug(f"Установлен срок действия токена: {expiration_time}")
            except IndexError:
                await self.bot.send_message(
                    self.chat_id,
                    "Не найдены действительные токены для этого магазина. Пожалуйста, добавьте новый токен.",
                )
                return False

        # Проверка на истечение срока действия
        if (
            expiration_time < datetime.now()
            and user.user_telegram_id not in const.ADMINS
        ):
            await self.bot.send_message(
                self.chat_id,
                "Срок действия токена истек. Пожалуйста, обновите токен.\nДля этого добавьте магазин под другим именем с новым токеном",
            )
            return False

        # Сохранение срока действия для дальнейшего использования
        if user.user_telegram_id in const.ADMINS:
            # Для админов устанавливаем временное значение
            self.expiration_time = datetime.now() + timedelta(days=30)
            self.last_days_for_token = 30
        else:
            self.expiration_time = expiration_time
            self.last_days_for_token = (expiration_time - datetime.now()).days

        logger.debug(
            f"Обработка токенов успешно завершена, установлен срок действия {self.last_days_for_token} дней"
        )
        return True

    async def __call__(self):
        """Оптимизированный метод для отображения меню магазина"""
        start_time = datetime.now()
        logger.debug(f"Вызов ShopMenu для кабинета {self._wb_user_cabinet_original_id}")

        # Единый метод загрузки всех данных вместо трех отдельных
        try:
            await self._load_all_data()
        except Exception as e:
            logger.error(f"Критическая ошибка в ShopMenu.__call__: {e}", exc_info=True)
            del e
            return  # Прерываем выполнение в случае ошибки

        # Проверка и обработка токенов только если это необходимо
        # Вызов метода _process_tokens закомментирован, так как из кода видно,
        # что он в данный момент не используется
        # if необходимое_условие:
        #     tokens_valid = await self._process_tokens()
        #     if not tokens_valid:
        #         return

        # Отображение меню магазина
        display_start_time = datetime.now()
        logger.debug("Отображение меню магазина (вызов родительского метода __call__)")

        # Вызываем родительский метод __call__, который отвечает за отправку сообщения
        await super().__call__()

        logger.debug(
            f"Меню магазина отображено за {(datetime.now() - display_start_time).total_seconds():.2f} сек"
        )
        total_time = (datetime.now() - start_time).total_seconds()
        logger.debug(
            f"Общее время выполнения метода ShopMenu.__call__: {total_time:.2f} сек"
        )

    @property
    def text(self):
        balance = self._balance
        bonus = self._bonus
        count_active_advs = self.count_active_advs
        total_money = balance + bonus
        total_amount_for_day = self.total_amount_for_day
        if self.total_amount_for_day:
            last_for_days = int(total_money / self.total_amount_for_day)
        else:
            last_for_days = "∞"
        text = (
            f"📊 <b>Кампаний на автоуправлении</b>: {count_active_advs}\n"
            f"""Ваш тариф в месяц: {self.price_for_month_for_shop if self.price_for_month_for_shop else 'Нет активных РК'}"""
            f"(больше РК -> ниже цена, тарифы -> https://telegra.ph/Tarify-03-17)\n"
            f"💸 <b>Расход в сутки</b>: {total_amount_for_day} р.\n"
        )

        if isinstance(last_for_days, int):
            if last_for_days > 7:
                text += f"""
💰 Денег хватит на {get_day_suffix(last_for_days)} работы бота. 💰
            """
            elif last_for_days == 0:
                text += """
⚠️ Денег на продление кампаний больше нет! ⚠️

💳 Срочно пополните баланс во избежание проблем с работой кампаний!
"""
            else:
                text += f"""
🚨 Внимание!!! 🚨

💰 Денег хватит на {get_day_suffix(last_for_days)} работы бота.

🔔 Настоятельно рекомендую пополнить счет во избежание проблем с работой кампаний"""

        text += (
            "===================================\n"
            f"🏬 Магазин: {self._wb_user_cabinet.name}\n"
            f"🆔 Shop ID: {self._wb_cabinet.shop_id}\n"
            f"💰 Баланс магазина: {balance:.0f} рублей\n"
            f"🎁 Бонусы: {self._bonus:.0f} рублей\n"
        )

        text += """
<a href="https://telegra.ph/Bystryj-start-02-11">Инструкция по быстрому старту работы</a>. Подходит для базовой автоматизации.
                """

        return text

    @property
    def keyboard(self):
        user_telegram_id = self._user_telegram_id
        wb_user_cabinet = self._wb_user_cabinet
        wb_cabinet = self._wb_cabinet
        is_active_adv = self.is_active_adv
        wb_cabinet_original_id = wb_cabinet.id
        is_active_adv: True
        builder = InlineKeyboardBuilder()
        button = InlineKeyboardButton(
            text="Автоматические рекламные кампании",
            callback_data=ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet.id, page=1
            ).pack(),
        )
        builder.row(button)

        button = InlineKeyboardButton(
            text="Создать и настроить кампании",
            callback_data=CreateNewAdvs(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )

        builder.row(button)

        button = InlineKeyboardButton(
            text="Пополнить баланс",
            callback_data=AddBalance(
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack(),
        )

        builder.row(button)
        #

        if user_telegram_id in const.ADMINS:
            button = InlineKeyboardButton(
                text="Удалить личный кабинет магазина",
                callback_data=DeleteWbUserCabinet(
                    wb_user_cabinet_original_id=self._wb_user_cabinet.id
                ).pack(),
            )

            builder.row(button)

        if is_active_adv:
            button = InlineKeyboardButton(
                text="Отключить все кампании",
                callback_data=TurnBot(
                    action="off_all", wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
            builder.row(button)

        if self._wb_cabinet.white_list_update_active:
            button = InlineKeyboardButton(
                text="Выключить авто-обновление белого списка",
                callback_data=TurnWhiteListUpdate(
                    wb_cabinet_original_id=self._wb_cabinet.id, action="off"
                ).pack(),
            )
        else:
            button = InlineKeyboardButton(
                text="Включить авто-обновление белого списка",
                callback_data=TurnWhiteListUpdate(
                    wb_cabinet_original_id=self._wb_cabinet.id, action="on"
                ).pack(),
            )

        builder.row(button)

        button = InlineKeyboardButton(
            text="Вернуться к списку магазинов", callback_data=Start().pack()
        )
        builder.row(button)
        return builder.as_markup()
