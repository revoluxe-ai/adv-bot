"""ORM-модели Wildberries (кабинеты, токены, AdvSetting, KeywordSetting и связанные сущности)."""

from __future__ import annotations
import datetime
import json
import logging
import re
import typing
from enum import Enum
from typing import ClassVar

import jwt
from jwt import DecodeError
from sqlalchemy import (
    BIGINT,
    Boolean,
    CheckConstraint,
    Column,
    Date,
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
from app.modules.common_slaves.wildberries.models.enums import (
    KeywordStrategyMode,
    OrdersSourceForAutoMode,
    TargetPositionMode,
)
from .bidder_mode import BidderMode
from .enums.auto_shelf_bid_control_strategy import AutoShelfBidControlStrategy
from .enums.strategy import Strategy
from .fact_methods_enum import FactMethods
from .wb_auto_budget_topup import WBAutoBudgetTopUp
from app.settings import settings
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.base import Base, BaseTable
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker
from .white_list_mode import WhiteListMode

# Ensure billing models (AdvPayment) are imported and registered before mapper configuration
try:
    # TODO: Надо разобраться что это за конструкцию такая, и постараться ее убрать без рейса исключения
    from app.modules.billing import models as _billing_models

    _: object = _billing_models  # side-effect: register AdvPayment mapper
except Exception:  # noqa
    # In minimal test contexts billing may be absent; relationship will fallback to string resolution
    pass

if typing.TYPE_CHECKING:
    from app.modules.billing.models import AdvPayment
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

logger = logging.getLogger(__name__)


def _sa_enum_values(enum_cls: type[Enum]) -> list[str]:
    """values_callable для SAEnum: строковые `.value` членов Enum."""
    return [str(item.value) for item in enum_cls]


class PredictCTRMode(Enum):
    V1 = "v1"
    V2 = "v2"


class BidderCoroutineType(str, Enum):
    """Тип корутины для обработки биддера."""

    OLD_UPDATE_CPM_BIDDER = "OLD_UPDATE_CPM_BIDDER"
    UPDATE_CLUSTER_BIDS = "UPDATE_CLUSTER_BIDS"


class WBTokenType(str, Enum):
    BASE = "base"
    TEST = "test"
    PERSONAL = "personal"
    SERVICE = "service"
    UNKNOWN = "unknown"


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
            return typing.cast(dict[str, object], result)
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
        s_raw = self.get_payload("s")
        if s_raw is None:
            raise NotValidTokenError
        s = int(s_raw)
        categories: set[str] = set()
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

    def detect_wb_token_type(self) -> WBTokenType:
        payload = self.__payload
        acc = payload.get("acc")
        for_field = payload.get("for")
        t = payload.get("t")

        if acc == 1 and for_field is None and t is False:
            return WBTokenType.BASE
        if acc == 2 and for_field is None and t is True:
            return WBTokenType.TEST
        if acc == 3 and for_field == "self" and t is False:
            return WBTokenType.PERSONAL
        if acc == 4 and isinstance(for_field, str) and for_field.startswith("asid:"):
            return WBTokenType.SERVICE
        return WBTokenType.UNKNOWN

    @property
    def token_type(self) -> WBTokenType:
        return self.detect_wb_token_type()

    @property
    def is_personal(self) -> bool:
        return self.token_type == WBTokenType.PERSONAL


class AdvKeyword(BaseTable):
    adv_setting_id = Column(Integer, ForeignKey("advsetting.id"), nullable=False)
    adv_setting = relationship("AdvSetting", back_populates="adv_keywords")
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0)
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
            return typing.cast(dict[str, object], data)
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
        photos_raw = typing.cast(list[object], raw)
        urls: list[str] = []
        for item in photos_raw:
            if isinstance(item, dict):
                item_dict = typing.cast(dict[str, object], item)
                val = item_dict.get("big")
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

    # DEPRECATED: populate-path отключён (set_worst_promo_position удалён / вызов
    # закомментирован). Non-mapped runtime flag (ClassVar — не колонка SA2; zlpr).
    # Must be bare ClassVar (not typing.ClassVar) under from __future__ import annotations.
    # Instance override via worst_promo_position setter remains supported.
    # Не удалять и не менять семантику без отдельного cleanup-scope.
    _worst_promo_position: ClassVar[bool | None] = None

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
    black_phrases: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False, server_default=text("'[]'")
    )
    relevant_phrases: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        server_default=text("'[]'"),
        comment="Шаблоны релевантных фраз (quoted + RE2), как black_phrases",
    )
    keyword_settings: Mapped[list["KeywordSetting"]] = relationship(
        "KeywordSetting",
        cascade="all, delete-orphan",
        back_populates="adv_setting",
        uselist=True,
    )
    pass_days = Column(Integer, default=30)
    boost: Mapped[float] = mapped_column(Float, server_default=text("1"))
    type: Mapped[int] = mapped_column(Integer, nullable=True)
    wb_bid_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment=(
            "Тип ставки WB из v2/adverts: unified или manual. "
            "Sync: apply_wb_campaign_meta_from_legacy_adv_data. "
            "normquery minus: только manual+search (см. wb_campaign_meta)."
        ),
    )
    wb_placement_search: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment=(
            "Размещение «Поиск» (settings.placements.search). "
            "True — единственный тип, для которого WB normquery get/set-minus."
        ),
    )
    wb_placement_recommendations: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment=(
            "Размещение «Рекомендации» (полка). "
            "manual+search=false+recom=true → полочная auto, skip normquery в MinusPhraseManager."
        ),
    )

    hard_min_ctr: Mapped[float | None] = mapped_column( # Устарело, не используется
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
    use_cluster_stats_in_freshness = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Учитывать кластерную статистику при проверке свежести",
    )
    min_block_position = mapped_column(Integer, nullable=True, default=0)
    clusters_mode = mapped_column(Boolean, nullable=True, default=True)
    target_ctr_mode = mapped_column(Boolean, nullable=True, default=False)
    hide_small_query_keywords = mapped_column(Integer, nullable=True, default=0)
    bidder_coroutine_type: Mapped[BidderCoroutineType] = mapped_column(
        SAEnum(
            BidderCoroutineType,
            name="bidder_coroutine_type",
            values_callable=_sa_enum_values,
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

    max_price_for_order: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    substitute_fact_cpo_for_max: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment=(
            "V3 Raise MAX: in-memory max=fact CPO when fact>db max (per tick, no persist)"
        ),
    )
    cpm = mapped_column(Integer, nullable=True, default=None)
    bidder_for_auto = mapped_column(
        Boolean, nullable=True, default=True, server_default="true",
        comment="Включает управление ставкой для Авто (legacy bidder)",
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
    auto_shelf_bid_control_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    comment="Включает управление общей ставкой полок НОВЫЙ МОДУЛЬ (auto_shelf_bid_control)",
    )

    # Intentional default:
    # auto_shelf_bid_control_strategy defaults to plan_distance intentionally.
    # At the moment auto_shelf_bid_control is enabled only for controlled shelf-test campaigns.
    # Legacy bidder paths do not read this field.
    auto_shelf_bid_control_strategy: Mapped[AutoShelfBidControlStrategy | None] = mapped_column(
        SAEnum(
            AutoShelfBidControlStrategy,
            name="auto_shelf_bid_control_strategy",
            values_callable=_sa_enum_values,
            validate_strings=True,
        ),
        nullable=True,
        default=AutoShelfBidControlStrategy.PLAN_DISTANCE,
        server_default="plan_distance",
        comment=(
            "Стратегия выбора main bid для auto_shelf_bid_control: "
            "cycle_metric | plan_distance | ctr | cpc. "
            "auto_shelf_bid_control_strategy defaults to plan_distance intentionally. "
            "At the moment auto_shelf_bid_control is enabled only for controlled shelf-test campaigns. "
            "Legacy bidder paths do not read this field."
        ),
    )

    # TODO: Р—Р°РІРµСЂРЅСѓС‚СЊ server_default РІ text
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
    aggressiveness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default=text("3"),
        comment="AutoUpdater v3: 1=min_cpm_first / 2=optimal_first / 3=max_conv_first (only outside shelf phase)",
    )
    keyword_calibration_max_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="V3 RESOLVE_CALIBRATION_TRIM: cap effective ladder DOWN steps per keyword per tick",
    )
    card_ab_hold_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="off",
        server_default=text("'off'"),
        comment="A/B Hold mode: off | pending_setup | active (spec card-ab-hold-mode)",
    )
    card_ab_hold_allowed_phrases_snapshot: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        server_default=text("'[]'"),
        comment=(
            "A/B Hold PG snapshot разрешённого (allowed/relevant) набора фраз "
            "[text, ...]; минус — производный enforcement (spec card-ab-hold-mode §8)"
        ),
    )
    card_ab_hold_degraded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment=(
            "A/B Hold honest degradation (spec card-ab-hold-mode §8): True когда "
            "enforcement замороженного allowed-set не может гарантировать чистый hold "
            "(превышен WB minus cap / open-match). Durable SoT для честного UI-статуса; "
            "self-healing — снимается на тике, где cap не превышен."
        ),
    )
    card_ab_hold_phase: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default=None,
        comment=(
            "A/B Hold epoch phase (§18.5/§19.5): NULL=legacy MVP-1; non-NULL=epoch-managed "
            "(awaiting_keyword_confirm|warm_up|…|ready_active)"
        ),
    )
    card_ab_hold_warmup_started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="A/B Hold WARM_UP timer start (timestamptz); NULL when not in WARM_UP",
    )
    card_ab_hold_warmup_duration_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=24,
        server_default=text("24"),
        comment="A/B Hold WARM_UP duration hours (default/min 24; MUST NOT go below 24)",
    )
    card_ab_hold_generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="A/B Hold epoch generation (monotonic; 0=no epoch intent yet)",
    )
    card_ab_hold_wb_sync_idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        default=None,
        unique=True,
        comment="A/B Hold WB sync idempotency key '{adv_id}:{generation}' (NULL until intent)",
    )
    card_ab_hold_pending_intent_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="A/B Hold durable PENDING intent snapshot (confirmed params + generation)",
    )
    card_ab_hold_sync_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="none",
        server_default=text("'none'"),
        comment="A/B Hold WB sync status: none|pending|partial|complete",
    )
    card_ab_hold_confirmed_keywords_json: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="A/B Hold confirmed keyword set (epoch SoT)",
    )
    card_ab_hold_confirmed_target_places_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="A/B Hold confirmed target places map keyword→TP (epoch SoT)",
    )
    card_ab_hold_confirmed_auto_participation: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
        comment="A/B Hold confirmed Auto participation (epoch SoT)",
    )
    card_ab_hold_confirmed_auto_bid: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
        comment="A/B Hold confirmed Auto bid (epoch SoT)",
    )
    card_ab_hold_emergency_latch: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment=(
            "A/B Hold Emergency kill-switch latch (ab-hold-emergency-kill-switch): "
            "True → no budget top-up / no activity restart; pause+block applied"
        ),
    )
    card_ab_hold_emergency_educated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment=(
            "A/B Hold Emergency launch education ACK "
            "(ab-hold-emergency-kill-switch Confirm/ACK)"
        ),
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

    individual_keywords_target_place_mode: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false")
    )
    min_target_position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=False,
        default=300,
        server_default=text('300'),
    )

    target_position_mode: Mapped[TargetPositionMode  | None] = mapped_column(SAEnum(TargetPositionMode),
                                                                     nullable=True,
                                                                     default=TargetPositionMode.MIN_CPA,
                                                                     server_default=TargetPositionMode.MIN_CPA.name)

    strategy: Mapped[Strategy | None] = mapped_column(SAEnum(Strategy),
                                               nullable=True,
                                               default=Strategy.MIN_CPO,
                                               server_default=Strategy.MIN_CPO.name)
    auto_update_strategy: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=True, server_default=text("true")
    )

    auto_common_budget: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false")
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

    @property
    def worst_promo_position(self) -> bool | None:
        """DEPRECATED: флаг worst promo position; наполнения больше нет.

        Populate-path (`data_manager.set_worst_promo_position`) удалён; вызов в
        client_bot закомментирован. Getter/setter оставлены без смены поведения
        для residual UI-read. Не использовать в новом коде.
        """
        try:
            return self._worst_promo_position
        except Exception as e:
            logger.error(e)
            return None

    @worst_promo_position.setter
    def worst_promo_position(self, value: bool | None) -> None:
        """DEPRECATED: см. getter; семантика setter не меняется.

        Instance shadow через ``object.__setattr__``: атрибут — ``ClassVar``
        (SA2 non-mapped / zlpr), прямой ``self._… =`` запрещён Pyright.
        """
        object.__setattr__(self, "_worst_promo_position", value)

    auto_budget_topups: Mapped[list["WBAutoBudgetTopUp"]] = relationship(
        "WBAutoBudgetTopUp",
        back_populates="adv_setting",
        cascade="all, delete-orphan",
    )


class KeywordSetting(BaseTable):
    """hard_status
    0 - black list
    1 - in test
    2 - white list
    3 - turn off
    4 - фикс.фразы (всегда вкл, не отключаются, не зависят от белого списка)
    """

    text: Mapped[str] = mapped_column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey("advsetting.id"))
    adv_setting: Mapped[AdvSetting] = relationship(
        "AdvSetting", back_populates="keyword_settings", uselist=False
    )
    predict_ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    adv_keywords = relationship(
        "AdvKeyword",
        back_populates="keyword_setting",
        cascade="all, delete-orphan",
        uselist=True,
    )
    hard_status: Mapped[int] = mapped_column(Integer, default=1)
    strategy_mode: Mapped[KeywordStrategyMode] = mapped_column(
        SAEnum(KeywordStrategyMode),
        nullable=False,
        default=KeywordStrategyMode.MIN_CPA,
        server_default=KeywordStrategyMode.MIN_CPA.name,
        # V3: для hard_status 1/0/3 нужен OFF — выставляется в write-path и backfill при включении V3.
    )
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
        if value < 0:
            raise ValueError(
                "target_place must be None or a non-negative integer "
                "(0 = минимальная ставка WB)"
            )
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



class AdvTimeSettings(Base):  # type: ignore[valid-type]
    # TODO: Тут косяк: надо использовать BaseTable
    __tablename__ = "adv_time_settings"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    adv_setting_id: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey("advsetting.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    date_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    date_start: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    date_end: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="Europe/Moscow",
        server_default=text("'Europe/Moscow'"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        CheckConstraint(
            "date_start IS NULL OR date_end IS NULL OR date_start <= date_end",
            name="ck_adv_time_settings_date_range",
        ),
    )


class AdvTimeWeekMask(Base):  # type: ignore[valid-type]
    __tablename__ = "adv_time_week_mask"

    adv_setting_id: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey("advsetting.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    dow: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    hours_mask: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    __table_args__ = (
        CheckConstraint("dow BETWEEN 0 AND 6", name="ck_adv_time_week_mask_dow"),
    )
