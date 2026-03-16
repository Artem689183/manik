import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def _month_add(year: int, month: int, shift: int) -> tuple[int, int]:
    idx = (year * 12 + (month - 1)) + shift
    return idx // 12, (idx % 12) + 1


def get_booking_window() -> tuple[date, date]:
    start = date.today()
    end = start + timedelta(days=30)
    return start, end


def build_calendar(
    year: int,
    month: int,
    callback_prefix: str,
    allowed_dates: set[str] | None = None,
) -> InlineKeyboardMarkup:
    start, end = get_booking_window()
    if allowed_dates is None:
        allowed_dates = set()
        cur = start
        while cur <= end:
            allowed_dates.add(cur.isoformat())
            cur += timedelta(days=1)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"{MONTHS_RU[month - 1]} {year}", callback_data="ignore")

    for wd in WEEKDAYS:
        kb.button(text=wd, callback_data="ignore")

    month_matrix = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    for week in month_matrix:
        for day in week:
            day_iso = day.isoformat()
            in_range = start <= day <= end
            in_month = day.month == month
            is_clickable = in_range and in_month
            has_slots = day_iso in allowed_dates

            if is_clickable and has_slots:
                kb.button(text=str(day.day), callback_data=f"{callback_prefix}:d:{day_iso}")
            elif is_clickable:
                # Date is clickable, but currently has no free slots.
                kb.button(text=f"·{day.day}", callback_data=f"{callback_prefix}:d:{day_iso}")
            else:
                kb.button(text=" ", callback_data="ignore")

    prev_y, prev_m = _month_add(year, month, -1)
    next_y, next_m = _month_add(year, month, 1)

    current_first = date(year, month, 1)
    min_first = date(start.year, start.month, 1)
    max_first = date(end.year, end.month, 1)

    if current_first > min_first:
        kb.button(text="⬅️", callback_data=f"{callback_prefix}:n:{prev_y}-{prev_m:02d}")
    else:
        kb.button(text=" ", callback_data="ignore")

    kb.button(text="Закрыть", callback_data=f"{callback_prefix}:close")

    if current_first < max_first:
        kb.button(text="➡️", callback_data=f"{callback_prefix}:n:{next_y}-{next_m:02d}")
    else:
        kb.button(text=" ", callback_data="ignore")

    kb.adjust(1, 7, *([7] * len(month_matrix)), 3)
    return kb.as_markup()
