from __future__ import annotations

import datetime
import zoneinfo

from typing import TYPE_CHECKING

import parsedatetime

from discord.ext import commands

from jishaku.codeblocks import codeblock_converter, Codeblock
from jishaku.modules import ExtensionConverter

from ..utils.time import TIMEZONE_ALIASES, update_time

if TYPE_CHECKING:
    from ..core.context import Context


__all__ = (
    "CONVERTERS",
    "Extension",
)


class Extension(str):
    ...


class CommandConverter(commands.Converter):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> commands.Command:
        result = ctx.bot.get_command(argument)

        if result is None:
            raise commands.BadArgument(f'Command "{argument}" not found.')
        return result


class DatetimeConverter(commands.Converter):
    calendar = parsedatetime.Calendar(version=parsedatetime.VERSION_CONTEXT_STYLE)

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> datetime.datetime:

        timezone = await cls.get_timezone(ctx)
        now = ctx.message.created_at.astimezone(tz=timezone)

        dt, status = cls.calendar.parseDT(datetimeString=argument, sourceTime=now, tzinfo=timezone)

        if isinstance(status, int):
            raise Exception("What the fuck?")

        if not status.hasDateOrTime:
            raise commands.BadArgument("Could not determine time provided.")

        if not status.hasTime:
            dt = update_time(dt, now)

        if status.accuracy == parsedatetime.pdtContext.ACU_HALFDAY:
            dt = dt.replace(day=now.day + 1)

        return dt

    @classmethod
    async def get_timezone(cls, ctx: Context) -> datetime.tzinfo:
        return await ctx.get_timezone() or datetime.timezone.utc


class WhenAndWhatConverter(commands.Converter):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> tuple[datetime.datetime, str]:

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
        dates = DatetimeConverter.calendar.nlp(argument, sourceTime=now)

        if dates is None or len(dates) == 0:
            raise commands.BadArgument("Could not determine time provided.")
        elif len(dates) > 1:
            ...  # TODO: Raise on too many?

        _, _, begin, end, dt_string = dates[0]

        if begin != 0 and end != len(argument):
            raise commands.BadArgument("Could not distinguish time from argument.")

        when = await DatetimeConverter.convert(ctx, dt_string)

        if begin == 0:
            what = argument[end + 1 :].lstrip(" ,.!:;")
        else:
            what = argument[:begin].strip()

        for prefix in ("to ",):
            if what.startswith(prefix):
                what = what[len(prefix) :]

        return (when, what)


class ZoneInfoConverter(commands.Converter):
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


CONVERTERS = {
    Codeblock: codeblock_converter,
    datetime.datetime: DatetimeConverter,
    Extension: ExtensionConverter,
    commands.Command: CommandConverter,
    zoneinfo.ZoneInfo: ZoneInfoConverter,
    tuple[datetime.datetime, str]: WhenAndWhatConverter,  # type: ignore[misc]
}
