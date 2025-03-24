import json
from sqlalchemy import (
    MetaData, Column, Integer, String, TypeDecorator, 
    Boolean, Float, DateTime, ForeignKey, BIGINT, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, timedelta

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

class MockUser(MockBase):
    __tablename__ = 'user'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(BIGINT, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    adv_updater_user_chat_id = Column(BIGINT, nullable=True)
    wb_user_cabinets: Mapped[list["MockWBUserCabinet"]] = relationship("MockWBUserCabinet", back_populates="user")
    wb_tokens: Mapped[list["MockWBToken"]] = relationship("MockWBToken", back_populates="user")

class MockWBCabinet(MockBase):
    __tablename__ = 'wbcabinet'
    id = Column(Integer, primary_key=True, autoincrement=True)
    balance = Column(Float, nullable=True)
    bonus = Column(Float, nullable=True)
    expiration_time = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    shop_id = Column(String, nullable=True)
    white_list_update_active = Column(Boolean, default=False)
    wb_user_cabinets = relationship("MockWBUserCabinet", back_populates="wb_cabinet")

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
    nmid = Column(Integer, nullable=False)
    vector = Column(JSONType, nullable=False)

class MockKeywordFeature(MockBase):
    __tablename__ = 'keywordfeature'
    
    id = Column(Integer, primary_key=True)
    nmid = Column(Integer, nullable=False)
    vector = Column(JSONType, nullable=False)

class MockWBToken(MockBase):
    __tablename__ = 'wbtoken'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'))
    user: Mapped["MockUser"] = relationship("MockUser", back_populates="wb_tokens")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    _shop_id: Mapped[str] = mapped_column('shop_id', String, nullable=True)

    @property
    def shop_id(self) -> str:
        return self._shop_id

    @shop_id.setter 
    def shop_id(self, value: str):
        self._shop_id = value

    def check_valid(self) -> bool:
        return True

    def get_payload(self, key: str, default: int = 0) -> int:
        return default

    @property
    def expires(self) -> datetime:
        return datetime.now() + timedelta(days=30)

class MockAdvSetting(MockBase):
    __tablename__ = 'advsetting'
    
    id = Column(Integer, primary_key=True)
    adv_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))
    wb_cabinet = relationship("MockWBCabinet")
    active_status = Column(Boolean, default=True)
    bot_active = Column(Boolean, default=True)
    nmids = Column(JSONType, nullable=True)
    pass_days = Column(Integer, default=0)
    boost = Column(Float, default=2.0)
    type = Column(String, default="search")
    hard_min_ctr = Column(Float, default=0.02)
    max_cpc = Column(Float, default=500.0)
    min_views_for_ml_predict = Column(Integer, default=100)
    parsing_active = Column(Boolean, default=False)
    last_update = Column(DateTime, nullable=True)
    bidder_active = Column(Boolean, default=False)
    max_cpm = Column(Float, default=150.0)
    max_place = Column(Integer, default=30)
    min_block_position = Column(Integer, default=1)
    clusters_mode = Column(Boolean, default=False)
    target_ctr_mode = Column(Boolean, default=False)
    hide_small_query_keywords = Column(Boolean, default=False)
    target_ctr_mode_strategy = Column(String, default="forward")
    new_auto_min_ctr_mode = Column(Boolean, default=False)
    reset_place = Column(Boolean, default=False)
    _search_adv_id = Column(String, nullable=True)
    bidder_step = Column(Float, default=0.5)
    exponent_predict_ctr = Column(Float, default=1.0)
    auction_boost_all_phrase_mode = Column(Boolean, default=False)
    plan_for_sales_for_day = Column(Float, default=0.0)
    target_price_for_order = Column(Float, default=0.0)
    max_price_for_order = Column(Float, default=0.0)
    cpm = Column(Float, default=100.0)
    bidder_for_auto = Column(Boolean, default=False) 