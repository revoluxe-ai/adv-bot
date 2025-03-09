import json
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Index, UniqueConstraint, ARRAY
from sqlalchemy import (Column, Integer, String, ForeignKey,
                        BIGINT, Boolean, Float, DateTime, text)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
import jwt
from sqlalchemy.dialects.postgresql import JSONB
import datetime

from app.client_bot.const import DEFAULT_BIDDER_STEP
from app.utils.db.base import BaseTable
from . import exceptions
from ...wb_adv_updater.models import AdvPayment

from app.utils.db.models import User, favorite_advs_association

from app.utils.db.session_maker import get_async_session_maker


_sm = get_async_session_maker

class WBUserCabinet(BaseTable):
    wb_cabinet_id: Mapped[Integer] = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet = relationship("WBCabinet", back_populates="wb_user_cabinets")
    user_id: Mapped[Integer] = Column(Integer, ForeignKey('user.id'), nullable=False)
    user: Mapped[User]  = relationship("User", back_populates="wb_user_cabinets",
                                       )
    name = Column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint('wb_cabinet_id', 'user_id',  name='_wb_cabinet_id_user_id_uc'),)





class WBCabinet(BaseTable):
    shop_id = Column(String, nullable=False, unique=True)
    wb_cards = relationship('WBCard', back_populates='wb_cabinet', uselist=True)
    wb_categories = relationship('WBCategory', uselist=True)
    adv_settings = relationship('AdvSetting', back_populates='wb_cabinet', uselist=True)
    wb_user_cabinets: Mapped[list[WBUserCabinet]] = relationship("WBUserCabinet",
                                                           back_populates="wb_cabinet",
                                                                 )
    active = Column(Boolean, default=True)

    expiration_time = Column(DateTime, nullable=False, server_default=text('now() + interval \'7 day\''))
    expiration_alarm_days_pass = Column(Integer, default=None)
    demo: Mapped[bool] = Column(Boolean, default=True)
    balance = Column(Float, default=0, server_default=text('0'), nullable=False)
    bonus = Column(Float, default=0, server_default=text('0'), nullable=False)
    white_list_update_active = Column(Boolean, default=False)
    __table_args__ = (
        Index('idx_balance_bonus', 'balance', 'bonus'),
        Index('idx_balance', 'balance'),
        Index('idx_bonus', 'bonus'),
    )


class WBToken(BaseTable):
    def __repr__(self):
        return f'user_id: {self.user_id}'
    api_key = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='wb_tokens',
                        lazy='joined')
    active = Column(Boolean, default=True)
    shop_id = mapped_column(String, nullable=True)
    __table_args__ = (UniqueConstraint('api_key', 'user_id', name='_api_key_user_id_uc'),)



    @property
    def __payload(self):
        try:
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            return result
        except:
            raise exceptions.NotValidTokenError

    def check_valid(self):
        try:
            result = jwt.decode(self.api_key, options={"verify_signature": False})
            if result:
                return True
        except Exception:
           return False


    def get_payload(self, key, default=0):
        payload = self.__payload
        return payload.get(key)


    @property
    def __expires(self):
        return datetime.datetime.utcfromtimestamp(self.__payload.get('exp'))

    @property
    def expires(self):
        return self.__expires


    @hybrid_property
    def shop_id(self):
        return self.get_payload('sid')

    @property
    def read_only(self) -> bool:
        # Проверяем, содержится ли категория "Токен только на чтение" в категориях
        return "Токен только на чтение" in self.categories

    @hybrid_property
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
        s = self.get_payload('s', 0)
        categories = set()
        for bit_position, category_name in categories_map.items():
            if s & (1 << bit_position):
                categories.add(category_name)
        return categories




class AdvKeyword(BaseTable):
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'), nullable=False)
    adv_setting = relationship('AdvSetting', back_populates='adv_keywords')
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    positive = Column(Boolean)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0)
    add_to_db = Column(Boolean, default=False)
    keyword_setting_id = Column(Integer, ForeignKey('keywordsetting.id'), nullable=False)
    keyword_setting = relationship('KeywordSetting', back_populates='adv_keywords')
    __table_args__ = (UniqueConstraint('text', 'date', 'adv_setting_id', name='_text_date_adv_setting_id_uc'),)





class WBCategory(BaseTable):
    cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)  # Добавляем внешний ключ, ссылающийся на кабинет
    wb_cabinet = relationship('WBCabinet', back_populates='wb_categories')  # Добавляем связь обратно к WbCabinet
    wb_category_name = Column(String, nullable=False)
    wb_cards = relationship('WBCard',
                            back_populates='wb_category',
                            uselist=True)


class WBCard(BaseTable): # Изменено название таблицы
    nmid = Column(Integer, unique=True, nullable=False)
    offer_id = Column(String)
    name = Column(String)
    wb_category_id = Column(Integer, ForeignKey('wbcategory.id'))
    wb_category = relationship('WBCategory', back_populates='wb_cards',
                               lazy='joined')
    json = Column(JSONB)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'))  # Добавляем внешний ключ к WbCabinet
    wb_cabinet = relationship('WBCabinet', back_populates='wb_cards')
    adv_setting_id = Column(Integer, ForeignKey('advsetting.id'))  # Добавлен внешний ключ
    adv_setting = relationship('AdvSetting', back_populates='wb_cards')
    updated = Column(Boolean, default=False)
    add_to_db = Column(Boolean, default=False)


    @hybrid_property
    def card_json(self):
        return json.loads(self.json)

    @property
    def brand(self):
        return self.card_json['brand']

    @property
    def photos(self):
        photos = self.card_json['photos']
        urls = []
        for photo in photos:
            url = photo['big']
            urls.append(url)
        return urls
    @property
    def SubjectId(self):
        return self.card_json['subjectID']



class AdvSetting(BaseTable):
    def __repr__(self):
        return f'name: {self.name}, adverdId: {self.adv_id}, bot_active: {self.bot_active}, active_status: {self.active_status}'
    favorite_users: Mapped[list[User]] = relationship(
        'User',
        secondary=favorite_advs_association,
        back_populates='favorites_advs')
    adv_id = Column(BIGINT(), unique=True) # Автоматическая рекламная кампания
    name = mapped_column(String, nullable=False)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    wb_cabinet: Mapped[WBCabinet] =  relationship('WBCabinet',
                                                 back_populates='adv_settings',
                                                 lazy='joined')
    wb_cards = relationship('WBCard',
                            back_populates='adv_setting',
                            cascade="all,"
                            "delete-orphan",
                            uselist=True)  # Изменено на множественное число
    active_status = Column(String, default=False)
    adv_keywords = relationship('AdvKeyword',
                                cascade="all, delete-orphan",
                                back_populates='adv_setting',
                                uselist=True)
    bot_active = Column(Boolean, default=False)
    nmids = Column(JSONB, default=[])
    keyword_settings: Mapped[list['KeywordSetting']] = relationship('KeywordSetting',
                                                                    cascade="all, delete-orphan",
                                                                    back_populates='adv_setting',
                                                                    uselist=True)
    pass_days = Column(Integer, default=30)
    boost = Column(Float, server_default=text('1'))
    type: Mapped[int] = Column(Integer, nullable=True)
    hard_min_ctr = Column(Float, nullable=True)
    max_cpc = Column(Float, nullable=True)
    min_views_for_ml_predict = Column(Integer, nullable=True, server_default=text('0'))
    payments = relationship(AdvPayment, back_populates='adv_setting', uselist=True)
    parsing_active =  mapped_column(Boolean, default=False)
    last_update = mapped_column(DateTime, nullable=True)
    bidder_active = mapped_column(Boolean, default=False)
    max_cpm = mapped_column(Integer, nullable=True)
    max_place = mapped_column(Integer, nullable=True)
    min_block_position = mapped_column(Integer, nullable=True, default=0)
    clusters_mode = mapped_column(Boolean, nullable=True, default=True)
    target_ctr_mode = mapped_column(Boolean, nullable=True, default=False)
    hide_small_query_keywords = mapped_column(Integer, nullable=True, default=0)
    target_ctr_mode_strategy = mapped_column(String, nullable=True, default='forward') # forward, keep
    new_auto_min_ctr_mode = mapped_column(Boolean,
                                          nullable=False,
                                          default=False,
                                          server_default='false'
                                          )
    reset_place = mapped_column(Boolean, nullable=True, default=True)
    _search_adv_id = mapped_column(Integer, nullable=True)
    bidder_step = mapped_column(Integer, nullable=True, default=DEFAULT_BIDDER_STEP)
    exponent_predict_ctr = mapped_column(Float,
                                         nullable=False,
                                         default=3,
                                         server_default='3')

    auction_boost_all_phrase_mode = mapped_column(Boolean,
                                                  nullable=False,
                                                  default=False,
                                                  server_default='false')
    plan_for_sales_for_day = mapped_column(Integer,
                                           nullable=True,
                                           default=None,)
    target_price_for_order = mapped_column(Float,
                                           nullable=True,
                                           default=None,)

    max_price_for_order = mapped_column(Float,
                                           nullable=True,
                                           default=None,)





    __table_args__ = (
        # Составной индекс для основного запроса
        Index('ix_adv_settings_cabinet_type_update',
              'wb_cabinet_id', 'type', 'last_update'),

        # Индекс для поиска по cabinet_id
        Index('ix_adv_settings_cabinet_id', 'wb_cabinet_id'),

        # Индекс для type, если он часто используется в запросах
        Index('ix_adv_settings_type', 'type'),
        Index('ix_advsetting_adv_id', 'adv_id'),
        Index('ix_advsetting_active_status', 'active_status'),
        Index('ix_advsetting_cabinet_bot_active', 'wb_cabinet_id', 'bot_active'),
        Index('ix_advsetting_name_pattern',
              'name',
              postgresql_using='gin',
              postgresql_ops={'name': 'gin_trgm_ops'}),
        Index('ix_name__nmids__search_adv_id', 'name', 'nmids', '_search_adv_id')
    )



    @property
    def search_adv_id(self): #Аукцион
        if self._search_adv_id:
            return self._search_adv_id
        if not self.name:
            return None
        name = self.name
        name = name.replace(' ', '')
        pattern = re.compile(r'<!-\[(\d+)\]-!>') # Изменено на поиск по всей строке
        match = re.search(pattern,  name)
        if not match:
            return None
        else:
           return int(match.group(1))

    @search_adv_id.setter
    def search_adv_id(self, value: int):
        assert isinstance(value, int)
        self._search_adv_id = value


    @search_adv_id.setter
    def search_adv_id(self, value: int):
        assert isinstance(value, int)
        self._search_adv_id = value


    @property
    def max_pay_for_order(self) -> Optional[int]:
        pattern = re.compile(r'<MAX_PAY>(\d+)!?</MAX_PAY>')  # Добавили !? для необязательного символа "!"
        match = re.search(pattern, self.name)
        if match:
            return int(match.group(1))
        return None

    @property
    def auto_max_bid(self) -> bool:
        pattern = re.compile(r'<MAX_PAY>(\d+)!?</MAX_PAY>')  # Используем тот же паттерн, чтобы найти !
        match = re.search(pattern, self.name)
        if match and '!' in match.group(0):  # Проверяем, есть ли "!" в найденной строке
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



class KeywordSetting(BaseTable):

    """
    hard_status
    0 - black listA
    1 - in test
    2 - white list

    """
    text = Column(String, nullable=False)
    adv_setting_id: Mapped[int] = mapped_column(ForeignKey('advsetting.id'))
    adv_setting: Mapped[AdvSetting] = relationship('AdvSetting',
                                                   back_populates='keyword_settings',
                                                   uselist=False)
    predict_ctr = Column(Float, nullable=True)
    adv_keywords = relationship('AdvKeyword',
                                back_populates='keyword_setting',
                                cascade='all, delete-orphan',
                                uselist=True)
    hard_status = Column(Integer, default=1)
    added_clicks = Column(Integer)
    added_views = Column(Integer)
    auto_block = Column(Boolean)
    __table_args__ = (UniqueConstraint('text', 'adv_setting_id'),
                      Index('ix_text_adv_setting_id', 'text', 'adv_setting_id'),
                      # Составной индекс для запроса
                      Index('ix_keywordsetting_status_adv',
                            'hard_status', 'adv_setting_id'),
                    Index('ix_keywordsetting_adv_setting_id', 'adv_setting_id'),
                    Index('ix_keywordsetting_text', 'text'),
                      )





@dataclass
class WBItemPosition:
    nmid: int = None
    base_position: int = None
    real_position: int = None
    timestamp:  datetime = None
    promo_position: int = None
    cpm: int = None
    adv_id: int = None
    keyword_text: str = None
    adv_type: int = None

    @property
    def type_native(self)-> str:
        if self.adv_type == 9:
            return 'search'
        elif self.adv_type == 8:
            return 'auto'

    def to_dict(self):
        timestamp: datetime = self.timestamp
        str_timestamp = timestamp.isoformat()
        return {
            'real_position': self.real_position,
            'promo_position': self.promo_position,
            'base_position': self.base_position,
            'keyword_text': self.keyword_text,
            'cpm': self.cpm,
            'adv_id': self.adv_id,
            'nmid': self.nmid,
            'timestamp': str_timestamp,
            'adv_type': self.adv_type
        }

    @staticmethod
    def from_dict(data):
        position = WBItemPosition()
        position.real_position = data['real_position']
        position.promo_position = data['promo_position']
        position.base_position = data['base_position']
        position.cpm = data['cpm']
        position.adv_id = data['adv_id']
        position.nmid = data['nmid']
        try:
           str_timestamp = data['timestamp']
           position.timestamp = datetime.datetime.fromisoformat(str_timestamp)
        except:
            position.timestamp = None

        position.keyword_text = data['keyword_text']
        try:
            position.adv_type = data['adv_type']
        except:
            position.adv_type = None

        return position
