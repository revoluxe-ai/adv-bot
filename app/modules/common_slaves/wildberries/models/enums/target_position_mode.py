from enum import StrEnum

#TODO Надо выпилить, не актуально. Теперь режим задается в ComplexAdv.strategy
class TargetPositionMode(StrEnum):
    MIN_CPA = 'MIN_CPA'
    MAX_CART_TO_VIEWS_CONV = 'MAX_CART_TO_VIEWS_CONV'
