import json
from sqlalchemy import (
    MetaData, Column, Integer, String, TypeDecorator,
    Boolean, Float, DateTime, ForeignKey, BIGINT, UniqueConstraint, Date, Index, text, Table, JSON
)

from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, timedelta
import pytest
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.declarative import declarative_base
from unittest.mock import MagicMock


# Создаем отдельный экземпляр MetaData для моков
mock_metadata = MetaData()
MockBase = declarative_base(metadata=mock_metadata)

class JSONType(TypeDecorator):
    """Тип для хранения JSON в SQLite"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

class ArrayType(TypeDecorator):
    """Тип для хранения массивов в SQLite"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# Создаем мок для таблицы связи между User и AdvSetting
favorite_advs_association = Table(
    'favorite_advs_association', 
    MockBase.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('adv_setting_id', Integer, ForeignKey('advsetting.id'), primary_key=True),
)


class MockUser(MockBase):
    __tablename__ = 'user'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BIGINT, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    adv_updater_user_chat_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    wb_user_cabinets: Mapped[list["MockWBUserCabinet"]] = relationship("MockWBUserCabinet",
                                                                       back_populates="user",
                                                                       cascade="all,"
                                                                      " delete-orphan")
    wb_tokens: Mapped[list["MockWBToken"]] = relationship("MockWBToken",
                                                          back_populates="user",
                                                          cascade="all, delete-orphan")
    payments = relationship("MockAdvPayment", back_populates="user")
    favorites_advs = relationship("MockAdvSetting", secondary=favorite_advs_association)
    
    __table_args__ = (
        Index('user_telegram_id_index', user_telegram_id),
    )

class MockWBCabinet(MockBase):
    __tablename__ = 'wbcabinet'
    expiration_time = Column(DateTime, nullable=False, default=datetime.now() + timedelta(days=7))
    id = Column(Integer, primary_key=True)
    balance = Column(Float, default=0, server_default=text('0'), nullable=False)
    bonus = Column(Float, default=0, server_default=text('0'), nullable=False)
    expiration_alarm_days_pass = Column(Integer, default=None)
    active = Column(Boolean, default=True)
    shop_id = Column(String, nullable=False, unique=True)
    demo = Column(Boolean, default=True)
    white_list_update_active = Column(Boolean, default=False)
    wb_user_cabinets = relationship("MockWBUserCabinet", back_populates="wb_cabinet")
    wb_categories = relationship("MockWBCategory", back_populates="wb_cabinet")
    wb_cards = relationship("MockWBCard", back_populates="wb_cabinet")
    adv_settings = relationship("MockAdvSetting", back_populates="wb_cabinet")
    payments = relationship("MockAdvPayment", back_populates="wb_cabinet")
    balance_payments = relationship('MockWBBalancePayment', back_populates='wb_cabinet', uselist=True)
    bonus_payments = relationship('MockWBBonusPayment', back_populates='wb_cabinet', uselist=True)
    
    __table_args__ = (
        Index('idx_balance_bonus', 'balance', 'bonus'),
        Index('idx_balance', 'balance'),
        Index('idx_bonus', 'bonus'),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def calculated_balance(self) -> float:
        """Вычисляет баланс на основе начального значения balance и всех платежей"""
        if not hasattr(self, 'balance_payments') or not self.balance_payments:
            return self.balance  # Возвращаем текущее значение, если нет платежей
        
        # Суммируем все платежи и начальное значение баланса
        return self.balance + sum(payment.amount for payment in self.balance_payments)
    
    @property
    def calculated_bonus(self):
        """Вычисляет бонусы на основе начального значения bonus и всех платежей"""
        if not hasattr(self, 'bonus_payments') or not self.bonus_payments:
            return self.bonus  # Возвращаем текущее значение, если нет платежей
        
        # Суммируем все платежи и начальное значение бонусов
        return self.bonus + sum(payment.amount for payment in self.bonus_payments)


class MockWBCategory(MockBase):
    __tablename__ = 'wbcategory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet = relationship("MockWBCabinet", back_populates="wb_categories")
    wb_category_name = Column(String, nullable=False)
    wb_cards = relationship("MockWBCard", back_populates="wb_category")


class MockWBUserCabinet(MockBase):
    __tablename__ = 'wbusercabinet'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet = relationship("MockWBCabinet", back_populates="wb_user_cabinets")
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship("MockUser", back_populates="wb_user_cabinets")
    name = Column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint('wb_cabinet_id', 'user_id', name='_wb_cabinet_id_user_id_uc'),)

class MockItemFeature(MockBase):
    __tablename__ = 'itemfeature'
    id = Column(Integer, primary_key=True)
    nmid = Column(Integer, nullable=False, unique=True)
    vector = Column(JSONType, nullable=False)


class MockKeywordFeature(MockBase):
    __tablename__ = 'keywordfeature'
    id = Column(Integer, primary_key=True)
    keyword = Column(String, nullable=False, unique=True)
    vector = Column(JSONType, nullable=False)

class MockWBToken(MockBase):
    __tablename__ = 'wbtoken'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped["MockUser"] = relationship("MockUser", back_populates="wb_tokens")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    shop_id = mapped_column(String, nullable=True)
    
    __table_args__ = (UniqueConstraint('api_key', 'user_id', name='_api_key_user_id_uc'),)

    def __payload(self):
        try:
            return {'exp': (datetime.now() + timedelta(days=30)).timestamp(), 'sid': self.shop_id}
        except:
            raise Exception("NotValidTokenError")

    def check_valid(self) -> bool:
        try:
            if self.__payload():
                return True
        except Exception:
            return False
        return True

    def get_payload(self, key: str, default: int = 0) -> int:
        payload = self.__payload()
        return payload.get(key, default)

    @property
    def __expires(self):
        return datetime.utcfromtimestamp(self.__payload().get('exp'))

    @property
    def expires(self) -> datetime:
        return self.__expires

    @property
    def read_only(self) -> bool:
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
        s = self.get_payload('s',)
        categories = set()
        for bit_position, category_name in categories_map.items():
            if s & (1 << bit_position):
                categories.add(category_name)
        return categories

class MockAdvSetting(MockBase):
    __tablename__ = 'advsetting'
    
    id = Column(Integer, primary_key=True)
    adv_id = Column(BIGINT, unique=True)
    name = Column(String, nullable=False)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet = relationship("MockWBCabinet", back_populates="adv_settings")
    active_status = Column(String, default=False)
    bot_active = Column(Boolean, default=False)
    nmids = Column(JSON, default=lambda: [])
    pass_days = Column(Integer, default=30)
    boost = Column(Float, default=1)
    type = Column(Integer, nullable=True)
    hard_min_ctr = Column(Float, nullable=True)
    max_cpc = Column(Float, nullable=True)
    min_views_for_ml_predict = Column(Integer, nullable=True, default=0)
    parsing_active = Column(Boolean, default=False)
    last_update = Column(DateTime, nullable=True)
    bidder_active = Column(Boolean, default=False)
    max_cpm = Column(Integer, nullable=True)
    max_place = Column(Integer, nullable=True)
    min_block_position = Column(Integer, nullable=True, default=0)
    clusters_mode = Column(Boolean, nullable=True, default=True)
    target_ctr_mode = Column(Boolean, nullable=True, default=False)
    hide_small_query_keywords = Column(Integer, nullable=True, default=0)
    target_ctr_mode_strategy = Column(String, nullable=True, default='forward')
    new_auto_min_ctr_mode = Column(Boolean, nullable=False, default=True)
    reset_place = Column(Boolean, nullable=True, default=True)
    _search_adv_id = Column(Integer, nullable=True)
    bidder_step = Column(Integer, nullable=True, default=0.5)
    exponent_predict_ctr = Column(Float, nullable=False, default=3)
    auction_boost_all_phrase_mode = Column(Boolean, nullable=False, default=False)
    plan_for_sales_for_day = Column(Integer, nullable=True, default=None)
    target_price_for_order = Column(Float, nullable=True, default=None)
    max_price_for_order = Column(Float, nullable=True, default=None)
    cpm = Column(Integer, nullable=True, default=None)
    bidder_for_auto = Column(Boolean, nullable=True, default=True)
    payments = relationship("MockAdvPayment", back_populates="adv_setting")
    favorite_users = relationship("MockUser", secondary=favorite_advs_association, back_populates="favorites_advs")
    wb_cards = relationship("MockWBCard", back_populates="adv_setting")
    
    __table_args__ = (
        Index('ix_adv_settings_cabinet_type_update', 'wb_cabinet_id', 'type', 'last_update'),
        Index('ix_adv_settings_cabinet_id', 'wb_cabinet_id'),
        Index('ix_adv_settings_type', 'type'),
        Index('ix_advsetting_adv_id', 'adv_id'),
        Index('ix_advsetting_active_status', 'active_status'),
        Index('ix_advsetting_cabinet_bot_active', 'wb_cabinet_id', 'bot_active'),
        Index('ix_advsetting_bot_active', 'bot_active'),
        Index('ix_name__nmids__search_adv_id', 'name', 'nmids', '_search_adv_id'),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class MockAdvPayment(MockBase):
    __tablename__ = 'advpayment'
    
    id = Column(Integer, primary_key=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=True)
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=True)
    type = Column(String, nullable=True)
    
    wb_cabinet = relationship('MockWBCabinet', back_populates='payments')
    adv_setting = relationship('MockAdvSetting', back_populates='payments')
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    user = relationship('MockUser', back_populates='payments')
    
    __table_args__ = (
        UniqueConstraint('date', 'adv_setting_id', 'type', name='uix_date_adv_setting_id_type'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MockWBBalancePayment(MockBase):
    __tablename__ = "wbbalancepayment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_date_time = Column(DateTime, nullable=False, default=datetime.now)
    wb_cabinet = relationship("MockWBCabinet", back_populates="balance_payments")
    
    __table_args__ = (
        Index('idx_wb_balance_payment_cabinet_id', 'wb_cabinet_id'),
        Index('idx_wb_balance_payment_date', 'transaction_date_time'),
    )


class MockWBBonusPayment(MockBase):
    __tablename__ = "wbbonuspayment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    transaction_date_time = Column(DateTime, nullable=False, default=datetime.now)
    operation_type = Column(String, nullable=False, default="add")  # 'add', 'subtract', 'reset'
    admin_user_id = Column(Integer, nullable=True)  # ID администратора, выполнившего операцию
    wb_cabinet = relationship("MockWBCabinet", back_populates="bonus_payments")
    
    __table_args__ = (
        Index('idx_wb_bonus_payment_cabinet_id', 'wb_cabinet_id'),
        Index('idx_wb_bonus_payment_date', 'transaction_date_time'),
        Index('idx_wb_bonus_payment_admin', 'admin_user_id'),
        Index('idx_wb_bonus_payment_operation', 'operation_type'),
    )

@pytest.fixture
def mock_adv_setting(mock_wb_cabinet):
    return MockAdvSetting(
        id=1,
        adv_id="test_adv_id",
        name="Test Adv",
        wb_cabinet_id=mock_wb_cabinet.id,
        active_status=True,
        bot_active=True,
        nmids=[12345, 67890],
        type=8
    )

class MockWBCard(MockBase):
    __tablename__ = 'wbcard'
    
    id = Column(Integer, primary_key=True)
    nmid = Column(Integer, unique=True, nullable=False)
    offer_id = Column(String)
    name = Column(String)
    wb_category_id = Column(Integer, ForeignKey('wbcategory.id'))
    wb_category = relationship("MockWBCategory", back_populates="wb_cards")
    json = Column(JSONType)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))
    wb_cabinet = relationship("MockWBCabinet", back_populates="wb_cards")
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'))
    adv_setting = relationship("MockAdvSetting", back_populates="wb_cards")
    updated = Column(Boolean, default=False)
    add_to_db = Column(Boolean, default=False)

class MockKeyword(MockBase):
    __tablename__ = 'keyword'
    
    id = Column(Integer, primary_key=True)
    word2vec = Column(ArrayType, nullable=True)

class MockImage(MockBase):
    __tablename__ = 'image'
    
    id = Column(Integer, primary_key=True)
    vector = Column(ArrayType)
    nouns = Column(ArrayType, nullable=True)
    old_keywords = Column(ArrayType)

# Добавим мок для модуля pandas, чтобы обойти ошибку AttributeError: __version__
if not hasattr(pd, '__version__'):
    pd.__version__ = '1.5.3'  # Устанавливаем фиктивную версию pandas

# Создадим мок для XGBoost
class MockXGBModel:
    def predict(self, X):
        return [0.1] * len(X)  # Возвращаем фиктивные предсказания

class MockXGBoost:
    XGBModel = MockXGBModel
    XGBRegressor = MockXGBModel

    @staticmethod
    def load_model(*args, **kwargs):
        return MockXGBModel()

import sys
# Если нужно замокать целые модули, которые вызывают ошибки
sys.modules['xgboost'] = MockXGBoost()

# Базовый класс для моделей SQLAlchemy
Base = declarative_base()

# Дополнительный класс для MockBase с улучшенными моками
class MockBase:
    metadata = MagicMock()
    metadata.drop_all = MagicMock()
    metadata.create_all = MagicMock()
    query = MagicMock()

    @classmethod
    def get_or_404(cls, id):
        return cls(id=id)

    def to_dict(self):
        return {
            'id': getattr(self, 'id', None),
            'name': getattr(self, 'name', None)
        }

# Класс для моков SQLAlchemy
class Column:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        
class ForeignKey:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

class relationship:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

class ArrayType:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

# Мок для WBCabinet
class MockWBCabinet:
    def __init__(self, id=1, shop_id="test_shop", expiration_time=None, active=True, 
                 demo=False, balance=0.0, bonus=0.0, white_list_update_active=False):
        self.id = id
        self.shop_id = shop_id
        self.expiration_time = expiration_time or (datetime.now() + timedelta(days=30))
        self.active = active
        self.demo = demo
        self.balance = balance
        self.calculated_balance = balance
        self.bonus = bonus
        self.calculated_bonus = bonus
        self.white_list_update_active = white_list_update_active
        self.adv_settings = []
        self.bonus_payments = []
        self.balance_payments = []
        self.wbusercabinets = []

    def to_dict(self):
        return {
            'id': self.id,
            'shop_id': self.shop_id,
            'expiration_time': self.expiration_time,
            'active': self.active,
            'demo': self.demo,
            'balance': self.balance,
            'bonus': self.bonus,
            'white_list_update_active': self.white_list_update_active
        }

# Мок для User
class MockUser:
    def __init__(self, id=1, user_telegram_id=123456789, username="test_user", 
                 email=None, adv_updater_user_chat_id=None):
        self.id = id
        self.user_telegram_id = user_telegram_id
        self.username = username
        self.email = email
        self.adv_updater_user_chat_id = adv_updater_user_chat_id
        self.wbusercabinets = []
        self.favorite_advs = []

    def to_dict(self):
        return {
            'id': self.id,
            'user_telegram_id': self.user_telegram_id,
            'username': self.username,
            'email': self.email
        }

# Мок для WBUserCabinet
class MockWBUserCabinet:
    def __init__(self, id=1, user=None, wb_cabinet=None, active=True, name='Test Cabinet'):
        self.id = id
        self.user = user
        self.user_id = user.id if user else None
        self.wb_cabinet = wb_cabinet
        self.wb_cabinet_id = wb_cabinet.id if wb_cabinet else None
        self.active = active
        self.name = name
        
        if user and user.wbusercabinets is not None and self not in user.wbusercabinets:
            user.wbusercabinets.append(self)
        if wb_cabinet and wb_cabinet.wbusercabinets is not None and self not in wb_cabinet.wbusercabinets:
            wb_cabinet.wbusercabinets.append(self)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'wb_cabinet_id': self.wb_cabinet_id,
            'active': self.active,
            'name': self.name
        }

# Мок для WBToken
class MockWBToken:
    def __init__(self, id=1, api_key="test_api_key", user=None, active=True, shop_id="test_shop"):
        self.id = id
        self.api_key = api_key
        self.user = user
        self.user_id = user.id if user else None
        self.active = active
        self.shop_id = shop_id

    def to_dict(self):
        return {
            'id': self.id,
            'api_key': self.api_key,
            'user_id': self.user_id,
            'active': self.active,
            'shop_id': self.shop_id
        }

# Мок для AdvSetting
class MockAdvSetting:
    def __init__(self, id=1, adv_id="test_adv_id", name="Test Adv", wb_cabinet=None, wb_cabinet_id=None,
                 active_status=True, bot_active=True, nmids=None, type="search", 
                 keyword_settings=None, adv_keywords=None, payments=None):
        self.id = id
        self.adv_id = adv_id
        self.name = name
        self.wb_cabinet = wb_cabinet
        self.wb_cabinet_id = wb_cabinet_id or (wb_cabinet.id if wb_cabinet else None)
        self.active_status = active_status
        self.bot_active = bot_active
        self.nmids = nmids or [12345, 67890]
        self.type = type
        self.keyword_settings = keyword_settings or []
        self.adv_keywords = adv_keywords or []
        self.payments = payments or []
        self.bid_data = {}
        self.bidder_active = True
        self.exponent_predict_ctr = 1.0
        self.auction_boost_all_phrase_mode = False
        self.new_auto_min_ctr_mode = True
        
        if wb_cabinet and self not in wb_cabinet.adv_settings:
            wb_cabinet.adv_settings.append(self)

    def to_dict(self):
        return {
            'id': self.id,
            'adv_id': self.adv_id,
            'name': self.name,
            'wb_cabinet_id': self.wb_cabinet_id,
            'active_status': self.active_status,
            'bot_active': self.bot_active,
            'nmids': self.nmids,
            'type': self.type,
            'bidder_active': self.bidder_active
        }

# Мок для ItemFeature
class MockItemFeature:
    def __init__(self, id=1, nmid=12345, vector=None):
        self.id = id
        self.nmid = nmid
        self.vector = vector or "[0.1, 0.2, 0.3]"

    def to_dict(self):
        return {
            'id': self.id,
            'nmid': self.nmid,
            'vector': self.vector
        }

# Мок для KeywordFeature
class MockKeywordFeature:
    def __init__(self, id=1, keyword="test_keyword", vector=None):
        self.id = id
        self.keyword = keyword
        self.vector = vector or "[0.1, 0.2, 0.3]"

    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'vector': self.vector
        }

# Мок для AdvPayment
class MockAdvPayment:
    def __init__(self, id=1, adv_setting=None, adv_setting_id=None, date=None, 
                 amount=100.0, type="balance", wb_cabinet=None, wb_cabinet_id=None, user=None, user_id=None):
        self.id = id
        self.adv_setting = adv_setting
        self.adv_setting_id = adv_setting_id or (adv_setting.id if adv_setting else None)
        self.date = date or datetime.now().date()
        self.amount = amount
        self.type = type
        self.wb_cabinet = wb_cabinet
        self.wb_cabinet_id = wb_cabinet_id or (wb_cabinet.id if wb_cabinet else None)
        self.user = user
        self.user_id = user_id or (user.id if user else None)
        
        if adv_setting and adv_setting.payments is not None and self not in adv_setting.payments:
            adv_setting.payments.append(self)

    def to_dict(self):
        return {
            'id': self.id,
            'adv_setting_id': self.adv_setting_id,
            'date': self.date,
            'amount': self.amount,
            'type': self.type,
            'wb_cabinet_id': self.wb_cabinet_id,
            'user_id': self.user_id
        }

# Мок для KeywordSetting
class MockKeywordSetting:
    def __init__(self, id=1, adv_setting=None, adv_setting_id=None, text="test_keyword", 
                 bid=None, search_count=100, auto_bid=True):
        self.id = id
        self.adv_setting = adv_setting
        self.adv_setting_id = adv_setting_id or (adv_setting.id if adv_setting else None)
        self.text = text
        self.bid = bid or 100.0
        self.search_count = search_count
        self.auto_bid = auto_bid
        
        if adv_setting and adv_setting.keyword_settings is not None and self not in adv_setting.keyword_settings:
            adv_setting.keyword_settings.append(self)

    def to_dict(self):
        return {
            'id': self.id,
            'adv_setting_id': self.adv_setting_id,
            'text': self.text,
            'bid': self.bid,
            'search_count': self.search_count,
            'auto_bid': self.auto_bid
        }

# Моки для файловых операций и другие вспомогательные классы
class MockMessage:
    def __init__(self, text=None, from_user=None, chat=None):
        self.text = text
        self.from_user = from_user or MockUser()
        self.chat = chat or {'id': 123456789}

class MockCallback:
    def __init__(self, data=None, from_user=None, message=None):
        self.data = data
        self.from_user = from_user or MockUser()
        self.message = message or MockMessage()

# Мокируем все функции SQLAlchemy
SQLAlchemyMockClasses = [
    'and_', 'or_', 'not_', 'select', 'update', 'delete', 'join', 'outerjoin', 
    'func', 'desc', 'asc', 'cast', 'text', 'alias', 'literal', 'distinct'
]

for cls_name in SQLAlchemyMockClasses:
    globals()[cls_name] = MagicMock(return_value=MagicMock())
