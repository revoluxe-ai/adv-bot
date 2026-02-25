from __future__ import annotations
import datetime
import json
import logging
import re
import typing
from enum import Enum

import jwt
from jwt import DecodeError
from sqlalchemy import (
    BIGINT,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.modules.common_slaves.wildberries.exceptions import NotValidTokenError
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode, TargetPositionMode
from .bidder_mode import BidderMode
from .fact_methods_enum import FactMethods
from .wb_auto_budget_topup import WBAutoBudgetTopUp
from app.settings import settings
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.base import BaseTable
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from .white_list_mode import WhiteListMode

# Ensure billing models (AdvPayment) are imported and registered before mapper configuration
try:
    # TODO: Надо разобраться что это за конструкцию такая, и постараться ее убрать без рейса исключения
    from app.modules.billing import models as _billing_models  # noqa: F401
except Exception:  # noqa
    # In minimal test contexts billing may be absent; relationship will fallback to string resolution
    pass

if typing.TYPE_CHECKING:
    from app.modules.billing.models import AdvPayment
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

logger = logging.getLogger(__name__)


class PredictCTRMode(Enum):
    V1 = "v1"
    V2 = "v2"


class BidderCoroutineType(str, Enum):
    """Тип корутины для обработки биддера."""

    OLD_UPDATE_CPM_BIDDER = "OLD_UPDATE_CPM_BIDDER"
    UPDATE_CLUSTER_BIDS = "UPDATE_CLUSTER_BIDS"


_sm = get_async_session_maker


class WBUserCabinet(BaseTable):
    wb_cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="wb_user_cabinets"
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped[User] = relationship("User", back_populates="wb_user_cabinets")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    __table_args__ = (
        UniqueConstraint("wb_cabinet_id", "user_id", name="_wb_cabinet_id_user_id_uc"),
        Index("idx_wb_user_cabinet_user_id", "user_id"),
        Index("idx_wb_user_cabinet_cabinet_id", "wb_cabinet_id"),
    )


class WBBalancePayment(BaseTable):
    """Модель для хранения информации о пополнениях баланса"""

    __tablename__ = "wbbalancepayment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="balance_payments"
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    # Тип операции для унификации с бонусами: 'add', 'subtract', 'auto_subtract', 'reset' (если понадобится)
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'subtract'")
    )
    __table_args__ = (
        Index("idx_wb_balance_payment_cabinet_id", "wb_cabinet_id"),
        Index("idx_wb_balance_payment_date", "transaction_date_time"),
        Index("idx_wb_balance_payment_operation", "operation_type"),
        Index(
            "idx_unique_daily_auto_balance_charge",
            "wb_cabinet_id",
            text("DATE(transaction_date_time)"),
            unique=True,
            postgresql_where=text("operation_type = 'auto_subtract' AND amount < 0"),
        ),
    )


class WBBonusPayment(BaseTable):
    """Модель для хранения информации о бонусах"""

    __tablename__ = "wbbonuspayment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="bonus_payments"
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    # 'add', 'subtract', 'reset', 'auto_subtract'
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'subtract'")
    )
    admin_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )

    __table_args__ = (
        Index("idx_wb_bonus_payment_cabinet_id", "wb_cabinet_id"),
        Index("idx_wb_bonus_payment_date", "transaction_date_time"),
        Index("idx_wb_bonus_payment_admin", "admin_user_id"),
        Index("idx_wb_bonus_payment_operation", "operation_type"),
        Index(
            "idx_unique_daily_auto_bonus_charge",
            "wb_cabinet_id",
            text("DATE(transaction_date_time)"),
            unique=True,
            postgresql_where=text(
                "operation_type = 'auto_subtract' AND amount < 0 AND admin_user_id IS NULL"
            ),
        ),
    )


class WBCategory(BaseTable):
    cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="wb_categories"
    )
    wb_category_name: Mapped[str] = mapped_column(String, nullable=False)
    wb_cards: Mapped[list["WBCard"]] = relationship(
        "WBCard", back_populates="wb_category", uselist=True
    )
    __table_args__ = (Index("ix_wb_category_name", "wb_category_name"),)


class WBToken(BaseTable):
    def __repr__(self) -> str:
        return f"user_id: {self.user_id}"

    api_key: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user: Mapped[User] = relationship("User", back_populates="wb_tokens", lazy="joined")
    active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    shop_id: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (
        UniqueConstraint("api_key", "user_id", name="_api_key_user_id_uc"),
        Index("idx_shop_id", "shop_id"),
    )

    @property
    def hash(self):
        return hash(self.api_key)

    @property
    def __payload(self) -> dict[str, object]:
        try:
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            if not isinstance(result, dict):
                raise NotValidTokenError
            return  result
        except Exception:
            raise NotValidTokenError

    def check_valid(self) -> bool:
        try:
            assert self.api_key
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            return bool(result)
        except (ValueError, DecodeError):
            return False

    def get_payload(self, key: str) -> str | int | None:
        payload = self.__payload
        value = payload.get(key)
        if isinstance(value, (str | int)) or value is None:
            return value
        return None

    @property
    def __expires(self) -> datetime.datetime:
        exp = self.__payload.get("exp")
        if isinstance(exp, (int | float | str)):
            # Make the datetime timezone-aware (UTC)
            return datetime.datetime.fromtimestamp(int(exp), tz=datetime.UTC)
        raise NotValidTokenError

    @property
    def expires(self) -> datetime.datetime:
        return self.__expires

    def get_shop_id_from_token(self) -> str:
        sid = self.get_payload("sid")
        if isinstance(sid, str):
            return sid
        raise NotValidTokenError

    @property
    def read_only(self) -> bool:
        # Проверяем, содержится ли категория "Токен только на чтение" в категориях
        return "Токен только на чтение" in self.categories

    @property
    def categories(self) -> set[str]:
        categories_map = {
            1: "Контент",
            2: "Аналитика",
            3: "Цены и скидки",
            4: "Маркетплейс",
            5: "Статистика",
            6: "Продвижение",
            7: "Вопросы и отзывы",
            8: "Рекомендации",
            30: "Токен только на чтение",
        }
        s = int(self.get_payload("s"))
        categories = set()
        for bit_position, category_name in categories_map.items():
            if s & (1 << bit_position):
                categories.add(category_name)
        return categories

    @property
    def is_expired(self) -> bool:
        """Проверяет, истёк ли токен"""
        try:
            # Compare using timezone-aware UTC now
            return datetime.datetime.now(datetime.UTC) >= self.__expires
        except Exception:  # noqa
            return (
                True  # Если нет exp в payload или ошибка — считаем токен просроченным
            )


class AdvKeyword(BaseTable):
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"), nullable=False)
    adv_setting = relationship("AdvSetting", back_populates="adv_keywords")
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0)
    add_to_db = Column(Boolean, default=False)
    keyword_setting_id = Column(
        Integer, ForeignKey("keywordsetting.id"), nullable=False
    )
    keyword_setting = relationship("KeywordSetting", back_populates="adv_keywords")
    __table_args__ = (
        UniqueConstraint(
            "text", "date", "adv_setting_id", name="_text_date_adv_setting_id_uc"
        ),
    )


class WBCard(BaseTable):
    nmid: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    offer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    wb_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("wbcategory.id"), nullable=True
    )
    wb_category: Mapped[WBCategory] = relationship(
        "WBCategory", back_populates="wb_cards", lazy="joined"
    )
    json: Mapped[str | None] = mapped_column(JSONB, nullable=True)
    wb_cabinet_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=True
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="wb_cards"
    )
    adv_setting_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("advsetting.id"), nullable=True
    )
    adv_setting: Mapped["AdvSetting"] = relationship(
        "AdvSetting", back_populates="wb_cards"
    )
    updated: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    add_to_db: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )

    @property
    def card_json(self) -> dict[str, object]:
        raw = self.json
        if not isinstance(raw, str):
            return {}
        data = json.loads(raw)
        if isinstance(data, dict):
            return  data
        return {}

    @property
    def brand(self) -> str:
        brand = self.card_json.get("brand", "")
        if isinstance(brand, str):
            return brand
        return str(brand)

    @property
    def photos(self) -> list[str]:
        raw = self.card_json.get("photos")
        if not isinstance(raw, list):
            return []
        urls: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                val = item.get("big")
                if isinstance(val, str):
                    urls.append(val)
                else:
                    urls.append(str(val))
        return urls

    @property
    def SubjectId(self) -> int | None:  # noqa
        subject_id = self.card_json.get("subjectID")
        if isinstance(subject_id, int) or subject_id is None:
            return subject_id
        if isinstance(subject_id, str) and subject_id.isdigit():
            return int(subject_id)
        return None


class AdvSetting(BaseTable):
    # TODO: Модель поделена между микросервисами и требует рефакторинга!!!!
    # Не менять поля до рефакторина! По уму: вынести всю работу с базами в один микросервис и прикрутить GRPC-DTO
    class ActiveStatuses(Enum):
        DONE = "done"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # noqa
        self._worst_promo_position = None

    def __repr__(self):
        return (
            f"name: {self.name}, adverdId: {self.adv_id},"
            f" bot_active: {self.bot_active}, active_status: {self.active_status}"
        )

    favorite_users: Mapped[list[User]] = relationship(
        "User", secondary=favorite_advs_association, back_populates="favorites_advs"
    )
    adv_id: Mapped[int] = mapped_column(
        BIGINT(),
        unique=True,
        nullable=True,
    )  # Автоматическая рекламная кампания
    name = mapped_column(String, nullable=False)
    wb_cabinet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wbcabinet.id"), nullable=False
    )
    wb_cabinet: Mapped["WBCabinet"] = relationship(
        "WBCabinet", back_populates="adv_settings", lazy="joined"
    )
    wb_cards: Mapped[list[WBCard]] = relationship(
        "WBCard",
        back_populates="adv_setting",
        cascade="all,delete-orphan",
        uselist=True,
    )  # Изменено на множественное число
    active_status: Mapped[str] = mapped_column(String, default=False)
    adv_keywords: Mapped[list[AdvKeyword]] = relationship(
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
    hard_min_ctr: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=settings.DEFAULT_MIN_CTR,
        server_default=text(str(settings.DEFAULT_MIN_CTR)),
    )
    max_cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_views_for_ml_predict: Mapped[int] = mapped_column(Integer, nullable=True, server_default=text("0"))
    payments: Mapped[list["AdvPayment"]] = relationship(
        "AdvPayment", back_populates="adv_setting", uselist=True
    )
    parsing_active = mapped_column(Boolean, default=False)
    last_update = mapped_column(DateTime, nullable=True)
    bidder_active: Mapped[bool | None] = mapped_column(
        Boolean, default=False, nullable=True
    )
    max_cpm: Mapped[int | None] = mapped_column(Integer, nullable=True) # Максимальная ставка
    max_place: Mapped[int | None ] = mapped_column(Integer,
                                                  nullable=True,
                                                default=1,
                                                  server_default=text("1")
                                                  )
    use_incremental_stats = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Использовать инкрементальный учет продаж вместо дневных агрегатов",
    )  # поле от недоделанного модуля инкрементальной статистики
    min_block_position = mapped_column(Integer, nullable=True, default=0)
    clusters_mode = mapped_column(Boolean, nullable=True, default=True)
    target_ctr_mode = mapped_column(Boolean, nullable=True, default=False)
    hide_small_query_keywords = mapped_column(Integer, nullable=True, default=0)
    bidder_coroutine_type: Mapped[BidderCoroutineType] = mapped_column(
        SAEnum(
            BidderCoroutineType,
            name="bidder_coroutine_type",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        server_default=text("'OLD_UPDATE_CPM_BIDDER'"),
        comment="Тип корутины для обработки биддера",
    )
    target_ctr_mode_strategy = mapped_column(
        String, nullable=True, default="forward"
    )  # forward, keep
    new_auto_min_ctr_mode = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    reset_place = mapped_column(
        Boolean, nullable=True, default=True, server_default=text("true")
    )
    _search_adv_id: Mapped[int] = mapped_column(Integer, nullable=True)
    bidder_step = mapped_column(Integer, nullable=True, default=settings.BIDDER_STEP)
    exponent_predict_ctr: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=settings.DEFAULT_CTR_EXPONENTA,
        server_default=text(str(settings.DEFAULT_CTR_EXPONENTA)),
    )

    auction_boost_all_phrase_mode = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    plan_for_sales_for_day = mapped_column(Integer, nullable=True, default=None)
    target_price_for_order = mapped_column(Float, nullable=True, default=None)

    max_price_for_order = mapped_column(Float, nullable=True, default=None)
    cpm = mapped_column(Integer, nullable=True, default=None)
    bidder_for_auto = mapped_column(
        Boolean, nullable=True, default=True, server_default="true"
    )

    auto_update_white_list: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )

    auto_budget_watchdog_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Включает контроль запуска кампаний и пополнения бюджета",
    )

    auto_update_target_place: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )
    auto_update_exponent: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=True, server_default="true"
    )

    rec_system_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )
    # TODO: Завернуть server_default в text
    hide_zero_views_keywords: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )

    max_balance_adding_for_day: Mapped[int] = mapped_column(
        Integer, nullable=True, default=0, server_default=text("0")
    )

    auto_budget_daily_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Автолимит РАСХОДА бюджета (руб/сутки) для автоматической кампании, 0 = отключено",
    )
    search_auto_budget_daily_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Автолимит РАСХОДА бюджета (руб/сутки) для аукционной кампании, 0 = отключено",
    )

    use_common_budget: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Режим общего бюджета на обе РК (Поиск + Авто) для auto_budget_watchdog",
    )
    common_budget_daily_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text('0'),
        comment="Общий дневной лимит расхода (руб/сутки) на обе РК; при первом включении use_common_budget = сумма лимитов",
    )

    auto_adv_target_status: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None
    )
    auction_adv_target_status: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None
    )


    auto_add_only_relevant_phrase: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default=text("false")
    )

    orders_source_for_auto_mode: Mapped[OrdersSourceForAutoMode] = mapped_column(
        SAEnum(OrdersSourceForAutoMode),
        nullable=True,
        default=OrdersSourceForAutoMode.COMMON_STATISTIC,  # экземпляр Enum
        server_default=OrdersSourceForAutoMode.COMMON_STATISTIC.name,  # строка
    )
    predict_ctr_mode: Mapped[PredictCTRMode] = mapped_column(
        SAEnum(PredictCTRMode),
        nullable=True,
        default=PredictCTRMode.V2,  # экземпляр Enum
        server_default=PredictCTRMode.V2.name,  # строка
    )

    sales_predict_method: Mapped[FactMethods] = mapped_column(
        SAEnum(FactMethods),
        nullable=True,
        default=FactMethods.DIRECT_SALES,  # экземпляр Enum
        server_default=FactMethods.DIRECT_SALES.name,
    )  # строка

    # TODO: Навести порядок в боте, со стороны клиента

    automatic_version: Mapped[int] = mapped_column(
        Integer, nullable=True, default=1, server_default="1"
    )
    bidder_mode: Mapped[BidderMode | None] = mapped_column(
        SAEnum(BidderMode),
        nullable=True,
        default=BidderMode.BY_AUTO_MAX_CPM,
        server_default=BidderMode.BY_AUTO_MAX_CPM.name,
    )

    updater_common_bid_in_search_adv_active_status: Mapped[bool] = \
         mapped_column(Boolean, nullable=True, default=False, server_default=text("false"))

    # TODO: Как будет время - установить дефолт в БД для старых строк
    white_list_mode: Mapped[WhiteListMode] = mapped_column(SAEnum(WhiteListMode),
                                                           nullable=True,
                                                           default=WhiteListMode.ABOVE_MIN_RATING,
                                                           server_default=WhiteListMode.ABOVE_MIN_RATING.name,)

    individual_keywords_target_place_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false")
    )
    min_target_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=300,
        server_default=text('300'),
    )

    target_position_mode: Mapped[TargetPositionMode] = mapped_column(SAEnum(TargetPositionMode),
                                                                     nullable=True,
                                                                     default=TargetPositionMode.MIN_CPA,
                                                                     server_default=TargetPositionMode.MIN_CPA.name)

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

    @auction_adv_id.setter
    def auction_adv_id(self, value: int) -> None:
        self._search_adv_id = value

    @property
    def search_adv_id(self) -> int | None:  # Аукцион
        if self._search_adv_id:
            return self._search_adv_id
        if not self.name:
            return None
        name = self.name.replace(" ", "")
        pattern = re.compile(r"<!-\[(\d+)\]-!>")  # noqa
        match = re.search(pattern, name)
        if not match:
            return None
        return int(match.group(1))

    @search_adv_id.setter
    def search_adv_id(self, value: int) -> None:
        self._search_adv_id = value

    #
    @property
    def max_pay_for_order(self) -> int | None:
        pattern = re.compile(
            r"<MAX_PAY>(\d+)!?</MAX_PAY>"
        )  # Добавили !? для необязательного символа "!"
        match = re.search(pattern, self.name)
        if match:
            return int(match.group(1))
        return None

    @property
    def worst_promo_position(self) -> bool | None:
        try:
            return self._worst_promo_position
        except Exception as e:
            logger.error(e)
            return None

    @worst_promo_position.setter
    def worst_promo_position(self, value):
        self._worst_promo_position = value

    auto_budget_topups: Mapped[list["WBAutoBudgetTopUp"]] = relationship(
        "WBAutoBudgetTopUp",
        back_populates="adv_setting",
        cascade="all, delete-orphan",
    )


class KeywordSetting(BaseTable):
    """hard_status
    0 - black listA
    1 - in test
    2 - white list

    """

    text: Mapped[str] = mapped_column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey("advsetting.id"))
    adv_setting: Mapped[AdvSetting] = relationship(
        "AdvSetting", back_populates="keyword_settings", uselist=False
    )
    predict_ctr = Column(Float, nullable=True)
    adv_keywords = relationship(
        "AdvKeyword",
        back_populates="keyword_setting",
        cascade="all, delete-orphan",
        uselist=True,
    )
    hard_status: Mapped[int] = mapped_column(Integer, default=1)
    added_clicks: Mapped[int | None] = mapped_column(Integer, default=0)
    added_views = Column(Integer, default=0)
    auto_block = Column(Boolean)
    relevant: Mapped[bool] = mapped_column(
        Boolean, nullable=True, default=False, server_default="false"
    )
    target_place: Mapped[int | None] = mapped_column(Integer,
                                                     nullable=True,
                                                     default=None,
                                              )

    @validates("target_place")
    def _validate_target_place(self, _key: str, value: int | None) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int) or value < 1:
            raise ValueError("target_place must be None or an integer > 0")
        return value

    __table_args__ = (
        UniqueConstraint("text", "adv_setting_id"),
        Index("ix_text_adv_setting_id", "text", "adv_setting_id"),
        # Составной индекс для запроса
        Index("ix_keywordsetting_status_adv", "hard_status", "adv_setting_id"),
        Index("ix_keywordsetting_adv_setting_id", "adv_setting_id"),
        Index("ix_keywordsetting_text", "text"),
    )

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "adv_setting_id": self.adv_setting_id,
            "predict_ctr": self.predict_ctr,
            "hard_status": self.hard_status,
            "added_clicks": self.added_clicks,
            "added_views": self.added_views,
            "auto_block": self.auto_block,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> "KeywordSetting":
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            id=data.get("id"),
            text=data.get("text"),
            adv_setting_id=data.get("adv_setting_id"),
            predict_ctr=data.get("predict_ctr"),
            hard_status=data.get("hard_status"),
            added_clicks=data.get("added_clicks"),
            added_views=data.get("added_views"),
            auto_block=data.get("auto_block"),
        )

#
# class WBItemPosition(BaseModel):
#     model_config = ConfigDict(validate_assignment=True)
#
#     nmid: int | None = None
#     position: int | None = None
#     timestamp: datetime.datetime | None = None
#     adv_id: int | None = None
#     keyword_text: str | None = None
#     adv_type: int | None = None
#     total_views: int | None = None
#     total_orders: int | None = None
#
#     @property
#     def type_native(self) -> str:
#         if self.adv_type == 9:
#             return "search"
#         elif self.adv_type == 8:
#             return "auto"
#         else:
#             return "unknown"
#
#     def to_dict(self) -> dict[str, object]:
#         timestamp = self.timestamp
#         return {
#             "real_position": self.position,
#             "promo_position": self.position,
#             "base_position": self.position,
#             "position": self.position,
#             "keyword_text": self.keyword_text,
#             "adv_id": self.adv_id,
#             "nmid": self.nmid,
#             "timestamp": timestamp.isoformat() if timestamp else None,
#             "adv_type": self.adv_type,
#             "total_views": self.total_views,
#             "total_orders": self.total_orders,
#         }
#
#     @staticmethod
#     def from_dict(data: dict[str, object]) -> "WBItemPosition":
#         # создаём пустую модель (разрешено, так как все поля optional)
#         position = WBItemPosition()
#
#         # position
#         raw_position = data.get("position")
#         if isinstance(raw_position, int):
#             position.position = raw_position
#         elif isinstance(raw_position, str) and raw_position.isdigit():
#             position.position = int(raw_position)
#         else:
#             base_raw = data.get("base_position")
#             if isinstance(base_raw, int):
#                 position.position = base_raw
#             elif isinstance(base_raw, str) and base_raw.isdigit():
#                 position.position = int(base_raw)
#             else:
#                 position.position = None
#
#         # adv_id
#         raw_adv_id = data.get("adv_id")
#         if isinstance(raw_adv_id, int):
#             position.adv_id = raw_adv_id
#         elif isinstance(raw_adv_id, str) and raw_adv_id.isdigit():
#             position.adv_id = int(raw_adv_id)
#         else:
#             position.adv_id = None
#
#         # nmid
#         raw_nmid = data.get("nmid")
#         if isinstance(raw_nmid, int):
#             position.nmid = raw_nmid
#         elif isinstance(raw_nmid, str) and raw_nmid.isdigit():
#             position.nmid = int(raw_nmid)
#         else:
#             position.nmid = None
#
#         # timestamp
#         raw_ts = data.get("timestamp")
#         if isinstance(raw_ts, str):
#             try:
#                 position.timestamp = datetime.datetime.fromisoformat(raw_ts)
#             except Exception:
#                 position.timestamp = None
#         else:
#             position.timestamp = None
#
#         # keyword
#         raw_kw = data.get("keyword_text")
#         position.keyword_text = raw_kw if isinstance(raw_kw, str) else None
#
#         # adv_type
#         raw_adv_type = data.get("adv_type")
#         if isinstance(raw_adv_type, int):
#             position.adv_type = raw_adv_type
#         elif isinstance(raw_adv_type, str) and raw_adv_type.isdigit():
#             position.adv_type = int(raw_adv_type)
#         else:
#             position.adv_type = None
#
#         # total_views
#         raw_total_views = data.get("total_views")
#         if isinstance(raw_total_views, int):
#             position.total_views = raw_total_views
#         else:
#             position.total_views = None
#
#         # total_orders
#         raw_total_orders = data.get("total_orders")
#         if isinstance(raw_total_orders, int):
#             position.total_orders = raw_total_orders
#         else:
#             position.total_orders = None
#
#         return position
