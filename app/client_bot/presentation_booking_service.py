from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import Select, and_, select, update
from sqlalchemy.exc import IntegrityError

from app.utils.db.models import (
    PresentationBooking,
    PresentationBookingStatus,
    PresentationSlot,
    User,
)
from app.client_bot.const import SUPPORT_USER_NAME
from app.utils.db.session_maker import get_async_session_maker as sm

MSK_TZ = timezone(timedelta(hours=3))
WEEKDAY_RU_SHORT = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


@dataclass(frozen=True, slots=True)
class PresentationSlotView:
    slot_id: int
    start_at_utc: datetime
    duration_minutes: int
    is_active: bool
    booked_by_user_id: int | None

    @property
    def is_booked(self) -> bool:
        return self.booked_by_user_id is not None


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utc_naive_to_msk(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC).astimezone(MSK_TZ)


def format_slot_for_human(slot: PresentationSlotView) -> str:
    start_msk = utc_naive_to_msk(slot.start_at_utc)
    end_msk = start_msk + timedelta(minutes=slot.duration_minutes)
    weekday = WEEKDAY_RU_SHORT[start_msk.weekday()]
    return f"{weekday}, {start_msk:%d.%m %H:%M}-{end_msk:%H:%M} МСК"


async def list_available_slots(limit: int = 12) -> list[PresentationSlotView]:
    now = utc_now_naive()
    async with sm(read_only=True) as session:
        stmt: Select[tuple[PresentationSlot, int | None]] = (
            select(PresentationSlot, PresentationBooking.user_id)
            .outerjoin(
                PresentationBooking,
                PresentationBooking.slot_id == PresentationSlot.id,
            )
            .where(
                and_(
                    PresentationSlot.is_active.is_(True),
                    PresentationSlot.start_at >= now,
                )
            )
            .order_by(PresentationSlot.start_at.asc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
    out: list[PresentationSlotView] = []
    for slot, booked_by_user_id in rows:
        if booked_by_user_id is not None:
            continue
        out.append(
            PresentationSlotView(
                slot_id=slot.id,
                start_at_utc=slot.start_at,
                duration_minutes=slot.duration_minutes,
                is_active=slot.is_active,
                booked_by_user_id=booked_by_user_id,
            )
        )
    return out


async def list_slots_for_admin(limit: int = 20) -> list[PresentationSlotView]:
    now = utc_now_naive()
    async with sm(read_only=True) as session:
        stmt: Select[tuple[PresentationSlot, int | None]] = (
            select(PresentationSlot, PresentationBooking.user_id)
            .outerjoin(
                PresentationBooking,
                PresentationBooking.slot_id == PresentationSlot.id,
            )
            .where(PresentationSlot.start_at >= now)
            .order_by(PresentationSlot.start_at.asc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()
    return [
        PresentationSlotView(
            slot_id=slot.id,
            start_at_utc=slot.start_at,
            duration_minutes=slot.duration_minutes,
            is_active=slot.is_active,
            booked_by_user_id=booked_by_user_id,
        )
        for slot, booked_by_user_id in rows
    ]


async def create_slot(
    *,
    start_at_utc: datetime,
    duration_minutes: int,
    admin_telegram_id: int,
) -> PresentationSlot:
    async with sm(read_only=False) as session:
        admin = (
            (
                await session.execute(
                    select(User.id).where(User.user_telegram_id == admin_telegram_id)
                )
            )
            .scalars()
            .first()
        )
        slot = PresentationSlot(
            start_at=start_at_utc,
            duration_minutes=duration_minutes,
            is_active=True,
            created_by_user_id=admin,
        )
        session.add(slot)
        await session.commit()
        await session.refresh(slot)
        return slot


async def deactivate_slot(slot_id: int) -> bool:
    async with sm(read_only=False) as session:
        stmt = (
            update(PresentationSlot)
            .where(PresentationSlot.id == slot_id, PresentationSlot.is_active.is_(True))
            .values(is_active=False)
        )
        result = await session.execute(stmt)
        await session.commit()
        return bool(result.rowcount)


async def get_slot(slot_id: int) -> PresentationSlotView | None:
    async with sm(read_only=True) as session:
        stmt = (
            select(PresentationSlot, PresentationBooking.user_id)
            .outerjoin(PresentationBooking, PresentationBooking.slot_id == PresentationSlot.id)
            .where(PresentationSlot.id == slot_id)
            .limit(1)
        )
        row = (await session.execute(stmt)).first()
    if row is None:
        return None
    slot, booked_by_user_id = row
    return PresentationSlotView(
        slot_id=slot.id,
        start_at_utc=slot.start_at,
        duration_minutes=slot.duration_minutes,
        is_active=slot.is_active,
        booked_by_user_id=booked_by_user_id,
    )


async def create_booking(slot_id: int, user_telegram_id: int) -> str:
    now = utc_now_naive()
    async with sm(read_only=False) as session:
        user = (
            (
                await session.execute(
                    select(User).where(User.user_telegram_id == user_telegram_id).limit(1)
                )
            )
            .scalars()
            .first()
        )
        if user is None:
            return "user_not_found"

        slot = (
            (
                await session.execute(
                    select(PresentationSlot)
                    .where(PresentationSlot.id == slot_id)
                    .with_for_update()
                )
            )
            .scalars()
            .first()
        )
        if slot is None or not slot.is_active or slot.start_at < now:
            return "slot_unavailable"

        already_booked = (
            (
                await session.execute(
                    select(PresentationBooking.id)
                    .where(
                        PresentationBooking.slot_id == slot_id,
                        PresentationBooking.status == PresentationBookingStatus.BOOKED,
                    )
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if already_booked is not None:
            return "slot_taken"

        booking = PresentationBooking(
            slot_id=slot_id,
            user_id=user.id,
            status=PresentationBookingStatus.BOOKED,
        )
        session.add(booking)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return "slot_taken"
    return "ok"


def presentation_manager_confirm_url(slot_text_human: str) -> str:
    confirm_text = f"Подтверждаю запись на презентацию {slot_text_human}"
    return f"https://t.me/{SUPPORT_USER_NAME}?text={quote(confirm_text)}"


async def get_user_upcoming_booked_slot_human(user_telegram_id: int) -> str | None:
    """Текст слота для ближайшей активной записи (BOOKED, не отменена, слот ещё не закончился)."""
    now = utc_now_naive()
    async with sm(read_only=True) as session:
        stmt = (
            select(PresentationSlot)
            .join(
                PresentationBooking,
                PresentationBooking.slot_id == PresentationSlot.id,
            )
            .join(User, User.id == PresentationBooking.user_id)
            .where(
                User.user_telegram_id == user_telegram_id,
                PresentationBooking.status == PresentationBookingStatus.BOOKED,
                PresentationBooking.cancelled_at.is_(None),
            )
            .order_by(PresentationSlot.start_at.asc())
        )
        slots = (await session.execute(stmt)).scalars().all()
    for slot in slots:
        end_at = slot.start_at + timedelta(minutes=slot.duration_minutes)
        if end_at >= now:
            view = PresentationSlotView(
                slot_id=slot.id,
                start_at_utc=slot.start_at,
                duration_minutes=slot.duration_minutes,
                is_active=slot.is_active,
                booked_by_user_id=None,
            )
            return format_slot_for_human(view)
    return None
