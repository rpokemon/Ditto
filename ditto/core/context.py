from __future__ import annotations

import io
import zoneinfo
from collections.abc import Awaitable, Coroutine
from typing import TYPE_CHECKING, Any, TypeVar, overload

import discord
from discord.ext import commands
from donphan import MaybeAcquire

from ..db import NoDatabase, TimeZones
from ..types import Emoji
from ..utils.guild import user_in_guild
from ..utils.message import bulk_add_reactions, confirm, download_attachment, fetch_previous_message, prompt
from ..utils.users import download_avatar

if TYPE_CHECKING:
    from discord.asset import ValidAssetFormatTypes

    from .bot import AutoShardedBot, Bot

__all__ = ("Context",)


T = TypeVar("T")
BotT = TypeVar("BotT", bound="Bot | AutoShardedBot")


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

    async def get_timezone(self) -> zoneinfo.ZoneInfo | None:
        if self.author.id in TimeZones._cache:
            return TimeZones._cache[self.author.id]
        else:
            async with self.db as connection:
                return await TimeZones.get_timezone(connection, self.author)

    async def fetch_previous_message(self) -> discord.Message | None:
        return await fetch_previous_message(self.message)

    async def download_attachment(self, *, index: int = 0) -> io.BytesIO:
        return await download_attachment(self.message, index=index)

    async def download_avatar(
        self, size: int = 256, static: bool = False, format: ValidAssetFormatTypes = "png"
    ) -> io.BytesIO:
        return await download_avatar(self.author, size=size, static=static, format=format)

    async def bulk_add_reactions(self, *reactions: Emoji) -> None:
        return await bulk_add_reactions(self.message, *reactions)

    async def tick(self, *, emoji: Emoji = CHECK_MARK) -> None:
        await self.message.add_reaction(emoji)

    async def confirm(
        self,
        *args,
        dm: bool = False,
        timeout: float = 60,
        delete_after: bool = False,
        **kwargs,
    ) -> bool | None:
        return await confirm(
            self.bot,
            self.author if dm else self.channel,
            self.author,
            *args,
            timeout=timeout,
            delete_after=delete_after,
            **kwargs,
        )

    @overload
    async def prompt(
        self,
        *args,
        dm: bool = ...,
        converter: type[T] = ...,  # type: ignore
        timeout: float = ...,
        max_tries: int = ...,
        confirm_after: bool = ...,
        delete_after: bool = ...,
        **kwargs,
    ) -> T:
        ...

    @overload
    async def prompt(
        self,
        *args,
        dm: bool = ...,
        timeout: float = ...,
        max_tries: int = ...,
        confirm_after: bool = ...,
        delete_after: bool = ...,
        **kwargs,
    ) -> str:
        ...

    async def prompt(
        self,
        *args,
        dm: bool = False,
        converter: type[T] = str,
        timeout: float = 60,
        max_tries: int = 3,
        confirm_after: bool = False,
        delete_after: bool = False,
        **kwargs,
    ) -> T | str:
        return await prompt(
            *args,
            context=self,
            channel=self.author if dm else self.channel,
            user=self.author,
            converter=converter,
            timeout=timeout,
            max_tries=max_tries,
            confirm_after=confirm_after,
            delete_after=delete_after,
            **kwargs,
        )
