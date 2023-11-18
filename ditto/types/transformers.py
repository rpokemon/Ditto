from __future__ import annotations

import datetime
import zoneinfo

import discord

from ..core.bot import BotBase
from ..db.tables import TimeZones
from ..utils.time import ALL_TIMEZONES, human_friendly_timestamp
from .converters import DatetimeConverter

__all__ = (
    "GuildTransformer",
    "WhenAndWhatTransformer",
    "ZoneInfoTransformer",
)


class GuildTransformer(discord.app_commands.Transformer):
    @property
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.integer

    async def transform(self, interaction: discord.Interaction, value: int) -> discord.Guild:
        guild = interaction.client.get_guild(value)

        if guild is None:
            raise ValueError(f"Could not find guild with id '{value}'.")

        return guild

    async def autocomplete(self, interaction: discord.Interaction, value: str) -> list[discord.app_commands.Choice[int]]:
        suggestions = []

        for guild in interaction.client.guilds:
            if guild.get_member(interaction.user.id) is not None:
                suggestions.append(discord.app_commands.Choice(name=guild.name, value=guild.id))

        return suggestions[:25]


class DatetimeTransformer(discord.app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction[BotBase], value: str) -> datetime.datetime:
        cached_record = TimeZones.get_cached(user_id=interaction.user.id)
        if cached_record is not None:
            timezone = zoneinfo.ZoneInfo(cached_record["time_zone"])
        else:
            async with interaction.client.pool.acquire() as connection:
                timezone = await TimeZones.get_timezone(connection, interaction.user) or datetime.timezone.utc

        now = interaction.created_at.astimezone(tz=timezone)

        parsed_times = await DatetimeConverter.parse(value, timezone=timezone, now=now)

        if len(parsed_times) == 0:
            raise ValueError("Could not parse time.")
        elif len(parsed_times) > 1:
            ...  # TODO: Raise on too many?

        return parsed_times[0][0]

    async def autocomplete(
        self,
        interaction: discord.Interaction[BotBase],
        value: str | None,
    ) -> list[discord.app_commands.Choice[str]]:
        if value is None:
            return []

        cached_record = TimeZones.get_cached(user_id=interaction.user.id)
        if cached_record is not None:
            timezone = zoneinfo.ZoneInfo(cached_record["time_zone"])
        else:
            async with interaction.client.pool.acquire() as connection:
                timezone = await TimeZones.get_timezone(connection, interaction.user) or datetime.timezone.utc

        now = interaction.created_at.astimezone(tz=timezone)

        parsed_times = await DatetimeConverter.parse(value, timezone=timezone, now=now)

        if len(parsed_times) != 1:
            return []

        return [
            discord.app_commands.Choice(name=human_friendly_timestamp(when), value=value[start:end])
            for when, start, end in parsed_times
        ]


class WhenAndWhatTransformer(discord.app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction[BotBase], value: str) -> tuple[datetime.datetime, str]:
        cached_record = TimeZones.get_cached(user_id=interaction.user.id)
        if cached_record is not None:
            timezone = zoneinfo.ZoneInfo(cached_record["time_zone"])
        else:
            async with interaction.client.pool.acquire() as connection:
                timezone = await TimeZones.get_timezone(connection, interaction.user) or datetime.timezone.utc

        now = interaction.created_at.astimezone(tz=timezone)

        # Strip some common stuff
        for prefix in ("me to ", "me in ", "me at ", "me that "):
            if value.startswith(prefix):
                argument = value[len(prefix) :]
                break

        for suffix in ("from now",):
            if value.endswith(suffix):
                argument = value[: -len(suffix)]

        argument = value.strip()

        # Determine the date argument
        parsed_times = await DatetimeConverter.parse(argument, timezone=timezone, now=now)

        if len(parsed_times) == 0:
            raise ValueError("Could not parse time.")
        elif len(parsed_times) > 1:
            ...  # TODO: Raise on too many?

        when, begin, end = parsed_times[0]

        if begin != 0 and end != len(argument):
            raise ValueError("Could not distinguish time from argument.")

        if begin == 0:
            what = argument[end + 1 :].lstrip(" ,.!:;")
        else:
            what = argument[:begin].strip()

        for prefix in ("to ",):
            if what.startswith(prefix):
                what = what[len(prefix) :]

        return (when, what)


class ZoneInfoTransformer(discord.app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> zoneinfo.ZoneInfo:
        try:
            return zoneinfo.ZoneInfo(value)
        except Exception:  # catch all due to BPO: 41530
            raise ValueError(f'Time Zone "{value}" not found.')

    async def autocomplete(self, interaction: discord.Interaction, value: str) -> list[discord.app_commands.Choice[str]]:
        choices = []
        for name, tzinfo in ALL_TIMEZONES.items():
            if name.lower().startswith(value.lower()):
                choices.append(discord.app_commands.Choice(name=name, value=tzinfo.key))

        return choices[:25]
