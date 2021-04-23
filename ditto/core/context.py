from __future__ import annotations

import asyncio
import zoneinfo

from typing import Awaitable, Optional, TYPE_CHECKING, Union

import donphan

import discord
from discord.ext import commands

from ..db import Time_Zones
from ..utils.guild import user_in_guild
from ..types import Emoji, TextChannel

if TYPE_CHECKING:
    from .bot import BotBase

__all__ = ("Context",)


CHECK_MARK = "\N{WHITE HEAVY CHECK MARK}"

THUMBS_UP = "\N{THUMBS UP SIGN}"
CONFIRM_REACTIONS = (
    THUMBS_UP,
    "\N{THUMBS DOWN SIGN}",
)


class Context(commands.Context):
    bot: BotBase

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = donphan.MaybeAcquire(pool=self.bot.pool)

    def reply(self, *args, **kwargs):
        mention_author = kwargs.pop("mention_author", True)
        return super().reply(*args, mention_author=mention_author, **kwargs)

    def user_in_guild(self, guild: discord.Guild) -> Awaitable[bool]:
        return user_in_guild(guild, self.author)

    def get_timezone(self) -> Awaitable[Optional[zoneinfo.ZoneInfo]]:
        return Time_Zones.get_timezone(self.author)

    async def bulk_add_reactions(self, *reactions: Emoji, message: Optional[discord.Message] = None) -> None:
        message = message or self.message
        coros = [asyncio.ensure_future(message.add_reaction(reaction)) for reaction in reactions]
        await asyncio.wait(coros)

    async def tick(self, *, message: Optional[discord.Message] = None, emoji: Emoji = CHECK_MARK) -> None:
        message = message or self.message
        await message.add_reaction(emoji)

    async def confirm(
        self,
        *args,
        channel: Optional[TextChannel] = None,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs,
    ) -> Optional[bool]:
        channel = channel or self

        message = await channel.send(*args, **kwargs)
        await self.bulk_add_reactions(*CONFIRM_REACTIONS, message=message)

        def check(payload: discord.RawReactionActionEvent) -> bool:
            return (
                payload.message_id == message.id
                and payload.user_id == self.author.id
                and str(payload.emoji) in CONFIRM_REACTIONS
            )

        try:
            payload = await self.bot.wait_for("raw_reaction_add", check=check, timeout=timeout)
            return str(payload.emoji) == THUMBS_UP
        except asyncio.TimeoutError:
            return None
        finally:
            if delete_after:
                await message.delete()
