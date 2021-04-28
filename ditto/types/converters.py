from __future__ import annotations

import datetime
import zoneinfo

from typing import Any, Generic, Optional, TYPE_CHECKING, TypeVar

import aiohttp
import parsedatetime

import discord
from discord.ext import commands

from jishaku.codeblocks import codeblock_converter, Codeblock
from jishaku.modules import ExtensionConverter

from ..config import CONFIG
from ..utils.time import TIMEZONE_ALIASES, update_time

if TYPE_CHECKING:
    from ..core.context import Context


__all__ = (
    "CONVERTERS",
    "Extension",
)


ET = TypeVar("ET", bound=discord.Enum)


class Extension(str):
    ...


class _MissingSentinel:
    def __repr__(self) -> str:
        return "MISSING"


MISSING: Any = _MissingSentinel()


class CommandConverter(commands.Converter[commands.Command]):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> commands.Command:
        result = ctx.bot.get_command(argument)

        if result is None:
            raise commands.BadArgument(f'Command "{argument}" not found.')
        return result


class DatetimeConverter(commands.Converter[datetime.datetime]):
    calendar = parsedatetime.Calendar(version=parsedatetime.VERSION_CONTEXT_STYLE)

    @staticmethod
    async def get_timezone(ctx: Context) -> datetime.tzinfo:
        return await ctx.get_timezone() or datetime.timezone.utc

    @classmethod
    def parse_local(
        cls,
        argument: str,
        /,
        *,
        timezone: datetime.tzinfo = datetime.timezone.utc,
        now: Optional[datetime.datetime] = None,
    ) -> list[tuple[datetime.datetime, int, int]]:
        now = now or datetime.datetime.now(datetime.timezone.utc)

        times: list[tuple[datetime.datetime, int, int]] = []

        dates = DatetimeConverter.calendar.nlp(argument, sourceTime=now)

        if dates is None:
            return times

        for _, _, begin, end, dt_string in dates:
            dt, status = cls.calendar.parseDT(datetimeString=dt_string, sourceTime=now, tzinfo=timezone)

            if not status.hasTime:
                dt = update_time(dt, now)

            if status.accuracy == parsedatetime.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=now.day + 1)

            times.append((dt, begin, end))

        return times

    @classmethod
    async def parse(
        cls,
        argument: str,
        /,
        *,
        timezone: datetime.tzinfo = datetime.timezone.utc,
        now: Optional[datetime.datetime] = None,
    ) -> list[tuple[datetime.datetime, int, int]]:
        now = now or datetime.datetime.now(datetime.timezone.utc)

        # If no duckling server default to parsedatetime
        if CONFIG.MISC.DUCKLING_SERVER is None:
            return cls.parse_local(argument, timezone=timezone, now=now)

        times = []

        async with aiohttp.ClientSession() as session:
            async with session.post(
                CONFIG.MISC.DUCKLING_SERVER,
                data={
                    "locale": "en_US",  # Todo: locale based on tz?
                    "text": argument,
                    "dims": str(["time"]),
                    "tz": str(timezone),
                    # 'reftime': now.isoformat(),
                },
            ) as response:
                data = await response.json()

                for time in data:
                    if time["dim"] == "time" and "value" in time["value"]:
                        times.append(
                            (
                                datetime.datetime.fromisoformat(time["value"]["value"]),
                                time["start"],
                                time["end"],
                            )
                        )

        return times

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> datetime.datetime:

        timezone = await cls.get_timezone(ctx)
        now = ctx.message.created_at.astimezone(tz=timezone)

        parsed_times = await cls.parse(argument, timezone=timezone, now=now)

        if len(parsed_times) == 0:
            raise commands.BadArgument("Could not parse time.")
        elif len(parsed_times) > 1:
            ...  # TODO: Raise on too many?

        return parsed_times[0][0]


class WhenAndWhatConverter(commands.Converter[tuple[datetime.datetime, str]]):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> tuple[datetime.datetime, str]:  # type: ignore[override]

        timezone = await DatetimeConverter.get_timezone(ctx)
        now = ctx.message.created_at.astimezone(tz=timezone)

        # Strip some common stuff
        for prefix in ("me to ", "me in ", "me at ", "me that "):
            if argument.startswith(prefix):
                argument = argument[len(prefix) :]
                break

        for suffix in ("from now",):
            if argument.endswith(suffix):
                argument = argument[: -len(suffix)]

        argument = argument.strip()

        # Determine the date argument
        parsed_times = await DatetimeConverter.parse(argument, timezone=timezone, now=now)

        if len(parsed_times) == 0:
            raise commands.BadArgument("Could not parse time.")
        elif len(parsed_times) > 1:
            ...  # TODO: Raise on too many?

        when, begin, end = parsed_times[0]

        if begin != 0 and end != len(argument):
            raise commands.BadArgument("Could not distinguish time from argument.")

        if begin == 0:
            what = argument[end + 1 :].lstrip(" ,.!:;")
        else:
            what = argument[:begin].strip()

        for prefix in ("to ",):
            if what.startswith(prefix):
                what = what[len(prefix) :]

        return (when, what)


class ZoneInfoConverter(commands.Converter[zoneinfo.ZoneInfo]):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> zoneinfo.ZoneInfo:
        argument = argument.replace(" ", "_").strip()

        if argument in TIMEZONE_ALIASES:
            argument = TIMEZONE_ALIASES[argument]

        try:
            return zoneinfo.ZoneInfo(argument)
        except Exception:  # catch all due to BPO: 41530
            raise commands.BadArgument(f'Time Zone "{argument}" not found.')


class PosixFlags(commands.FlagConverter, prefix="--", delimiter=" "):  # type: ignore[call-arg]
    ...


class EmbedConverter(commands.Converter[discord.Embed]):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> discord.Embed:
        try:
            code = codeblock_converter(argument)
            return discord.Embed.from_dict(code.content)
        except Exception:
            raise commands.BadArgument("Could not generate embed from supplied JSON.")


class EnumConverter(commands.Converter[discord.Enum], Generic[ET]):
    _type: type[ET] = MISSING  # type: ignore

    def __init_subclass__(cls, *, enum: type[ET] = MISSING) -> None:
        super().__init_subclass__()
        cls._type = enum

    async def convert(self, ctx: Context, argument: str) -> ET:
        if self._type is MISSING:
            try:
                self._type = self.__orig_class__.__args__[0]  # type: ignore
            except (AttributeError, IndexError):
                raise RuntimeError("No enum type found.")

        value = int(argument) if argument.isdigit() else argument
        value = self._type.try_value(value)  # type: ignore
        if value == argument:
            raise commands.BadArgument(f"Could not convert to Enum: {self._type.__name__}")
        return value  # type: ignore


CONVERTERS: dict[type[Any], Any] = {
    Codeblock: codeblock_converter,
    datetime.datetime: DatetimeConverter,
    Extension: ExtensionConverter,
    discord.Embed: EmbedConverter,
    commands.Command: CommandConverter,
    zoneinfo.ZoneInfo: ZoneInfoConverter,
    tuple[datetime.datetime, str]: WhenAndWhatConverter,  # type: ignore[misc]
    discord.Status: EnumConverter[discord.Status],
}
