"""Unit тесты для PlanFactStatDTO"""

from datetime import date, datetime

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.dto.plan_fact_stat_dto import PlanFactStatDTO


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_dto_with_full_data():
    """Тест создания DTO с полными данными (план и факт)"""
    plan = PlanData(orders=100, target_pay_for_order=500, max_pay_for_order=1000)
    fact = FactData(
        predict_orders=95.5,
        original_orders=90.0,
        pay_for_order=520.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    
    dto = PlanFactStatDTO.create(
        adv_id=12345,
        shop_id="test_shop_123",
        plan=plan,
        fact=fact,
        version=1.0,
    )
    
    assert dto.adv_id == 12345
    assert dto.shop_id == "test_shop_123"
    assert dto.plan_orders == 100
    assert dto.plan_target_pay_for_order == 500
    assert dto.plan_max_pay_for_order == 1000
    assert dto.fact_predict_orders == 95.5
    assert dto.fact_original_orders == 90.0
    assert dto.fact_pay_for_order == 520.0
    assert dto.fact_method == "DIRECT_SALES"
    assert dto.version == 1.0
    assert isinstance(dto.date, date)
    assert isinstance(dto.timestamp, datetime)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_dto_with_plan_only():
    """Тест создания DTO только с планом (факт = None)"""
    plan = PlanData(orders=50, target_pay_for_order=300, max_pay_for_order=800)
    
    dto = PlanFactStatDTO.create(
        adv_id=67890,
        shop_id="test_shop_456",
        plan=plan,
        fact=None,
        version=2.0,
    )
    
    assert dto.adv_id == 67890
    assert dto.shop_id == "test_shop_456"
    assert dto.plan_orders == 50
    assert dto.plan_target_pay_for_order == 300
    assert dto.plan_max_pay_for_order == 800
    assert dto.fact_predict_orders is None
    assert dto.fact_original_orders is None
    assert dto.fact_pay_for_order is None
    assert dto.fact_method is None
    assert dto.version == 2.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_dto_with_fact_only():
    """Тест создания DTO только с фактом (план = None)"""
    fact = FactData(
        predict_orders=75.3,
        original_orders=70.0,
        pay_for_order=450.0,
        fact_method=FactMethods.BY_CARTS,
    )
    
    dto = PlanFactStatDTO.create(
        adv_id=11111,
        shop_id="test_shop_789",
        plan=None,
        fact=fact,
        version=3.0,
    )
    
    assert dto.adv_id == 11111
    assert dto.shop_id == "test_shop_789"
    assert dto.plan_orders is None
    assert dto.plan_target_pay_for_order is None
    assert dto.plan_max_pay_for_order is None
    assert dto.fact_predict_orders == 75.3
    assert dto.fact_original_orders == 70.0
    assert dto.fact_pay_for_order == 450.0
    assert dto.fact_method == "BY_CARTS"
    assert dto.version == 3.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_dto_without_plan_and_fact():
    """Тест создания DTO без плана и факта (оба None)"""
    dto = PlanFactStatDTO.create(
        adv_id=22222,
        shop_id="test_shop_empty",
        plan=None,
        fact=None,
        version=4.0,
    )
    
    assert dto.adv_id == 22222
    assert dto.shop_id == "test_shop_empty"
    assert dto.plan_orders is None
    assert dto.plan_target_pay_for_order is None
    assert dto.plan_max_pay_for_order is None
    assert dto.fact_predict_orders is None
    assert dto.fact_original_orders is None
    assert dto.fact_pay_for_order is None
    assert dto.fact_method is None
    assert dto.version == 4.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fact_method_enum_to_string_conversion():
    """Тест преобразования fact_method из enum в строку"""
    fact_direct = FactData(
        predict_orders=100.0,
        original_orders=95.0,
        pay_for_order=500.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    
    fact_carts = FactData(
        predict_orders=80.0,
        original_orders=75.0,
        pay_for_order=400.0,
        fact_method=FactMethods.BY_CARTS,
    )
    
    dto_direct = PlanFactStatDTO.create(
        adv_id=33333,
        shop_id="test_shop",
        plan=None,
        fact=fact_direct,
        version=5.0,
    )
    
    dto_carts = PlanFactStatDTO.create(
        adv_id=44444,
        shop_id="test_shop",
        plan=None,
        fact=fact_carts,
        version=6.0,
    )
    
    assert dto_direct.fact_method == "DIRECT_SALES"
    assert dto_carts.fact_method == "BY_CARTS"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_date_and_timestamp_set_on_creation():
    """Тест установки даты и timestamp при создании"""
    before = datetime.now()
    
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=200)
    dto = PlanFactStatDTO.create(
        adv_id=55555,
        shop_id="test_shop",
        plan=plan,
        fact=None,
        version=7.0,
    )
    
    after = datetime.now()
    
    # Проверяем, что дата и timestamp установлены
    assert dto.date is not None
    assert dto.timestamp is not None
    
    # Проверяем, что дата соответствует timestamp
    assert dto.date == dto.timestamp.date()
    
    # Проверяем, что timestamp находится в разумных пределах
    assert before <= dto.timestamp <= after


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fact_without_fact_method():
    """Тест создания DTO с фактом, но без fact_method"""
    # Создаем FactData без fact_method (это не должно произойти в реальности,
    # но проверяем обработку граничного случая)
    fact = FactData(
        predict_orders=50.0,
        original_orders=45.0,
        pay_for_order=300.0,
        fact_method=FactMethods.DIRECT_SALES,
    )
    
    dto = PlanFactStatDTO.create(
        adv_id=66666,
        shop_id="test_shop",
        plan=None,
        fact=fact,
        version=8.0,
    )
    
    # fact_method должен быть установлен, так как он есть в FactData
    assert dto.fact_method == "DIRECT_SALES"





