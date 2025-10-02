from enum import Enum


class BidPaymentType(Enum):
    CPM = "cpm"  # Оплата за показы
    CPC = "cpc"  # Оплата за клики
