import re
from datetime import datetime


PHONE_PATTERN = re.compile(r"^\+?[0-9\-\s\(\)]{10,20}$")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(phone.strip()))


def is_valid_time(time_value: str) -> bool:
    return bool(TIME_PATTERN.match(time_value.strip()))


def format_datetime_human(date_iso: str, time_value: str) -> str:
    dt = datetime.strptime(f"{date_iso} {time_value}", "%Y-%m-%d %H:%M")
    return dt.strftime("%d.%m.%Y %H:%M")
