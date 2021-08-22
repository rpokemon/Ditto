from __future__ import annotations

import datetime
import io
import zoneinfo

from collections.abc import Awaitable
from typing import Any, Coroutine, Optional, TYPE_CHECKING, Union, TypeVar

import discord
from discord.ext import commands

from donphan import MaybeAcquire

from ..db import TimeZones, NoDatabase
from ..types import Emoji, Message, TextChannel, User
from ..utils.guild import fetch_audit_log_entry, user_in_guild
from ..utils.message import bulk_add_reactions, confirm, download_attachment, fetch_previous_message, prompt
from ..utils.users import download_avatar


if TYPE_CHECKING:
    from discord.asset import ValidAssetFormatTypes
    from .bot import BotBase, Bot, AutoShardedBot

__all__ = ("Context",)


T = TypeVar("T")
BotT = TypeVar("BotT", bound=Union["Bot", "AutoShardedBot"])


CHECK_MARK = "\N{WHITE HEAVY CHECK MARK}"


class Context(commands.Context[BotT]):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db: MaybeAcquire
        if self.bot.pool:
            self.db = MaybeAcquire(pool=self.bot.pool)
        else:
            self.db = NoDatabase()

    def reply(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, discord.Message]:
        mention_author = kwargs.pop("mention_author", True)
        return super().reply(*args, mention_author=mention_author, **kwargs)

    def user_in_guild(self, guild: discord.Guild) -> Awaitable[bool]:
        return user_in_guild(guild, self.author)

    async def get_timezone(self) -> Optional[zoneinfo.ZoneInfo]:
        async with self.db as connection:
            return await TimeZones.get_timezone(connection, self.author)

    async def fetch_previous_message(self, message: Optional[Message]) -> Optional[discord.Message]:
        return await fetch_previous_message(message or self.message)

    async def download_attachment(self, message: Optional[discord.Message], *, index: int = 0) -> io.BytesIO:
        return await download_attachment(message or self.message, index=index)

    async def download_avatar(
        self, user: Optional[User], size: int = 256, static: bool = False, format: ValidAssetFormatTypes = "png"
    ) -> io.BytesIO:
        return await download_avatar(user or self.author, size=size, static=static, format=format)

    async def fetch_audit_log_entry(
        self,
        *,
        guild: Optional[discord.Guild] = None,
        user: Optional[User] = None,
        moderator: Optional[User] = None,
        action: Optional[discord.AuditLogAction] = None,
        delta: Union[float, datetime.timedelta] = 10,
        retry: int = 3,
    ) -> Optional[discord.AuditLogEntry]:
        guild = guild or self.guild

        if guild is None:
            raise ValueError("Can only fetch audit log entries for guilds.")

        return await fetch_audit_log_entry(
            guild,
            time=self.message.created_at,
            user=user,
            moderator=moderator,
            action=action,
            delta=delta,
            retry=retry - 1,
        )

    async def bulk_add_reactions(self, *reactions: Emoji, message: Optional[discord.Message] = None) -> None:
        return await bulk_add_reactions(message or self.message, *reactions)

    async def tick(self, *, message: Optional[discord.Message] = None, emoji: Emoji = CHECK_MARK) -> None:
        await (message or self.message).add_reaction(emoji)

    async def confirm(
        self,
        *args,
        channel: Optional[TextChannel] = None,
        user: Optional[User] = None,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs,
    ) -> Optional[bool]:
        return await confirm(
            self.bot,
            channel or self.channel,
            user or self.author,
            *args,
            timeout=timeout,
            delete_after=delete_after,
            **kwargs,
        )

    async def prompt(
        self,
        *args,
        channel: Optional[TextChannel] = None,
        user: Optional[User] = None,
        converter: type[T] = str,
        timeout: float = 60,
        max_tries: int = 3,
        confirm_after: bool = False,
        delete_after: bool = False,
        **kwargs,
    ) -> T:
        return await prompt(
            *args,
            context=self,
            channel=channel,
            user=user,
            converter=converter,
            timeout=timeout,
            max_tries=max_tries,
            confirm_after=confirm_after,
            delete_after=delete_after,
            **kwargs,
        )
