import pytest
from sqlalchemy.future import select
from tests.mocks import (
    MockUser, 
    MockAdvSetting, 
    MockWBCabinet, 
    MockWBToken,
    favorite_advs_association
)

@pytest.fixture
def mock_user():
    """Фикстура для создания тестового пользователя"""
    return MockUser(
        id=1,
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User"
    )

@pytest.fixture
def mock_wb_cabinet():
    """Фикстура для создания тестового кабинета WB"""
    return MockWBCabinet(
        id=1,
        shop_id="test_shop_id",
        active=True
    )

@pytest.fixture
def mock_wb_token(mock_user):
    """Фикстура для создания тестового токена WB"""
    return MockWBToken(
        id=1,
        user_id=mock_user.id,
        token="test_token",
        is_valid=True
    )

@pytest.fixture
def mock_adv_setting(mock_user, mock_wb_token):
    """Фикстура для создания тестовой настройки рекламы"""
    return MockAdvSetting(
        id=1,
        user_id=mock_user.id,
        wb_token_id=mock_wb_token.id,
        campaign_name="Test Campaign",
        budget=1000.0,
        daily_budget=100.0,
        bid=50.0,
        status="active"
    )

@pytest.mark.asyncio
async def test_add_adv_to_favorites(test_async_db, mock_user, mock_adv_setting):
    """Тест добавления рекламной настройки в избранное"""
    async with test_async_db() as session:
        # Arrange
        session.add(mock_user)
        session.add(mock_adv_setting)
        await session.commit()

        # Act
        # Добавляем рекламную настройку в избранное пользователя
        stmt = favorite_advs_association.insert().values(
            user_id=mock_user.id,
            adv_setting_id=mock_adv_setting.id
        )
        await session.execute(stmt)
        await session.commit()

        # Assert
        # Проверяем, что связь создана
        stmt = select(favorite_advs_association).where(
            favorite_advs_association.c.user_id == mock_user.id,
            favorite_advs_association.c.adv_setting_id == mock_adv_setting.id
        )
        result = await session.execute(stmt)
        assert result.first() is not None

@pytest.mark.asyncio
async def test_remove_adv_from_favorites(test_async_db, mock_user, mock_adv_setting):
    """Тест удаления рекламной настройки из избранного"""
    async with test_async_db() as session:
        # Arrange
        session.add(mock_user)
        session.add(mock_adv_setting)
        await session.commit()

        # Сначала добавляем в избранное
        stmt = favorite_advs_association.insert().values(
            user_id=mock_user.id,
            adv_setting_id=mock_adv_setting.id
        )
        await session.execute(stmt)
        await session.commit()

        # Act
        # Удаляем из избранного
        stmt = favorite_advs_association.delete().where(
            favorite_advs_association.c.user_id == mock_user.id,
            favorite_advs_association.c.adv_setting_id == mock_adv_setting.id
        )
        await session.execute(stmt)
        await session.commit()

        # Assert
        # Проверяем, что связь удалена
        stmt = select(favorite_advs_association).where(
            favorite_advs_association.c.user_id == mock_user.id,
            favorite_advs_association.c.adv_setting_id == mock_adv_setting.id
        )
        result = await session.execute(stmt)
        assert result.first() is None

@pytest.mark.asyncio
async def test_get_user_favorite_advs(test_async_db, mock_user, mock_adv_setting):
    """Тест получения списка избранных рекламных настроек пользователя"""
    async with test_async_db() as session:
        # Arrange
        session.add(mock_user)
        session.add(mock_adv_setting)
        await session.commit()

        # Добавляем в избранное
        stmt = favorite_advs_association.insert().values(
            user_id=mock_user.id,
            adv_setting_id=mock_adv_setting.id
        )
        await session.execute(stmt)
        await session.commit()

        # Act
        # Получаем список избранных настроек
        stmt = select(MockAdvSetting).join(
            favorite_advs_association,
            favorite_advs_association.c.adv_setting_id == MockAdvSetting.id
        ).where(
            favorite_advs_association.c.user_id == mock_user.id
        )
        result = await session.execute(stmt)
        favorite_advs = result.scalars().all()

        # Assert
        assert len(favorite_advs) == 1
        assert favorite_advs[0].id == mock_adv_setting.id
        assert favorite_advs[0].campaign_name == "Test Campaign"

@pytest.mark.asyncio
async def test_multiple_users_favorite_same_adv(test_async_db, mock_user, mock_adv_setting):
    """Тест добавления одной рекламной настройки в избранное нескольких пользователей"""
    async with test_async_db() as session:
        # Arrange
        session.add(mock_user)
        session.add(mock_adv_setting)
        
        # Создаем второго пользователя
        second_user = MockUser(
            id=2,
            telegram_id=987654321,
            username="second_user"
        )
        session.add(second_user)
        await session.commit()

        # Act
        # Добавляем рекламную настройку в избранное обоих пользователей
        for user_id in [mock_user.id, second_user.id]:
            stmt = favorite_advs_association.insert().values(
                user_id=user_id,
                adv_setting_id=mock_adv_setting.id
            )
            await session.execute(stmt)
        await session.commit()

        # Assert
        # Проверяем для каждого пользователя
        for user_id in [mock_user.id, second_user.id]:
            stmt = select(favorite_advs_association).where(
                favorite_advs_association.c.user_id == user_id,
                favorite_advs_association.c.adv_setting_id == mock_adv_setting.id
            )
            result = await session.execute(stmt)
            assert result.first() is not None 