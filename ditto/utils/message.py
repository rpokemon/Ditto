from __future__ import annotations

import asyncio
import inspect
import io

from typing import Any, Literal, Optional, TYPE_CHECKING, TypeVar, overload

import discord
from discord.ext import commands

from ..types import Emoji, Message, TextChannel, User

if TYPE_CHECKING:
    from ..core import BotBase, Context


__all__ = (
    "bulk_add_reactions",
    "confirm",
    "download_attachment",
    "fetch_previous_message",
    "prompt",
)


THUMBS_UP = "\N{THUMBS UP SIGN}"

CONFIRM_REACTIONS = (
    THUMBS_UP,
    "\N{THUMBS DOWN SIGN}",
)


T = TypeVar("T")


async def _prompt(
    bot: BotBase,
    context: Context,
    to_delete: list[discord.Message],
    channel: TextChannel,
    user: User,
    converter: type[T],
    timeout: float,
    max_tries: int,
    confirm_after: bool,
    delete_after: bool,
) -> T:
    def check(message: discord.Message) -> bool:
        return message.author == user and message.channel == channel

    for i in range(1, max_tries + 1):
        try:
            argument = await bot.wait_for("message", check=check, timeout=timeout)
            to_delete.append(argument)

            try:
                result = await commands.converter.run_converters(
                    context,
                    converter,
                    argument.content,
                    inspect.Parameter("prompt", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                )
                break
            except commands.UserInputError as error:
                error_message = await bot.on_command_error(context, error)
                if error_message is not None:
                    to_delete.append(error_message)

        except asyncio.TimeoutError:
            raise commands.BadArgument("Timed out.")
    else:
        raise commands.BadArgument("Maximum attempts exceeded.")

    if confirm_after:
        if not (
            await confirm(
                bot,
                channel,
                user,
                f"Just to confirm: {result}?",
                timeout=timeout,
                delete_after=delete_after,
            )
        ):
            return await _prompt(
                bot,
                context,
                to_delete,
                channel,
                user,
                converter,
                timeout,
                max_tries - i,
                confirm_after,
                delete_after,
            )

    return result  # type: ignore


async def bulk_add_reactions(message: discord.Message, *reactions: Emoji) -> None:
    coros = [asyncio.ensure_future(message.add_reaction(reaction)) for reaction in reactions]
    await asyncio.wait(coros)


async def confirm(
    bot: BotBase,
    channel: TextChannel,
    user: User,
    *args: Any,
    timeout: float = 60,
    delete_after: bool = False,
    **kwargs: Any,
) -> Optional[bool]:
    message = await channel.send(*args, **kwargs)
    await bulk_add_reactions(message, *CONFIRM_REACTIONS)

    def check(payload: discord.RawReactionActionEvent) -> bool:
        return (
            payload.message_id == message.id and payload.user_id == user.id and str(payload.emoji) in CONFIRM_REACTIONS
        )

    try:
        payload = await bot.wait_for("raw_reaction_add", check=check, timeout=timeout)
        return str(payload.emoji) == THUMBS_UP
    except asyncio.TimeoutError:
        return None
    finally:
        if delete_after:
            await message.delete()


async def download_attachment(message: discord.Message, *, index: int = 0) -> io.BytesIO:
    attachment = io.BytesIO()
    await message.attachments[index].save(attachment)
    return attachment


async def fetch_previous_message(message: Message) -> Optional[discord.Message]:
    async for msg in message.channel.history(before=message, limit=1):
        return msg
    return None


@overload
async def prompt(
    *args: Any,
    context: Literal[None] = ...,
    bot: BotBase = ...,
    channel: TextChannel = ...,
    user: User = ...,
    converter: type[T] = ...,
    timeout: float = ...,
    max_tries: int = ...,
    confirm_after: bool = ...,
    delete_after: bool = ...,
    **kwargs: Any,
) -> T:
    ...


@overload
async def prompt(
    *args: Any,
    context: Context = ...,
    bot: Optional[BotBase] = ...,
    channel: Optional[TextChannel] = ...,
    user: Optional[User] = ...,
    converter: type[T] = ...,
    timeout: float = ...,
    max_tries: int = ...,
    confirm_after: bool = ...,
    delete_after: bool = ...,
    **kwargs: Any,
) -> T:
    ...


async def prompt(
    *args,
    context: Optional[Context] = None,
    bot: Optional[BotBase] = None,
    channel: Optional[TextChannel] = None,
    user: Optional[User] = None,
    converter: type[T] = str,
    timeout: float = 60,
    max_tries: int = 3,
    confirm_after: bool = False,
    delete_after: bool = False,
    **kwargs,
) -> T:
    if context is None:
        if None in (bot, channel, user):
            raise ValueError("Values; bot, channel and user cannot be None if no context passed.")
    else:
        bot = bot or context.bot
        channel = channel or context.channel
        user = user or context.author

    assert isinstance(bot, BotBase)
    assert isinstance(channel, TextChannel)
    assert isinstance(user, User)

    message = await channel.send(*args, **kwargs)

    if context is None:
        # this is a hack because >circular imports<
        from ..core import Context

        context = await bot.get_context(message, cls=Context)

    to_delete: list[discord.Message] = [message]

    async with channel.typing():
        result = await _prompt(
            bot,
            context,
            to_delete,
            channel,
            user,
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
