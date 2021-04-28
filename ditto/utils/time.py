import datetime
import zoneinfo

from typing import Optional, Union

import humanize

from .files import get_base_dir
from .strings import ordinal

__all__ = (
    "MAIN_TIMEZONES",
    "TIMEZONE_ALIASES",
    "update_time",
    "readable_timestamp",
    "human_friendly_timestamp",
    "human_friendly_timedelta",
    "normalise_timedelta",
)


BASE_DIR = get_base_dir()

MAIN_TZ_FILE = "res/cldr/MainTimeZones.txt"
TZ_ALIASES_FILE = "res/cldr/TimeZoneAliases.txt"

# ALL_TIMEZONES: list[str] = []

MAIN_TIMEZONES: dict[str, zoneinfo.ZoneInfo] = {}

TIMEZONE_ALIASES: dict[str, str] = {}

with open(BASE_DIR / TZ_ALIASES_FILE) as f:
    for record in f:
        if record.strip() and not record.startswith("#"):
            alias, key = (timezone.strip() for timezone in record.split(";", 1))

            try:
                tzinfo = zoneinfo.ZoneInfo(key)
            except:
                continue

            TIMEZONE_ALIASES[alias] = key

            # Skip some specific timezones
            if alias.startswith("SystemV") or any(c.isdigit() for c in alias):
                continue

            MAIN_TIMEZONES[alias] = tzinfo


def update_time(a: datetime.datetime, b: datetime.datetime) -> datetime.datetime:
    return a.replace(hour=b.hour, minute=b.minute, second=b.second, microsecond=b.microsecond)


def readable_timestamp(datetime: datetime.datetime, /) -> str:
    return datetime.strftime(f"%a %b %d, %Y @ %H:%M:%S %Z")


def human_friendly_timestamp(datetime: datetime.datetime, /) -> str:
    day = datetime.day
    return datetime.strftime(f"%I:%M%p on %A the {ordinal(day)} of %B, %Y")


def human_friendly_timedelta(timedelta: datetime.timedelta, /, relative_to: Optional[datetime.datetime]) -> str:
    return humanize.naturaldelta(timedelta, when=relative_to)


def normalise_timedelta(delta: Union[float, datetime.timedelta]) -> datetime.timedelta:
    if isinstance(delta, (int, float)):
        return datetime.timedelta(seconds=delta)
    return delta
