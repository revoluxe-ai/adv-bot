import datetime

import jwt
from new.wildberries import models

from . import exceptions

"""
"Контент",
"Аналитика",
"Цены и скидки",
"Маркетплейс",
"Статистика",
"Продвижение",
"Вопросы и отзывы",
"Рекомендации",
"Токен только на чтение",
"""

rights_for_adv_bot = {'Контент', 'Продвижение'}

def check_token_rights(token: models.Token):
     try:
         result = all([
             token.expires > datetime.datetime.now(),
             rights_for_adv_bot.issubset(token.categories),
             ~{'Токен только на чтение'}.issubset(token.categories)
         ])
     except jwt.exceptions.DecodeError:
         raise exceptions.NotValidTokenError


     return result





