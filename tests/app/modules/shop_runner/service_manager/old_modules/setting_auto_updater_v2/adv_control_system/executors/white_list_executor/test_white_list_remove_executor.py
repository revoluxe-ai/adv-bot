"""Тесты для WhiteListRemoveExecutor с поддержкой rec_system_mode."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.data_classes.data_classes import (
    ExecutionResult,
    PipelineContext,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    PlanData,
    FactData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.executors.white_list_executor.white_list_remove_executor import (
    WhiteListRemoveExecutor,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


def create_mock_keyword(
    keyword_id: int,
    text: str,
    hard_status: int = 2,
    above_rec_conversion: bool | None = None,
    conversion_without_cpm: float = 0.05,
    rating_by_orders: float = 10.0,
    pay_for_order: float = 100.0,
    best_keyword_status: bool = False,
) -> CalculatedKeyword:
    """Создает мок CalculatedKeyword."""
    keyword = MagicMock(spec=CalculatedKeyword)
    keyword.keyword_setting_original_id = keyword_id
    keyword.text = text
    keyword.hard_status = hard_status
    keyword.above_rec_conversion = above_rec_conversion
    keyword.conversion_without_cpm = conversion_without_cpm
    keyword.rating_by_orders = rating_by_orders
    keyword.pay_for_order_by_current_cpm = pay_for_order
    keyword.best_keyword_status = best_keyword_status
    keyword.status = KeywordStatus.GOOD
    return keyword


def create_mock_context(
    rec_system_mode_active: bool = False,
    white_list_control_enabled: bool = True,
    keywords: list[CalculatedKeyword] | None = None,
    plan: PlanData | None = None,
    fact: FactData | None = None,
) -> PipelineContext:
    """Создает мок PipelineContext."""
    ctx = MagicMock(spec=PipelineContext)
    
    # Mock complex_adv
    complex_adv = MagicMock()
    complex_adv.rec_system_promotion_mode_active = rec_system_mode_active
    complex_adv.is_white_list_control_enabled = white_list_control_enabled
    complex_adv.get_keywords = AsyncMock(return_value=keywords or [])
    
    # Mock adv_setting
    adv_setting = MagicMock()
    adv_setting.adv_id = 123
    complex_adv.adv_setting = adv_setting
    
    ctx.complex_adv = complex_adv
    
    # Mock session
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    ctx.session = session
    
    # PlanData and FactData
    ctx.plan = plan
    ctx.fact = fact
    
    return ctx


@pytest.mark.asyncio
async def test_removes_keywords_with_below_rec_conversion():
    """Проверка удаления ключей с above_rec_conversion = False при активном rec_system_mode."""
    # Arrange
    keywords = [
        create_mock_keyword(1, "keyword1", above_rec_conversion=False, conversion_without_cpm=0.01),
        create_mock_keyword(2, "keyword2", above_rec_conversion=False, conversion_without_cpm=0.02),
        create_mock_keyword(3, "keyword3", above_rec_conversion=True, conversion_without_cpm=0.05),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=True,
        keywords=keywords,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    assert result.success is True
    assert result.used_power == 2  # Удалено 2 ключа с above_rec_conversion=False
    assert result.efficiency == pytest.approx(2/3, rel=1e-6)  # 2 из 3 ключей
    
    # Проверяем, что был вызван execute для удаления
    ctx.session.execute.assert_called_once()
    ctx.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_skips_rec_check_when_mode_disabled():
    """Проверка, что при выключенном rec_system_mode проверка не применяется."""
    # Arrange
    plan = MagicMock(spec=PlanData)
    plan.target_pay_for_order = 100.0
    plan.max_pay_for_order = 150.0
    plan.orders = 10
    
    fact = MagicMock(spec=FactData)
    fact.predict_orders = 12.0
    
    keywords = [
        create_mock_keyword(1, "keyword1", above_rec_conversion=False, pay_for_order=80.0),
        create_mock_keyword(2, "keyword2", above_rec_conversion=False, pay_for_order=90.0),
        create_mock_keyword(3, "keyword3", above_rec_conversion=True, pay_for_order=120.0),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=False,  # Режим выключен
        keywords=keywords,
        plan=plan,
        fact=fact,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    # Должен удалиться только keyword3 с pay_for_order > target (100.0)
    assert result.success is True
    assert result.used_power == 1  # Удален только keyword3
    
    ctx.session.execute.assert_called_once()
    ctx.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_rec_check_has_priority_over_pay_for_order():
    """Проверка приоритета rec_conversion над pay_for_order."""
    # Arrange
    plan = MagicMock(spec=PlanData)
    plan.target_pay_for_order = 100.0
    plan.max_pay_for_order = 150.0
    plan.orders = 10
    
    fact = MagicMock(spec=FactData)
    fact.predict_orders = 12.0
    
    keywords = [
        # Ключ с низкой rec_conversion, но хорошим pay_for_order
        create_mock_keyword(1, "keyword1", above_rec_conversion=False, pay_for_order=80.0),
        # Ключ с хорошей rec_conversion, но плохим pay_for_order
        create_mock_keyword(2, "keyword2", above_rec_conversion=True, pay_for_order=120.0),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=True,
        keywords=keywords,
        plan=plan,
        fact=fact,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    # Должен удалиться только keyword1 (приоритет rec_conversion)
    # keyword2 не удаляется, т.к. проверка pay_for_order не выполняется после rec_check
    assert result.success is True
    assert result.used_power == 1  # Удален только keyword1
    
    ctx.session.execute.assert_called_once()
    ctx.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_anti_drain_ignores_rec_conversion():
    """Проверка, что в анти-слив-режиме rec_conversion игнорируется."""
    # Arrange
    keywords = [
        create_mock_keyword(1, "keyword1", above_rec_conversion=False, rating_by_orders=5.0),
        create_mock_keyword(2, "keyword2", above_rec_conversion=False, rating_by_orders=10.0),  # Лучший
        create_mock_keyword(3, "keyword3", above_rec_conversion=True, rating_by_orders=3.0),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=True,
        keywords=keywords,
        plan=None,  # Нет плана - анти-слив режим
        fact=None,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    # В анти-слив режиме удаляются все кроме лучшего (keyword2)
    # Игнорируется above_rec_conversion
    assert result.success is True
    assert result.used_power == 2  # Удалено 2 ключа (keyword1 и keyword3)
    
    ctx.session.execute.assert_called_once()
    ctx.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_no_removal_when_no_keywords_below_rec_conversion():
    """Проверка, что не происходит удаления, если нет ключей с above_rec_conversion = False."""
    # Arrange
    plan = MagicMock(spec=PlanData)
    plan.target_pay_for_order = 100.0
    plan.max_pay_for_order = 150.0
    plan.orders = 10
    
    fact = MagicMock(spec=FactData)
    fact.predict_orders = 12.0
    
    keywords = [
        create_mock_keyword(1, "keyword1", above_rec_conversion=True, pay_for_order=80.0),
        create_mock_keyword(2, "keyword2", above_rec_conversion=True, pay_for_order=90.0),
        create_mock_keyword(3, "keyword3", above_rec_conversion=True, pay_for_order=120.0),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=True,
        keywords=keywords,
        plan=plan,
        fact=fact,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    # Нет ключей с above_rec_conversion=False, продолжаем с обычной логикой
    # Должен удалиться keyword3 с pay_for_order > target
    assert result.success is True
    assert result.used_power == 1  # Удален только keyword3
    
    ctx.session.execute.assert_called_once()
    ctx.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_skips_when_white_list_control_disabled():
    """Проверка, что executor не работает при выключенном управлении белым списком."""
    # Arrange
    keywords = [
        create_mock_keyword(1, "keyword1", above_rec_conversion=False),
    ]
    
    ctx = create_mock_context(
        rec_system_mode_active=True,
        white_list_control_enabled=False,  # Управление выключено
        keywords=keywords,
    )
    
    executor = WhiteListRemoveExecutor()
    
    # Act
    result = await executor.execute(ctx)
    
    # Assert
    assert result.success is False
    assert result.used_power == 0
    
    ctx.session.execute.assert_not_called()
    ctx.session.commit.assert_not_called()
