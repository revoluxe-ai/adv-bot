from app.modules.common_slaves.wildberries.exceptions import ApiForbiddenError



class CardNotFoundInDB(Exception):
    pass


class PositionNotFoundError(Exception):
    pass


class NotFoundPositionWithCMPError(Exception):
    pass