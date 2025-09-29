from dataclasses import dataclass
from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, Field


class NmStats(BaseModel):
    views: int = Field(..., description="Количество просмотров")
    clicks: int = Field(..., description="Количество кликов")
    ctr: float = Field(..., description="Показатель кликабельности, %")
    cpc: float = Field(..., description="Средняя стоимость клика, ₽")
    sum: float = Field(..., description="Затраты, ₽")
    atbs: int = Field(..., description="Количество добавлений товаров в корзину")
    orders: int = Field(..., description="Количество заказов")
    cr: float = Field(..., description="Конверсия (CR), %")
    shks: int = Field(..., description="Количество заказанных товаров, шт.")
    sum_price: float = Field(..., description="Сумма заказов, ₽")
    name: str = Field(..., description="Название товара")
    nmId: int = Field(..., description="ID товара")


class AppStats(BaseModel):
    views: int = Field(..., description="Количество просмотров")
    clicks: int = Field(..., description="Количество кликов")
    ctr: float = Field(..., description="Показатель кликабельности, %")
    cpc: float = Field(..., description="Средняя стоимость клика, ₽")
    sum: float = Field(..., description="Затраты, ₽")
    atbs: int = Field(..., description="Количество добавлений товаров в корзину")
    orders: int = Field(..., description="Количество заказов")
    cr: float = Field(..., description="Конверсия (CR), %")
    shks: int = Field(..., description="Количество заказанных товаров, шт.")
    sum_price: float = Field(..., description="Сумма заказов, ₽")
    appType: int = Field(..., description="Тип приложения")
    nm: list[NmStats] = Field(..., description="Информация о товаре")


class DayStats(BaseModel):
    date: datetime = Field(..., description="Дата, за которую представлены данные")
    views: int = Field(..., description="Количество просмотров")
    clicks: int = Field(..., description="Количество кликов")
    ctr: float = Field(..., description="Показатель кликабельности, %")
    cpc: float = Field(..., description="Средняя стоимость клика, ₽")
    sum: float = Field(..., description="Затраты, ₽")
    atbs: int = Field(..., description="Количество добавлений товаров в корзину")
    orders: int = Field(..., description="Количество заказов")
    cr: float = Field(..., description="Конверсия (CR), %")
    shks: int = Field(..., description="Количество заказанных товаров, шт.")
    sum_price: float = Field(..., description="Сумма заказов, ₽")
    # apps: List[AppStats] = Field(..., description="Информация о платформе")


class BoosterStats(BaseModel):
    date: str = Field(..., description="Дата, за которую предоставлены данные")
    nm: int = Field(..., description="Артикул WB")
    avg_position: int = Field(
        ...,
        description="Средняя позиция товара на страницах поисковой выдачи и каталога",
    )


@dataclass
class SmallFullAdvStatPerDay:
    date: date
    views: int
    clicks: int
    spend: float
    added_to_cart: int
    orders: int
    sum_price: float  # deprecated

    @property
    def mean_pay_for_order(self) -> float:
        orders = max(self.orders, 1)
        return self.spend / orders


@dataclass
class SmallFullAdvStat:
    views: int
    clicks: int
    spend: float
    added_to_cart: int
    orders: int
    sum_price: float


class FullAdvStat(BaseModel):
    dates: list[str] = Field(..., description="Даты, за которые необходимо выдать информацию")
    views: int = Field(..., description="Количество просмотров за все дни")
    clicks: int = Field(..., description="Количество кликов за все дни")
    ctr: float = Field(..., description="Показатель кликабельности, % за все дни")
    cpc: float = Field(..., description="Средняя стоимость клика, ₽ за все дни")
    sum: float = Field(..., description="Затраты, ₽ за все дни")
    atbs: int = Field(..., description="Количество добавлений товаров в корзину за все дни")
    orders: int = Field(..., description="Количество заказов за все дни")
    cr: float = Field(..., description="Конверсия (CR), % за все дни")
    shks: int = Field(..., description="Количество заказанных товаров, шт. за все дни")
    sum_price: float = Field(..., description="Сумма заказов, ₽ за все дни")
    days: list[DayStats] = Field(..., description="Статистика по дням")
    boosterStats: list[BoosterStats] | None = Field(
        None, description="Информация о позициях товаров"
    )
    advertId: int = Field(..., description="ID рекламного объявления")
