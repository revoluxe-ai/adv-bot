from __future__ import annotations

import datetime
from dataclasses import dataclass



@dataclass(frozen=True)
class AdvInfoPlacement:
    search: bool
    recommendations: bool


@dataclass(frozen=True)
class AdvInfoSettings:
    name: str
    payment_type: str
    placements: AdvInfoPlacement


@dataclass(frozen=True)
class AdvInfoNmSetting:
    nmid: int
    subject_id: int
    subject_name: str
    search_bid_kopecks: int
    recommendations_bid_kopecks: int


@dataclass(frozen=True)
class AdvInfoTimestamps:
    created: datetime.datetime
    updated: datetime.datetime
    started: datetime.datetime | None
    deleted: datetime.datetime


@dataclass(frozen=True)
class AdvInfoSimple:
    adv_id: int
    bid_type: str
    status: int
    settings: AdvInfoSettings
    nmids_settings: list[AdvInfoNmSetting]
    timestamps: AdvInfoTimestamps


@dataclass(frozen=True)
class AdvInfoDTO:
    adv_id: int
    auto_adv: AdvInfoSimple | None
    search_adv: AdvInfoSimple
