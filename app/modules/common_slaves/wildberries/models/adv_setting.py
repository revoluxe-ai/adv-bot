import typing
from enum import Enum
import re
from sqlalchemy import (
    BIGINT, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Index, text
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.settings import settings
from app.utils.db.base import BaseTable
from app.utils.db.assoc_tables import favorite_advs_association
from .enums import OrdersSourceForAutoMode
if typing.TYPE_CHECKING:
    from app.utils.db.models import User
    from .wb_cabinet import WBCabinet
    from .wb_card import WBCard
    from .adv_keyword import AdvKeyword
    from .keyword_setting import KeywordSetting



class AdvSetting(BaseTable):
    # TODO: Модель поделена между микросервисами и требует рефакторинга!!!!
    # Не менять поля до рефакторина! По уму: вынести всю работу с базами в один микросервис и прикрутить GRPC-DTO
    class ActiveStatuses(Enum):
        DONE = "done"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self._search_adv_id: int = None
        self._worst_promo_position = None

    def __repr__(self):
        return (f"name: {self.name}, adverdId: {self.adv_id},"
                f" bot_active: {self.bot_active}, active_status: {self.active_status}")

    favorite_users: Mapped[list['User']] = relationship(
        "User", secondary=favorite_advs_association, back_populates="favorites_advs"
    )
    adv_id: Mapped[int] = mapped_column(
        BIGINT(),
        unique=True,
        nullable=True,
    )  # Автоматическая рекламная кампания
    name = mapped_column(String, nullable=False)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, ForeignKey("wbcabinet.id"), nullable=False)
    wb_cabinet: Mapped['WBCabinet'] = relationship("WBCabinet", back_populates="adv_settings", lazy="joined")
    wb_cards: Mapped[list['WBCard']] = relationship(
        "WBCard",
        back_populates="adv_setting",
        cascade="all,delete-orphan",
        uselist=True,
    )  # Изменено на множественное число
    active_status: Mapped[str] = mapped_column(String, default=False)
    adv_keywords: Mapped[list['AdvKeyword']] = relationship(
        "AdvKeyword",
        cascade="all, delete-orphan",
        back_populates="adv_setting",
        uselist=True,
    )
    bot_active: Mapped[bool] = mapped_column(Boolean, default=False)
    nmids: Mapped[list[int]] = mapped_column(JSONB, default=[])
    keyword_settings: Mapped[list["KeywordSetting"]] = relationship(
        "KeywordSetting",
        cascade="all, delete-orphan",
        back_populates="adv_setting",
        uselist=True,
    )
    pass_days = Column(Integer, default=30)
    boost = Column(Float, server_default=text("1"))
    type: Mapped[int] = mapped_column(Integer, nullable=True)
    hard_min_ctr = Column(
        Float,
        nullable=True,
        default=settings.DEFAULT_MIN_CTR,
        server_default=text(str(settings.DEFAULT_MIN_CTR)),
    )
    max_cpc = Column(Float, nullable=True)
    min_views_for_ml_predict = Column(Integer, nullable=True, server_default=text("0"))
    payments: Mapped[list['AdvPayment']] = relationship("AdvPayment", back_populates="adv_setting", uselist=True)
    parsing_active = mapped_column(Boolean, default=False)
    last_update = mapped_column(DateTime, nullable=True)
    bidder_active: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    max_cpm = mapped_column(Integer, nullable=True)
    max_place = mapped_column(Integer, nullable=True)
    min_block_position = mapped_column(Integer, nullable=True, default=0)
    clusters_mode = mapped_column(Boolean, nullable=True, default=True)
    target_ctr_mode = mapped_column(Boolean, nullable=True, default=False)
    hide_small_query_keywords = mapped_column(Integer, nullable=True, default=0)
    target_ctr_mode_strategy = mapped_column(String, nullable=True, default="forward")  # forward, keep
    new_auto_min_ctr_mode = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    reset_place = mapped_column(Boolean, nullable=True, default=True, server_default=text("true"))
    _search_adv_id: Mapped[int] = mapped_column(Integer, nullable=True)
    bidder_step = mapped_column(Integer, nullable=True, default=settings.BIDDER_STEP)
    exponent_predict_ctr = mapped_column(
        Float,
        nullable=False,
        default=settings.DEFAULT_CTR_EXPONENTA,
        server_default=text(str(settings.DEFAULT_CTR_EXPONENTA)),
    )

    auction_boost_all_phrase_mode = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    plan_for_sales_for_day = mapped_column(Integer, nullable=True, default=None)
    target_price_for_order = mapped_column(Float, nullable=True, default=None)

    max_price_for_order = mapped_column(Float, nullable=True, default=None)
    cpm = mapped_column(Integer, nullable=True, default=None)
    bidder_for_auto = mapped_column(Boolean, nullable=True, default=True, server_default="true")

    auto_update_white_list: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False, server_default="false")

    auto_update_target_place: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )
    max_balance_adding_for_day: Mapped[int] = mapped_column(Integer, nullable=True, default=0, server_default="0")

    auto_adv_target_status = mapped_column(Boolean, nullable=True, default=None)
    auction_adv_target_status = mapped_column(Boolean, nullable=True, default=None)
    auto_add_only_relevant_phrase: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=True, server_default=text("true")
    )

    orders_source_for_auto_mode: Mapped[OrdersSourceForAutoMode] = mapped_column(
        SAEnum(OrdersSourceForAutoMode),
        nullable=True,
        default=OrdersSourceForAutoMode.COMMON_STATISTIC,  # экземпляр Enum
        server_default=OrdersSourceForAutoMode.COMMON_STATISTIC.name  # строка
    )

    __table_args__ = (
        # Составной индекс для основного запроса
        Index(
            "ix_adv_settings_cabinet_type_update",
            "wb_cabinet_id",
            "type",
            "last_update",
        ),
        # Индекс для поиска по cabinet_id
        Index("ix_adv_settings_cabinet_id", "wb_cabinet_id"),
        # Добавляем новый индекс для оптимизации запросов
        # Индекс для type, если он часто используется в запросах
        Index("ix_adv_settings_type", "type"),
        Index("ix_advsetting_adv_id", "adv_id"),
        Index("ix_advsetting_active_status", "active_status"),
        Index("ix_advsetting_cabinet_bot_active", "wb_cabinet_id", "bot_active"),
        Index(
            "ix_advsetting_name_pattern",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_name__nmids__search_adv_id", "name", "nmids", "_search_adv_id"),
        Index("ix_advsetting_bot_active", "bot_active"),
    )

    @property
    def auction_adv_id(self) -> int | None:
        return self.search_adv_id

    @property
    def search_adv_id(self) -> int | None:  # Аукцион
        if self._search_adv_id:
            return self._search_adv_id
        if not self.name:
            return None
        name = self.name.replace(" ", "")
        pattern = re.compile(r"<!-\[(\d+)\]-!>")
        match = re.search(pattern, name)
        if not match:
            return None
        return int(match.group(1))

    # @search_adv_id.setter
    # def search_adv_id(self, value: int):
    #     assert isinstance(value, int)
    #     self._search_adv_id = value

    # @search_adv_id.setter
    # def search_adv_id(self, value: int) -> None:
    #     assert isinstance(value, int)
    #     self._search_adv_id = value

    @property
    def max_pay_for_order(self) -> int | None:
        pattern = re.compile(r"<MAX_PAY>(\d+)!?</MAX_PAY>")  # Добавили !? для необязательного символа "!"
        match = re.search(pattern, self.name)
        if match:
            return int(match.group(1))
        return None

    @property
    def auto_max_bid(self) -> bool:
        pattern = re.compile(r"<MAX_PAY>(\d+)!?</MAX_PAY>")  # Используем тот же паттерн, чтобы найти!
        match = re.search(pattern, self.name)
        if match and "!" in match.group(0):  # Проверяем, есть ли "!" в найденной строке
            return True
        return False

    @property
    def worst_promo_position(self):
        try:
            return self._worst_promo_position
        except:
            return None

    @worst_promo_position.setter
    def worst_promo_position(self, value):
        self._worst_promo_position = value