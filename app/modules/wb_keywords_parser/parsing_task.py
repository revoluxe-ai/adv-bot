from dataclasses import dataclass


@dataclass
class ParsingTask:
    keyword: str
    nmid: int
    adv_id_order: str