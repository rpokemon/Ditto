from __future__ import annotations

import zoneinfo

from typing import TYPE_CHECKING, Union

import discord
from discord.ext import commands

from jishaku.codeblocks import codeblock_converter, Codeblock  # type: ignore
from jishaku.modules import ExtensionConverter  # type: ignore

if TYPE_CHECKING:
    from .context import Context


__all__ = (
    "CONVERTERS",
    "Extension",
    "VocalGuildChannel",
    "GuildChannel",
    "User",
    "Emoji",
    "Message",
    "DiscordObject",
)

VocalGuildChannel = Union[
    discord.VoiceChannel,
    discord.StageChannel,
]


GuildChannel = Union[
    discord.TextChannel,
    VocalGuildChannel,  # type: ignore
    discord.CategoryChannel,
    discord.StoreChannel,
]

User = Union[
    discord.Member,
    discord.User,
]

Emoji = Union[
    discord.Emoji,
    discord.PartialEmoji,
]

Message = Union[
    discord.Message,
    discord.PartialMessage,
]

DiscordObject = Union[
    discord.Guild,
    discord.Role,
    GuildChannel,  # type: ignore
    User,  # type: ignore
    Emoji,  # type: ignore
    Message,  # type: ignore
    discord.Invite,
]


class Extension(str):
    ...


class CommandConverter(commands.Converter):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> commands.Command:  # type: ignore
        result = ctx.bot.get_command(argument)

        if result is None:
            raise commands.BadArgument(f'Command "{argument}" not found.')
        return result


class ZoneInfoConverter(commands.Converter):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> zoneinfo.ZoneInfo:  # type: ignore
        try:
            return zoneinfo.ZoneInfo(argument.replace(" ", "_"))
        except Exception:  # catch all due to BPO: 41530
            raise commands.BadArgument(f'Time Zone "{argument}" not found.')


CONVERTERS = {
    Codeblock: codeblock_converter,
    Extension: ExtensionConverter,
    commands.Command: CommandConverter,
    zoneinfo.ZoneInfo: ZoneInfoConverter,
}
