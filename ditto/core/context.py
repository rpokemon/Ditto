from __future__ import annotations

import asyncio
import datetime
import inspect
import io
import zoneinfo

from collections.abc import Awaitable
from typing import Optional, TYPE_CHECKING, Union, TypeVar

import discord
from discord.ext import commands

from donphan import MaybeAcquire

from ..db import Time_Zones, NoDatabase
from ..types import Emoji, TextChannel, User
from ..utils.guild import user_in_guild
from ..utils.time import normalise_timedelta


if TYPE_CHECKING:
    from .bot import BotBase

__all__ = ("Context",)


T = TypeVar("T")


CHECK_MARK = "\N{WHITE HEAVY CHECK MARK}"

THUMBS_UP = "\N{THUMBS UP SIGN}"
CONFIRM_REACTIONS = (
    THUMBS_UP,
    "\N{THUMBS DOWN SIGN}",
)

SLEEP_FOR = 3


class Context(commands.Context):
    bot: BotBase
    db: MaybeAcquire

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.bot.pool:
            self.db = MaybeAcquire(pool=self.bot.pool)
        else:
            self.db = NoDatabase()

    async def _prompt(
        self,
        to_delete: list[discord.Message],
        channel: discord.TextChannel,
        converter: type[T],
        timeout: float,
        max_tries: int,
        confirm_after: bool,
        delete_after: bool,
    ) -> T:
        def check(message: discord.Message) -> bool:
            return message.author == self.author and message.channel == channel

        for i in range(1, max_tries + 1):
            try:
                argument = await self.bot.wait_for("message", check=check, timeout=timeout)
                to_delete.append(argument)

                try:
                    result = await commands.converter.run_converters(
                        self,
                        converter,
                        argument.content,
                        inspect.Parameter("prompt", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                    )
                    break
                except commands.UserInputError as error:
                    error_message = await self.bot.on_command_error(self, error)
                    if error_message is not None:
                        to_delete.append(error_message)

            except asyncio.TimeoutError:
                raise commands.BadArgument("Timed out.")
        else:
            raise commands.BadArgument("Maximum attempts exceeded.")

        if confirm_after:
            if not (
                await self.confirm(
                    f"Just to confirm: {result}?",
                    channel=channel,
                    timeout=timeout,
                    delete_after=delete_after,
                )
            ):
                return await self._prompt(
                    to_delete,
                    channel,
                    converter,
                    timeout,
                    max_tries - i,
                    confirm_after,
                    delete_after,
                )

        return result  # type: ignore

    def reply(self, *args, **kwargs):
        mention_author = kwargs.pop("mention_author", True)
        return super().reply(*args, mention_author=mention_author, **kwargs)

    def user_in_guild(self, guild: discord.Guild) -> Awaitable[bool]:
        return user_in_guild(guild, self.author)

    async def get_timezone(self) -> Optional[zoneinfo.ZoneInfo]:
        async with self.db as connection:
            return await Time_Zones.get_timezone(connection, self.author)

    async def fetch_previous_message(
        self, message: Optional[Union[discord.Message, discord.PartialMessage]]
    ) -> Optional[discord.Message]:
        message = message or self.message
        async for msg in message.channel.history(before=message, limit=1):
            return msg
        return None

    async def download_attachment(self, message: Optional[discord.Message], *, index: int = 0) -> io.BytesIO:
        message = message or self.message
        attachment = io.BytesIO()
        await message.attachments[index].save(attachment)
        return attachment

    async def download_avatar(self, user: Optional[User]) -> io.BytesIO:
        user = user or self.author
        attachment = io.BytesIO()
        await user.avatar.save(attachment)
        return attachment

    async def fetch_audit_log_entry(
        self,
        guild: Optional[discord.Guild],
        *,
        user: Optional[User],
        moderator: Optional[User],
        action: Optional[discord.AuditLogAction],
        delta: Union[float, datetime.timedelta] = 10,
        retry: int = 3,
    ) -> Optional[discord.AuditLogEntry]:
        guild = guild or self.guild
        if guild is None:
            raise ValueError("Can only fetch audit log entries for guilds.")
        delta = normalise_timedelta(delta)

        async for entry in guild.audit_logs(action=action, user=moderator):
            if (self.message.created_at - entry.created_at) < delta and (user is None or entry.target == user):
                return entry

        if retry > 0:
            await asyncio.sleep(SLEEP_FOR)
            return await self.fetch_audit_log_entry(
                guild,
                user=user,
                moderator=moderator,
                action=action,
                delta=delta,
                retry=retry - 1,
            )

        return None

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

    async def prompt(
        self,
        *args,
        channel: Optional[TextChannel] = None,
        converter: type[T] = str,  # type: ignore
        timeout: float = 60,
        max_tries: int = 3,
        confirm_after: bool = False,
        delete_after: bool = False,
        **kwargs,
    ) -> T:
        channel = channel or self

        message = await channel.send(*args, **kwargs)

        to_delete: list[discord.Message] = [message]

        async with self.typing():
            result = await self._prompt(
                to_delete,
                channel,  # type: ignore
                converter,
                timeout,
                max_tries,
                confirm_after,
                delete_after,
            )

        try:
            if delete_after and isinstance(channel, discord.TextChannel):
                await channel.delete_messages(to_delete)
        finally:
            return result
