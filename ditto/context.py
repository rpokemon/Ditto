from __future__ import annotations

import zoneinfo

from typing import Any, Awaitable, Optional, TYPE_CHECKING

import donphan  # type: ignore

import discord
from discord.ext import commands

from .db import Time_Zones
from .utils.guild import user_in_guild

if TYPE_CHECKING:
    from .bot import BotBase

__all__ = ("Context",)


class Context(commands.Context):
    bot: BotBase  # type: ignore

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)  # type: ignore
        self.db = donphan.MaybeAcquire(pool=self.bot.pool)

    def reply(self, *args, **kwargs):
        mention_author = kwargs.pop("mention_author", True)
        return super().reply(*args, mention_author=mention_author, **kwargs)

    def user_in_guild(self, guild: discord.Guild) -> Awaitable[bool]:
        return user_in_guild(guild, self.author)

    def get_timezone(self) -> Awaitable[Optional[zoneinfo.ZoneInfo]]:
        return Time_Zones.get_timezone(self.author)
