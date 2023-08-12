import datetime
import zoneinfo

import humanize

from .strings import ordinal

__all__ = (
    "ALL_TIMEZONES",
    "update_time",
    "readable_timestamp",
    "human_friendly_timestamp",
    "human_friendly_timedelta",
    "normalise_timedelta",
)


ALL_TIMEZONES: dict[str, zoneinfo.ZoneInfo] = {
    name.replace("_", " "): zoneinfo.ZoneInfo(zone)
    for zone in zoneinfo.available_timezones()
    for _, _, name in [zone.partition("/")]
}


def update_time(a: datetime.datetime, b: datetime.datetime) -> datetime.datetime:
    return a.replace(hour=b.hour, minute=b.minute, second=b.second, microsecond=b.microsecond)


def readable_timestamp(datetime: datetime.datetime, /) -> str:
    return datetime.strftime(f"%a %b %d, %Y @ %H:%M:%S %Z")


def human_friendly_timestamp(datetime: datetime.datetime, /) -> str:
    day = datetime.day
    return datetime.strftime(f"%I:%M%p on %A the {ordinal(day)} of %B, %Y")


def human_friendly_timedelta(timedelta: datetime.timedelta) -> str:
    return humanize.naturaldelta(timedelta)


def normalise_timedelta(delta: float | datetime.timedelta) -> datetime.timedelta:
    if isinstance(delta, (int, float)):
        return datetime.timedelta(seconds=delta)
    return delta
