from __future__ import annotations

from typing import Awaitable, TYPE_CHECKING

import donphan  # type: ignore

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .bot import BotBase

__all__ = ("Context",)


class Context(commands.Context):
    bot: BotBase  # type: ignore

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)  # type: ignore
        self.db = donphan.MaybeAcquire(pool=self.bot.pool)

    def user_in_guild(self, guild: discord.Guild) -> Awaitable[bool]:
        # this is a hack because >circular imports<
        from .utils.guild import user_in_guild

        return user_in_guild(guild, self.author)
