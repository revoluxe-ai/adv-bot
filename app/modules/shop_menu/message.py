"""Меню магазина: текст, главная и mass-ops клавиатуры Telegram UI.

Содержит ``ShopMenu`` и builders клавиатур. ``build_shop_main_keyboard``
безопасно обрабатывает отсутствие ``WBUserCabinet.user`` (admin toggle
не показывается без валидного admin telegram id).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Mapping

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dependency_injector.wiring import Provide, inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.client_bot import const
from app.client_bot.admin_access import is_bot_admin
from app.client_bot.cashback_snapshot import parse_cashback_snapshot
from app.client_bot.ui_access import UiAccessMode, UiAccessResolver
from app.client_bot.ui_mode import UiModeService
from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.utils import format_required_wb_token_scopes
from app.client_bot.user_interface.views.callbacks import (
    AddNewToken,
    ApplyDefaultsForShop,
    ChangeShopDefaultMaxCPM,
    ResetShopNonRelevantPhrases,
    ShopMassAdvOpsBack,
    ShopMassAdvOpsMenu,
    ExportShopAdvExcel,
    ImportShopAdvExcel,
    ToggleCabinetActive,
)
from app.client_bot.user_interface.views.callbacks import (
    AddBalance,
    ChoiceAdvPaginator,
    ConnectExistingAdvs,
    ShowShopsList,
    TurnBot,
    UiModeToggle,
)
from app.modules.billing.pricer.pricer import Pricer, TariffMode, TariffDetails
from app.modules.billing.redis_manager import RedisManager as BillingRedisManager
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfoService,
    TokenStatusReport,
)
from app.modules.auto_budget_manager.redis_shop_balance_snapshot_manager import (
    RedisShopBalanceSnapshotManager,
)
from app.core.redis_manager_v2.redis_client import RedisClient
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker as sm
from app.utils.suffixes import get_day_suffix

logger = logging.getLogger(__name__)


def _is_admin_user(user_telegram_id: int | None) -> bool:
    if user_telegram_id is None:
        return False
    return is_bot_admin(user_telegram_id)


def _has_read_only_only_tokens(token_status: TokenStatusReport) -> bool:
    """Return True when the shop has only active read-only tokens for analytics."""
    has_active_read_only_token = any(
        token.is_read_only and token.is_valid and not token.is_expired
        for token in token_status.all_tokens
    )
    return has_active_read_only_token and not token_status.valid_tokens


def build_shop_main_keyboard(
    wb_user_cabinet: WBUserCabinet,
    wb_cabinet: WBCabinet,
    ui_access: UiAccessMode = UiAccessMode.FREE,
) -> InlineKeyboardMarkup:

    """Собрать главную inline-клавиатуру магазина.

    Админский toggle режима UI добавляется только при валидном
    telegram id админа. Отсутствие ``wb_user_cabinet.user`` (или ``None``)
    не должно приводить к ``AttributeError`` — toggle просто не показывается.

    Args:
        wb_user_cabinet: Кабинет пользователя WB (может быть без загруженного ``user``).
        wb_cabinet: Кабинет магазина.
        ui_access: Режим доступа UI (FREE/PAID), влияет на платные кнопки.

    Returns:
        InlineKeyboardMarkup главной клавиатуры магазина.
    """
    """Build the shop menu keyboard for the effective free/paid access mode."""
    wb_cabinet_original_id = wb_cabinet.id
    builder = InlineKeyboardBuilder()

    _ = builder.row(
        InlineKeyboardButton(
            text="Автоматические рекламные кампании",
            callback_data=ChoiceAdvPaginator(
                wb_user_cabinet_original_id=wb_user_cabinet.id, page=1
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="➕ Добавить токен/Обновить токены",
            callback_data=AddNewToken(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    cabinet_active = getattr(wb_cabinet, "active", True) is True
    toggle_label = "Деактивировать магазин" if cabinet_active else "Активировать магазин"
    _ = builder.row(
        InlineKeyboardButton(
            text=toggle_label,
            callback_data=ToggleCabinetActive(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Подключить существующие кампании",
            callback_data=ConnectExistingAdvs(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Пополнить баланс",
            callback_data=AddBalance(
                wb_cabinet_original_id=wb_cabinet_original_id
            ).pack(),
        )
    )

    if ui_access == UiAccessMode.PAID:
        _ = builder.row(
            InlineKeyboardButton(
                text="Массовые операции с РК",
                callback_data=ShopMassAdvOpsMenu(
                    wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
        )

        _ = builder.row(
            InlineKeyboardButton(
                text="Выгрузить все РК в Excel",
                callback_data=ExportShopAdvExcel(
                    wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
        )

    # Безопасный resolve: user может отсутствовать / быть None
    # (например, loader без joinedload или detached ORM вне сессии).
    user = getattr(wb_user_cabinet, "user", None)
    if _is_admin_user(getattr(user, "user_telegram_id", None)):
        _ = builder.row(
            InlineKeyboardButton(
                text=f"Режим интерфейса: {ui_access.name}",
                callback_data=UiModeToggle(
                    wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
        )

    if ui_access == UiAccessMode.PAID:
        _ = builder.row(
            InlineKeyboardButton(
                text="Загрузить настройки из Excel",
                callback_data=ImportShopAdvExcel(
                    wb_user_cabinet_original_id=wb_user_cabinet.id
                ).pack(),
            )
        )

    _ = builder.row(
        InlineKeyboardButton(
            text="Вернуться к списку магазинов",
            callback_data=ShowShopsList().pack(),
        )
    )
    return builder.as_markup()


def build_shop_mass_adv_ops_keyboard(
    wb_user_cabinet: WBUserCabinet,
    wb_cabinet: WBCabinet,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    _ = builder.row(
        InlineKeyboardButton(
            text="Полностью отключить бот от управления всех РК",
            callback_data=TurnBot(
                action="off_all",
                wb_user_cabinet_original_id=wb_user_cabinet.id,
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text=f"Дефолтная максимальная ставка (CPM) ({wb_cabinet.default_max_cpm})",
            callback_data=ChangeShopDefaultMaxCPM(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Применить дефолты всем кампаниям",
            callback_data=ApplyDefaultsForShop(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Сбросить все НРФ во всех РК",
            callback_data=ResetShopNonRelevantPhrases(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )

    _ = builder.row(
        InlineKeyboardButton(
            text="Назад",
            callback_data=ShopMassAdvOpsBack(
                wb_user_cabinet_original_id=wb_user_cabinet.id
            ).pack(),
        )
    )
    return builder.as_markup()


class ShopMenu(TextWithKeyboard):
    parse_mode = ParseMode.HTML

    @inject
    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        state: FSMContext,
        wb_user_cabinet_original_id: int,
        redis_client: RedisClient | None = Provide["redis_client_wrapper"],
    ):
        self._user_telegram_id = chat_id
        self._state = state
        self._wb_user_cabinet_original_id = wb_user_cabinet_original_id
        self._pricer = Pricer()
        self._tariff_details: TariffDetails | None = None
        self._last_charge_at: datetime | None = None
        self._billing_redis_manager: BillingRedisManager | None = None
        self._balance_snapshot_manager: RedisShopBalanceSnapshotManager | None = None
        self._shop_balance_snapshot: dict[str, int | str | None] | None = None
        self._ui_mode_service: UiModeService | None = None
        self._ui_access_resolver: UiAccessResolver | None = None
        self._ui_access: UiAccessMode = UiAccessMode.FREE
        if isinstance(redis_client, RedisClient):
            self._billing_redis_manager = BillingRedisManager(redis_client=redis_client)
            self._balance_snapshot_manager = RedisShopBalanceSnapshotManager(redis_client)
            self._ui_mode_service = UiModeService(redis_client=redis_client)
            self._ui_access_resolver = UiAccessResolver(self._ui_mode_service)

        # Initialize token status attributes
        self._token_status: TokenStatusReport | None = None
        self._token_status_loaded = False

        super().__init__(bot, chat_id)

    async def get_shop_token_status(self) -> None:
        """Load token status for the shop."""
        try:
            token_service = TokenInfoService()
            shop_id = self._wb_cabinet.shop_id
            self._token_status = await token_service.get_shop_token_status(shop_id)
            self._token_status_loaded = True
            assert self._token_status is not None
            logger.debug(
                "Token status loaded for shop %s: %s",
                shop_id,
                self._token_status.status,
            )
        except Exception as e:
            logger.error(f"Failed to load token status: {e}", exc_info=True)
            self._token_status = None
            self._token_status_loaded = False

    async def _load_tariff_details_in_session(
        self, session: AsyncSession, shop_id: str
    ) -> TariffDetails:
        """Load tariff details via Pricer using caller-opened session.

        Parent ``_load_all_data`` opens ``sm(read_only=True)`` and passes
        the session here (PURE_READ handoff). Threads ``leg_latch`` and
        ``utc_date`` like billing charge / ``_load_tariff_preview`` (PBH-003).
        """
        leg_latch = None
        utc_date = None
        if self._billing_redis_manager is not None:
            leg_latch = self._billing_redis_manager.leg_latch()
            utc_date = datetime.now(timezone.utc).date()
        return await self._pricer.get_tariff_details(
            session,
            shop_id,
            leg_latch=leg_latch,
            utc_date=utc_date,
        )

    async def _load_all_data(self) -> bool:
        """Оптимизированная загрузка всех данных в одной транзакции"""
        start_time = datetime.now()
        logger.debug(
            "Начало оптимизированной загрузки данных для кабинета %s",
            self._wb_user_cabinet_original_id,
        )

        # Сохраняем ID в состояние
        _ = await self._state.update_data(
            last_wb_user_cabinet_original_id=self._wb_user_cabinet_original_id
        )
        wb_user_cabinet_original_id = self._wb_user_cabinet_original_id
        async with sm(read_only=True) as session:
            wb_user_cabinet: WBUserCabinet = await self._get_wb_user_cabinet_with_user_and_wb_cabinet(
                session,
                wb_user_cabinet_original_id,
            )

            wb_cabinet = wb_user_cabinet.wb_cabinet
            self._wb_user_cabinet: WBUserCabinet = wb_user_cabinet
            self._wb_cabinet = wb_cabinet

            # 3. Расчет метрик кабинета
            self._now = datetime.now()
            self._expiration_time = self._wb_cabinet.expiration_time
            self._expiration_time_str = self._expiration_time.strftime("%d-%m-%Y-%H:%M")
            self.days_left = (self._expiration_time - self._now).days + 1
            self.bonus_days = self.days_left * 2

            # 4. Получаем данные баланса
            self._balance = self._wb_cabinet.calculated_balance
            self._bonus = self._wb_cabinet.calculated_bonus
            if self._balance_snapshot_manager is not None:
                self._shop_balance_snapshot = await self._balance_snapshot_manager.get(
                    self._wb_cabinet.shop_id
                )
            if self._ui_access_resolver is not None:
                self._ui_access = await self._ui_access_resolver.resolve_shop_ui_access(
                    self._user_telegram_id, session, self._wb_cabinet.shop_id
                )
            # 6. Load token status
            await self.get_shop_token_status()

            # 7. Сохраняем данные в состояние
            _ = await self._state.update_data(
                last_wb_cabinet_original_id=self._wb_cabinet.id
            )

            logger.debug(
                f"Данные успешно загружены за {(datetime.now() - start_time).total_seconds():.2f} сек"
            )

        # TODO: Почему-то на выброс этой ошибки мне не приходят сообщения в бот
        shop_id = self._wb_cabinet.shop_id
        async with sm(read_only=True) as session:
            self._tariff_details = await self._load_tariff_details_in_session(
                session, shop_id
            )
        self._total_active_advs_count = (
            self._tariff_details.count if self._tariff_details else 0
        )
        if self._billing_redis_manager:
            try:
                self._last_charge_at = await self._billing_redis_manager.get_last_charge_at(
                    self._wb_cabinet.shop_id
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Не удалось получить last_charge_at из Redis: %s", exc)

        return True

    async def _load_tariff_preview(self) -> None:
        """Превью тарифа: тот же leg_metering + latch read, что и billing charge."""
        shop_id = self._wb_cabinet.shop_id
        leg_latch = None
        utc_date = None
        if self._billing_redis_manager is not None:
            leg_latch = self._billing_redis_manager.leg_latch()
            utc_date = datetime.now(timezone.utc).date()
        async with sm(read_only=True) as session:
            self._tariff_details = await self._pricer.get_tariff_details(
                session,
                shop_id,
                leg_latch=leg_latch,
                utc_date=utc_date,
            )

    async def _process_tokens(self):
        """Обработка токенов для магазина"""
        # Получаем пользователя до обработки токенов для корректной проверки админа
        user: User = self._wb_user_cabinet.user
        shop_id = self._wb_cabinet.shop_id
        logger.debug(
            "Обработка токенов для пользователя %s, магазин %s",
            user.user_telegram_id,
            shop_id,
        )

        # Оптимизированная загрузка токенов - фильтруем сразу на уровне SQL
        try:
            token_start_time = datetime.now()
            async with sm(read_only=True) as session:
                # Сразу фильтруем токены для конкретного магазина
                stmt = select(WBToken).where(WBToken.shop_id == shop_id)
                result = await session.execute(stmt)
                work_tokens: list[WBToken] = list(result.scalars().all())
                logger.debug(
                    f"Найдено токенов для магазина {shop_id}:"
                    f" {len(work_tokens)} (запрос выполнен за "
                    f"{(datetime.now() - token_start_time).total_seconds():.2f} сек)"
                )
        except Exception as e:
            logger.error(f"Ошибка при загрузке токенов из БД: {e}", exc_info=True)
            work_tokens = []

        # Проверка наличия токенов
        if not work_tokens:
            logger.warning(f"Токены не найдены для магазина {shop_id}")
            # Для админов делаем исключение
            if _is_admin_user(user.user_telegram_id):
                logger.debug(f"Админ {user.user_telegram_id} получает временный токен")
                expiration_time = datetime.now() + timedelta(days=30)
                self.expiration_time = expiration_time
                self.last_days_for_token = 30
                return True
            else:
                _ = await self.bot.send_message(
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
        if _is_admin_user(user.user_telegram_id):
            expiration_time = datetime.now() + timedelta(days=30)
            logger.debug(
                "Пользователь - админ, установлен временный срок действия токена"
            )
        else:
            try:
                expiration_time = shops_tokens[0].expires
                logger.debug(f"Установлен срок действия токена: {expiration_time}")
            except IndexError:
                _ = await self.bot.send_message(
                    self.chat_id,
                    "Не найдены действительные токены для этого магазина. Пожалуйста, добавьте новый токен.",
                )
                return False

        # Проверка на истечение срока действия
        if (
            expiration_time < datetime.now()
            and not _is_admin_user(user.user_telegram_id)
        ):
            _ = await self.bot.send_message(
                self.chat_id,
                "Срок действия токена истек. Пожалуйста, обновите токен.\n"
                "Для этого добавьте магазин под другим именем с новым токеном",
            )
            return False

        # Сохранение срока действия для дальнейшего использования
        if _is_admin_user(user.user_telegram_id):
            # Для админов устанавливаем временное значение
            self.expiration_time = datetime.now() + timedelta(days=30)
            self.last_days_for_token = 30
        else:
            self.expiration_time = expiration_time
            self.last_days_for_token = (expiration_time - datetime.now()).days

        return True

    async def __call__(self):
        """Оптимизированный метод для отображения меню магазина"""
        start_time = datetime.now()
        logger.debug(f"Вызов ShopMenu для кабинета {self._wb_user_cabinet_original_id}")

        # Единый метод загрузки всех данных вместо трех отдельных
        _ = await self._load_all_data()

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

        logger.debug(
            "Меню магазина отображено" " за %s сек",
            round((datetime.now() - display_start_time).total_seconds(), 2),
        )
        total_time = (datetime.now() - start_time).total_seconds()
        logger.debug(
            f"Общее время выполнения метода ShopMenu.__call__: {total_time:.2f} сек"
        )
        await super().__call__()
        return None

    @property
    def text(self):
        balance = self._balance
        bonus = self._bonus
        count_active_advs = self._total_active_advs_count
        total_money = balance + bonus

        details = self._tariff_details
        if details:
            tariff_label = (
                "Новый тариф (Авто)" if details.mode == TariffMode.AUTO else "Старый тариф"
            )
            price_per_adv = details.price_per_adv
            monthly_tariff = details.total_per_month
            daily_tariff = details.total_per_day
        else:
            tariff_label = "Нет активных кампаний"
            price_per_adv = 0.0
            monthly_tariff = 0.0
            daily_tariff = 0.0

        # 💰 MONEY SECTION - All financial information grouped together
        text = (
            f"⚙️ <b>Тариф:</b> {tariff_label}\n"
            f"📊 <b>Кампаний на автоуправлении</b>: {count_active_advs}\n"
            f"💵 <b>Цена за кампанию</b>: {price_per_adv:.2f} р./мес "
            f"(детали -> {const.SUPPORT_LINK})\n"
            f"💰 <b>Расход в месяц</b>: {monthly_tariff:.2f} р.\n"
            f"💸 <b>Расход в сутки</b>: {daily_tariff:.2f} р.\n"
        )
        if self._last_charge_at:
            text += f"🕒 <b>Последнее списание</b>: {self._last_charge_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        else:
            text += "🕒 <b>Последнее списание</b>: нет данных\n"

        if monthly_tariff == 0:
            last_for_days = "ထ"
        else:
            last_for_days = int(total_money / monthly_tariff * 30)

        # Money status with appropriate warnings
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

        # Balance details
        text += (
            "\n===================================\n"
            f"💰 <b>Баланс магазина</b>: {balance:.0f} рублей\n"
            f"🎁 <b>Бонусы</b>: {self._bonus:.0f} рублей\n"
        )
        cashback_line = self._format_cashback_snapshot_line(self._shop_balance_snapshot)
        if cashback_line:
            text += f"{cashback_line}\n"

        # 🔑 TOKEN SECTION - All token information grouped together
        if self._token_status_loaded and self._token_status:
            token_status = self._token_status

            if token_status.status == "Complete":
                # All permissions available - show success status
                text += "\n🔑 <b>Токены:</b> ✅ <b>Все в порядке</b>\n"

                # Always show when service will expire (if we have expiration info)
                days_until_break = token_status.days_until_service_breaks
                if days_until_break is not None:
                    expiration_date = token_status.service_expiration_date
                    if expiration_date:
                        date_str = expiration_date.strftime("%d.%m.%Y")
                        if days_until_break <= 3:
                            text += f"🚨 <b>Сервис перестанет работать {date_str} (через {days_until_break} дн.)!</b>\n"
                        elif days_until_break <= 7:
                            text += (
                                f"⚠️ <b>Внимание:</b> Сервис перестанет работать {date_str} "
                                f"(через {days_until_break} дн.)\n"
                            )
                        elif days_until_break <= 30:
                            text += f"⏰ Сервис перестанет работать {date_str} (через {days_until_break} дн.)\n"
                        else:
                            # Show expiration date even for distant dates
                            text += f"📅 Токены действуют до {date_str} (через {days_until_break} дн.)\n"
            else:
                # Missing permissions - show critical status
                if _has_read_only_only_tokens(token_status):
                    text += (
                        "\n⚠️ <b>У этого WB API токена доступны только права чтения.</b>\n\n"
                        "Бот работает в режиме аналитики: можно смотреть кампании, ключи, историю и статистику.\n\n"
                        "Автоуправление ставками и кампаниями недоступно.\n"
                        "Для управления кампаниями из бота нужен токен с возможностью изменений в кабинете (без галочки"
                        " Только для чтения).\n"
                        f"{format_required_wb_token_scopes()}"
                    )
                text += "\n🔑 <b>Токены:</b> ❌ <b>Требуется обновление</b>\n"
                text += f"❌ <b>Отсутствуют права:</b> {', '.join(sorted(token_status.missing_permissions))}\n"
                text += "🔧 <b>Добавьте новые токены для восстановления работы</b>\n"

        elif not self._token_status_loaded:
            text += "\n🔑 <b>Токены:</b> ⚠️ <b>Ошибка загрузки</b>\n"

        # Shop information
        cabinet_active = getattr(self._wb_cabinet, "active", True) is True
        cabinet_status_human = "Активен" if cabinet_active else "Не активен"
        text += (
            "\n===================================\n"
            f"🏬 <b>Магазин</b>: {self._wb_user_cabinet.name}\n"
            f"🆔 <b>Shop ID</b>: {self._wb_cabinet.shop_id}\n"
            f"📶 <b>Статус магазина в боте</b>: {cabinet_status_human}\n"
        )

        text += """
<a href="https://telegra.ph/Bystryj-start-02-11">Инструкция по быстрому старту работы</a>.
 Подходит для базовой автоматизации.
                """

        return text

    @property
    def keyboard(self):
        return build_shop_main_keyboard(
            self._wb_user_cabinet, self._wb_cabinet, ui_access=self._ui_access
        )

    @staticmethod
    def _format_cashback_snapshot_line(
        snapshot: Mapping[str, int | str | None] | None,
    ) -> str | None:
        parsed = parse_cashback_snapshot(snapshot)
        if parsed is None:
            return None
        exp_part = ""
        if parsed.expiration_msk:
            exp_part = f", сгорят {parsed.expiration_msk.strftime('%d.%m.%Y')}"
        return (
            f"🧾 <b>Cashback</b>: {parsed.total} руб"
            f"{parsed.percent_part}{exp_part}"
        )
    @staticmethod
    async def _get_wb_user_cabinet_with_user_and_wb_cabinet(
        session: AsyncSession,
        wb_user_cabinet_original_id: int,
    ) -> WBUserCabinet:
        """Загрузить WBUserCabinet с user и wb_cabinet (eager load).

        Делает INNER JOIN по relationship-путям и selectinload связанных
        сущностей для меню магазина. В SQLAlchemy 2.0 каждый relationship
        joinится отдельным ``.join(...)`` без второго позиционного onclause.

        Args:
            session: Async SQLAlchemy-сессия.
            wb_user_cabinet_original_id: PK ``WBUserCabinet``.

        Returns:
            ``WBUserCabinet`` с предзагруженными связями.
        """
        stmt = (
            select(WBUserCabinet)
            # SA 2.0: каждый relationship — отдельный .join(); второй
            # позиционный аргумент — onclause, не вторая связь.
            .join(WBUserCabinet.wb_cabinet)
            .join(WBUserCabinet.user)
            .options(
                selectinload(WBUserCabinet.user),
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
                    WBCabinet.adv_settings.and_(AdvSetting.bot_active.is_(True))
                ),
            )
            .where(WBUserCabinet.id == wb_user_cabinet_original_id)
        )

        result = await session.execute(stmt)
        wb_cabinet = result.scalar_one()
        return wb_cabinet
