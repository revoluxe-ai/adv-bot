from unittest.mock import AsyncMock, patch, MagicMock

import pytest

import app.modules.billing.billing as billing

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_redis_lock():
    lock = AsyncMock()
    lock.acquire_lock.return_value = True
    lock.release_lock.return_value = None
    lock.is_locked.return_value = False
    return lock


@pytest.fixture
def mock_redis_manager():
    mgr = AsyncMock()
    mgr.get_billing_process_for_day.return_value = False
    mgr.set_billing_process_for_day.return_value = None
    return mgr


@pytest.fixture
def mock_pricer():
    pricer = AsyncMock()
    pricer.get_price_for_day_for_shop.return_value = 100.0
    return pricer


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_cabinets():
    # Два кабинета с активными кампаниями
    adv1 = MagicMock()
    adv1.id = 1
    adv1.bot_active = True
    adv1.wb_cabinet_id = 10
    adv2 = MagicMock()
    adv2.id = 2
    adv2.bot_active = True
    adv2.wb_cabinet_id = 20
    cab1 = MagicMock()
    cab1.id = 10
    cab1.shop_id = 100
    cab1.calculated_bonus = 200.0
    cab1.calculated_balance = 0.0
    cab1.adv_settings = [adv1]
    cab2 = MagicMock()
    cab2.id = 20
    cab2.shop_id = 200
    cab2.calculated_bonus = 0.0
    cab2.calculated_balance = 200.0
    cab2.adv_settings = [adv2]
    return [cab1, cab2]


@patch("app.modules.billing.billing.sm")
async def test_parallel_billing_all_shops(
    mock_sm, mock_redis_lock, mock_redis_manager, mock_pricer, mock_cabinets
):
    # Мокаем сессию и preload выборку кабинетов
    preload_session = AsyncMock()
    preload_session.execute.return_value = MagicMock()
    preload_session.execute.return_value.all.return_value = [
        (cab.id,) for cab in mock_cabinets
    ]
    mock_sm.return_value.__aenter__.return_value = preload_session
    # Мокаем обработку одного кабинета (внутри _process_single_cabinet)
    with patch(
        "app.modules.billing.billing._process_single_cabinet", new_callable=AsyncMock
    ) as mock_proc:
        mock_proc.side_effect = (
            lambda session, cabinet_id, current_dt, pricer, redis_manager: {
                "cabinet_id": cabinet_id,
                "processed": True,
                "payment_successful": True,
                "reason": "success",
                "campaigns": 1,
                "price_for_day": 100.0,
            }
        )
        await billing.process_payment_for_advs(
            redis_manager=mock_redis_manager,
            redis_lock=mock_redis_lock,
            global_ttl=900,
        )
        # Проверяем, что обработка была по всем кабинетам
        assert mock_proc.call_count == 2
        called_ids = {call.kwargs["cabinet_id"] for call in mock_proc.call_args_list}
        assert called_ids == {10, 20}


@patch("app.modules.billing.billing.sm")
async def test_billing_global_lock_blocks_run(
    mock_sm, mock_redis_lock, mock_redis_manager, mock_pricer
):
    mock_redis_lock.acquire_lock.return_value = False
    # Не должен быть вызван ни один процессинг
    with patch(
        "app.modules.billing.billing._process_payment_for_advs", new_callable=AsyncMock
    ) as mock_proc:
        await billing.process_payment_for_advs(
            redis_manager=mock_redis_manager,
            redis_lock=mock_redis_lock,
            global_ttl=900,
        )
        mock_proc.assert_not_called()


@patch("app.modules.billing.billing.sm")
async def test_billing_ttl_none_means_no_expiry(
    mock_sm, mock_redis_lock, mock_redis_manager, mock_pricer, mock_cabinets
):
    preload_session = AsyncMock()
    preload_session.execute.return_value = MagicMock()
    preload_session.execute.return_value.all.return_value = [
        (cab.id,) for cab in mock_cabinets
    ]
    mock_sm.return_value.__aenter__.return_value = preload_session
    with patch(
        "app.modules.billing.billing._process_single_cabinet", new_callable=AsyncMock
    ) as mock_proc:
        mock_proc.side_effect = (
            lambda session, cabinet_id, current_dt, pricer, redis_manager: {
                "cabinet_id": cabinet_id,
                "processed": True,
                "payment_successful": True,
                "reason": "success",
                "campaigns": 1,
                "price_for_day": 100.0,
            }
        )
        # TTL не передаём, должен быть default (3600) внутри функции
        await billing.process_payment_for_advs(
            redis_manager=mock_redis_manager,
            redis_lock=mock_redis_lock,
        )
        # Проверяем, что глобальный лок был взят
        mock_redis_lock.acquire_lock.assert_called()
