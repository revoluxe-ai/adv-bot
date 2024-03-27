from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import new

class UnknownApiRequestError(BaseException):
   pass


class ApiErrorWithCode(BaseException):
    def __init__(self, code, message, rejection):
        self.code = code
        self.message = message
        self.rejection = rejection
        m = 'Типовая ошибка Api Wildberries'
        super().__init__(f'{m} code: {self.code}, message: {self.message}, rejection: {self.rejection}')




class NotValidTokenError(BaseException):
    pass


class TokenExpiredError(Exception):
    def __init__(self, text):
        self.text = text
        m = 'Срок действия токена истек'
        super().__init__(f'{m} text: {self.text}')


class TokensFromDifferentShopsError(BaseException):
    def __init__(self):
        m = 'Токены принадлежат разным магазинам'
        super().__init__(f'{m}')




class ApiForbiddenError(Exception):
   def __init__(self, text, wb_user_cabinet: 'new.types.WBUserCabinet'):
       self.text = text
       self.wb_user_cabinet = wb_user_cabinet
       m = 'API доступ запрещен'
       super().__init__(f'{m} text: {self.text}')


class TooManyRequests(Exception):
    pass