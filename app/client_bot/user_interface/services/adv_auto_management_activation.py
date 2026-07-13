"""Use-case слой включения/выключения paid auto-management для одной РК.

Оркестрирует billing/token gates, mode transitions и post-commit side effects
(V3 backfill). Значения mode-defaults не задаёт напрямую — только через
``apply_paid_auto_management_transition`` / ``apply_free_mode_transition``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.user_interface.services.auto_management_mode import (
    apply_free_mode_transition,
    apply_paid_auto_management_transition,
)
from app.modules import balance_manager
from app.modules.billing.pricer import Pricer
from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.service_manager.services.v3_status_mode_backfill import (
    backfill_v3_hard_statuses_and_states_consistency,
)
from app.modules.token_monitoring.services.token_info_service import TokenInfoService

pricer = Pricer()

ZERO_BALANCE_MESSAGE = (
    "Недостаточно средств на балансе кабинета для запуска. Пополните баланс."
)
INSUFFICIENT_FOR_DAY_MESSAGE = "Недостаточно средств"
READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE = (
    "У этого токена только права чтения. Автоуправление недоступно. "
    "Вы можете пользоваться аналитикой или заменить токен на ключ с правами "
    "управления продвижением."
)


class PaidActivationBlockReason(StrEnum):
    """Причины отказа в включении paid auto-management (turn_adv_on)."""

    # Баланс + бонусы кабинета <= 0 — включать нечем вообще.
    ZERO_BALANCE = "zero_balance"
    # Баланс > 0, но меньше дневной стоимости одной РК (price_for_adv_for_day).
    INSUFFICIENT_FOR_DAY = "insufficient_for_day"
    # У магазина только read-only WB-токены — автоуправление недоступно.
    READ_ONLY_TOKEN = "read_only_token"


@dataclass(frozen=True)
class PaidActivationEligibility:
    """Результат проверки возможности включить paid auto-management."""

    allowed: bool
    block_reason: PaidActivationBlockReason | None = None


def get_paid_activation_block_message(
    block_reason: PaidActivationBlockReason,
) -> str:
    """Вернуть пользовательское сообщение для причины блокировки активации."""
    if block_reason is PaidActivationBlockReason.ZERO_BALANCE:
        return ZERO_BALANCE_MESSAGE
    if block_reason is PaidActivationBlockReason.INSUFFICIENT_FOR_DAY:
        return INSUFFICIENT_FOR_DAY_MESSAGE
    if block_reason is PaidActivationBlockReason.READ_ONLY_TOKEN:
        return READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE
    raise ValueError(f"Unknown block reason: {block_reason}")


async def _shop_has_read_only_only_tokens(shop_id: str) -> bool:
    """True, если у магазина только активные read-only токены для аналитики."""
    token_status = await TokenInfoService().get_shop_token_status(shop_id)
    has_active_read_only_token = any(
        token.is_read_only and token.is_valid and not token.is_expired
        for token in token_status.all_tokens
    )
    return has_active_read_only_token and not token_status.valid_tokens


async def check_paid_activation_eligibility(
    session: AsyncSession,
    wb_cabinet: WBCabinet,
) -> PaidActivationEligibility:
    """Проверить billing и token gates перед включением paid auto-management.

    Args:
        session: SQLAlchemy-сессия для расчёта тарифа магазина.
        wb_cabinet: Кабинет WB, для которого включают РК.

    Returns:
        ``PaidActivationEligibility`` с флагом разрешения и причиной блокировки.
    """
    tariff_for_month: int | float = await pricer.get_price_for_day_for_shop(
        session, wb_cabinet.shop_id
    )
    price_for_adv_for_day = pricer.get_tariff_for_day(int(tariff_for_month))
    balance, bonus = await balance_manager.get_cabinet_balance_and_bonuses(
        wb_cabinet.id
    )
    sum_balance = balance + bonus
    if sum_balance <= 0:
        return PaidActivationEligibility(
            allowed=False,
            block_reason=PaidActivationBlockReason.ZERO_BALANCE,
        )
    if not sum_balance >= price_for_adv_for_day:
        return PaidActivationEligibility(
            allowed=False,
            block_reason=PaidActivationBlockReason.INSUFFICIENT_FOR_DAY,
        )
    if await _shop_has_read_only_only_tokens(wb_cabinet.shop_id):
        return PaidActivationEligibility(
            allowed=False,
            block_reason=PaidActivationBlockReason.READ_ONLY_TOKEN,
        )
    return PaidActivationEligibility(allowed=True)


async def activate_adv_paid_mode(
    session: AsyncSession,
    adv: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Включить paid auto-management для РК и сохранить изменения в БД.

    Применяет только paid-start transition (без common defaults). После commit
    при переходе на V3 запускает backfill hard-statuses/states consistency.

    Args:
        session: writable SQLAlchemy-сессия с открытой транзакцией.
        adv: Настройки рекламной кампании.
        wb_cabinet: Кабинет WB кампании.

    Side effects:
        PostgreSQL commit; optional V3 backfill job.
    """
    switched_to_v3 = adv.automatic_version != 3
    apply_paid_auto_management_transition(adv, wb_cabinet)
    await session.commit()
    if switched_to_v3:
        _ = await backfill_v3_hard_statuses_and_states_consistency(
            dry_run=False,
            adv_setting_id=adv.id,
        )


async def deactivate_adv_free_mode(
    session: AsyncSession,
    adv: AdvSetting,
    wb_cabinet: WBCabinet,
) -> None:
    """Выключить paid auto-management и перевести РК в FREE overlay.

    Args:
        session: writable SQLAlchemy-сессия.
        adv: Настройки рекламной кампании.
        wb_cabinet: Кабинет WB кампании.

    Side effects:
        PostgreSQL commit.
    """
    apply_free_mode_transition(adv, wb_cabinet)
    await session.commit()


__all__ = [
    "INSUFFICIENT_FOR_DAY_MESSAGE",
    "PaidActivationBlockReason",
    "PaidActivationEligibility",
    "READ_ONLY_TOKEN_BOT_ACTIVE_MESSAGE",
    "ZERO_BALANCE_MESSAGE",
    "activate_adv_paid_mode",
    "check_paid_activation_eligibility",
    "deactivate_adv_free_mode",
    "get_paid_activation_block_message",
]
